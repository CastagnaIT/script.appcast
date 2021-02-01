# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 Netflix, Inc.
    Copyright (C) 2021 Stefano Gottardo (python porting)
    DIAL Service

    SPDX-License-Identifier: BSD-2-Clause
    See LICENSES/BSD-2-Clause-Netflix.md for more information.
"""
import importlib
import importlib.machinery
import importlib.util
import re
import sys
from copy import deepcopy
from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
from threading import Lock
from typing import TYPE_CHECKING, Type
from urllib.parse import parse_qs, urlparse

import xbmc

import resources.lib.database.db_base_sqlite as db_sqlite
import resources.lib.helpers.utils as utils
import resources.lib.servers.ssdp_helper as ssdp_msgs
from resources.lib.globals import G
from resources.lib.helpers import kodi_ops, file_ops
from resources.lib.helpers.kodi_interface import KodiInterface
from resources.lib.helpers.logging import GetLogger, LOG
from resources.lib.servers.dial_helper import (OPTIONS_RESPONSE, STATUS_RESPONSE, CREATED_RESPONSE, STOP_RESPONSE,
                                               DialStatus, RESPONSE_OK, store_dial_data, retrieve_dial_data)

if TYPE_CHECKING:  # This variable/import is used only by the editor, so not at runtime
    from resources.lib.apps.dial_app_test.dial_app_test import DialApp

LOGGER = GetLogger('DIAL-Server', LOG.TYPE_DIAL_SERVER)

MUTEX = Lock()

DIAL_VERSION = '2.2'  # DIAL version that is reported via in the status response
DIAL_MAX_PAYLOAD = 4096  # The maximum DIAL payload accepted per the DIAL 1.6.1 specification
DIAL_MAX_ADDITIONALURL = 1024  # The maximum additionalDataUrl length
DIAL_DATA_SIZE = 8*1024
DIAL_DATA_MAX_PAYLOAD = 4096  # 4 KB

RUN_URI = '/run'
APPS_URI = '/apps/'
HIDE_URI = '/hide'
DIAL_DATA_URI = '/dial_data'

APPS = []  # List of classes instances of the currently registered DIAL apps/Kodi add-ons


class DialTCPServer(TCPServer):
    """Override TCPServer to allow usage of shared members"""
    def __init__(self, server_address):
        """Initialization of DialTCPServer"""
        kodi_interface = KodiInterface(APPS)
        if G.ADDON.getSettingBool('use_internal_apps'):
            LOGGER.info('Registering internal DIAL apps/add-ons')
            register_internal_apps(kodi_interface)
        else:
            LOGGER.info('Registering DIAL apps/add-ons')
            register_apps(kodi_interface)
        # IPC calls
        utils.register_addonsignals_slot(start_app, signal='start_dial_app')
        utils.register_addonsignals_slot(stop_app, signal='stop_dial_app')
        utils.register_addonsignals_slot(reload_app, signal='reload_dial_app')
        LOGGER.info('Constructing DialTCPServer')
        self.timeout = 1
        super().__init__(server_address, DSHttpRequestHandler)


class DSHttpRequestHandler(BaseHTTPRequestHandler):
    """Handles requests from HTTP"""
    # pylint: disable=invalid-name
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.query_params = None
        self.body_data_size = 0
        self.body_data = b''

    def do_POST(self):
        self.route()

    def do_GET(self):
        self.route()

    def do_OPTIONS(self):
        self.route()

    def do_DELETE(self):
        self.route()

    def route(self):
        LOGGER.debug('Received {} request {} {}', self.command, self.path, self.client_address)
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/ssdp/device-desc.xml':
            handle_dd(self)
        else:
            self.query_params = parse_qs(parsed_url.query)  # NOTICE: the values of each query_params are always lists!
            # Get body content
            self.body_data_size = int(self.headers.get('content-length', 0))
            if self.body_data_size:
                self.body_data = self.rfile.read(self.body_data_size) or b''
            else:
                self.body_data = b''
            origin_header = self.headers.get('Origin', self.headers.get('origin'))
            host_header = self.headers.get('Host', self.headers.get('host'))
            try:
                handle_request(self, self.command, parsed_url.path, origin_header, host_header)
            except Exception as exc:
                LOGGER.error('handle_request raised an exception: {}', exc)
                import traceback
                LOGGER.error(traceback.format_exc())
                self.call_error(500, 'ERROR')

    def call_response(self, data):
        LOGGER.debug('Send response:\n{}', data)
        self.wfile.write(data.encode('utf-8'))

    def call_error(self, code, message):
        LOGGER.debug('Send error response: ({}) {}', code, message)
        self.send_response(code, message)
        self.end_headers()

    def log_message(self, *args):  # pylint: disable=arguments-differ
        """Override method to disable the BaseHTTPServer Log"""


def handle_dd(server):
    """Handle SSDP HTTP request for device descriptor xml"""
    data = ssdp_msgs.DD_XML.format(
        ip_addr=kodi_ops.get_local_ip(),
        dial_port=G.DIAL_SERVER_PORT,
        friendly_name=G.SP_FRIENDLY_NAME,
        manufacturer_name=G.SP_MANUFACTURER_NAME,
        model_name=G.SP_MODEL_NAME,
        device_uuid=G.DEVICE_UUID
    )
    server.call_response(utils.fix_return_chars(data))


def handle_request(server, req_method, req_path, origin_header, host_header):
    if req_path.endswith(RUN_URI):
        # URL ends with run
        # Maximum app name length of 255 characters.
        app_name = req_path.split('/')[-2][:255]
        # Check authorized origins.
        if origin_header and not is_allowed_origin(origin_header, app_name):
            server.call_error(403, 'Forbidden')
            return
        # Return OPTIONS.
        if req_method == 'OPTIONS':
            server.call_response(OPTIONS_RESPONSE.format(origin=origin_header, methods='DELETE, OPTIONS'))
            return
        # DELETE non-empty app name
        if app_name and req_method == 'DELETE':
            handle_app_stop(server, app_name, origin_header)
        else:
            server.call_error(501, 'Not Implemented')
    elif req_path.startswith(APPS_URI):
        # URI starts with "/apps/" and is followed by an app name
        app_name = req_path.replace(APPS_URI, '')
        # Check authorized origins.
        if origin_header and not is_allowed_origin(origin_header, app_name):
            server.call_error(403, 'Forbidden')
            return
        # Return OPTIONS.
        if req_method == 'OPTIONS':
            server.call_response(OPTIONS_RESPONSE.format(origin=origin_header, methods='GET, POST, OPTIONS'))
            return
        # Start app
        if req_method == 'POST':
            handle_app_start(server, app_name, origin_header)
        # Get app status
        elif req_method == 'GET':
            handle_app_status(server, app_name, origin_header)
        else:
            server.call_error(501, 'Not Implemented')
    elif req_path.endswith(HIDE_URI):
        # URI that ends with HIDE_URI
        # Maximum app name length of 255 characters.
        app_name = req_path.split('/')[-2][:255]
        # Check authorized origins.
        if origin_header and not is_allowed_origin(origin_header, app_name):
            server.call_error(403, 'Forbidden')
            return
        if req_method == 'OPTIONS':
            server.call_response(OPTIONS_RESPONSE.format(origin=origin_header, methods='POST, OPTIONS'))
            return
        # Hide app
        if app_name and req_method == 'POST':
            handle_app_hide(server, app_name, origin_header)
        else:
            server.call_error(501, 'Not Implemented')
    elif req_path.endswith(DIAL_DATA_URI):
        # URI is of the form */app_name/dial_data
        # Check if the call come from localhost
        if server.client_address[0] in ['127.0.0.1', xbmc.getIPAddress()]:
            app_name = req_path.split('/')[-2]
            if not app_name:
                server.call_error(500, '500 Internal Server Error')
            else:
                # Check authorized origins.
                if origin_header and not is_allowed_origin(origin_header, app_name):
                    server.call_error(403, 'Forbidden')
                    return
                if req_method == 'OPTIONS':
                    server.call_response(OPTIONS_RESPONSE.format(origin=origin_header, methods='POST, OPTIONS'))
                    return
                # Deliver data payload
                handle_dial_data(server, app_name, origin_header, req_method == 'POST')
        else:
            server.call_error(404, 'Not found')


def handle_app_status(server, app_name, origin_header):
    # Determine client version
    client_version = float(server.query_params.get('clientDialVer', ['0.0'])[0])
    if not MUTEX.acquire(False):
        server.call_error(500, '500 Internal Server Error')
        return
    app = find_app(app_name)
    if not app:
        server.call_error(404, 'Not found')
        MUTEX.release()
        return
    dial_data = ''
    try:
        for key, value in app.dial_data.items():
            dial_data += '\r\n    <{key}>{value}</{key}>'.format(
                key=utils.url_decode_xml_encode(key),
                value=utils.url_decode_xml_encode(value)
            )
    except Exception as exc:
        LOGGER.error('handle_app_status error {} with data {}', exc, app.dial_data)
        server.call_error(500, '500 Internal Server Error')
        MUTEX.release()
        return
    if utils.get_string_size(dial_data) > DIAL_DATA_SIZE:
        LOGGER.error('Exceeded maximum size for dial_data')
        server.call_error(500, '500 Internal Server Error')
        MUTEX.release()
        return
    local_state = app.dial_cb_status()
    app.state = local_state
    # Overwrite app->state if client version < 2.1
    if client_version < 2.09 and local_state == DialStatus.HIDE:
        local_state = DialStatus.STOPPED
    # Get string version of app state
    if local_state == DialStatus.HIDE:
        dial_state = 'hidden'
    elif local_state == DialStatus.RUNNING:
        dial_state = 'running'
    else:
        dial_state = 'stopped'
    server.call_response(STATUS_RESPONSE.format(
        origin=origin_header,
        dial_version=DIAL_VERSION,
        app_name=app_name,
        can_stop='true',  # We support the DELETE operation
        dial_state=dial_state,
        link='' if local_state == DialStatus.STOPPED else '\r\n  <link rel="run" href="run"/>',
        dial_data=dial_data + '\r\n  '
    ))
    MUTEX.release()


def handle_app_start(server, app_name, origin_header):
    additional_data_param = None
    if not MUTEX.acquire(False):
        server.call_error(500, '500 Internal Server Error')
        return
    app = find_app(app_name)
    if not app:
        server.call_error(404, 'Not found')
        MUTEX.release()
        return
    elif server.body_data_size > DIAL_MAX_PAYLOAD:
        server.call_error(413, '413 Request Entity Too Large')
    # Checks if a payload string contains invalid characters (unprintable or non-ASCII character)
    elif not utils.is_ascii(server.body_data):
        server.call_error(400, '400 Bad Request')
    else:
        if app.USE_ADDITIONAL_DATA:
            # Construct additionalDataUrl=http://host:port/apps/app_name/dial_data
            additional_data_param = 'http://127.0.0.1:{port}/apps/{app_name}/dial_data'.format(
                port=G.DIAL_SERVER_PORT,
                app_name=app_name)
            if utils.get_string_size(additional_data_param) > DIAL_MAX_ADDITIONALURL:
                LOGGER.error('Exceeded maximum size for additional_data_param')
                server.call_error(500, '500 Internal Server Error')
                MUTEX.release()
                return
        payload = server.body_data.decode('utf-8')
        LOGGER.debug('Starting app {} with params {}', app_name, payload)
        app.state = app.dial_cb_start(deepcopy(payload), server.query_params, additional_data_param)
        if app.state == DialStatus.RUNNING:
            server.call_response(CREATED_RESPONSE.format(
                address=kodi_ops.get_local_ip(),
                dial_port=G.DIAL_SERVER_PORT,
                app_name=app_name,
                origin=origin_header))
            # Make a backup copy of the payload
            app.last_payload = payload
        elif app.state == DialStatus.ERROR_FORBIDDEN:
            server.call_error(400, '403 Forbidden')
        elif app.state == DialStatus.ERROR_UNAUTH:
            server.call_error(401, '401 Unauthorized')
        elif app.state == DialStatus.ERROR_NOT_IMPLEMENTED:
            server.call_error(501, '501 Not Implemented')
        else:
            server.call_error(503, '503 Service Unavailable')
    MUTEX.release()


def handle_app_stop(server, app_name, origin_header):
    if not MUTEX.acquire(False):
        server.call_error(500, '500 Internal Server Error')
        return
    app = find_app(app_name)
    if app:
        app.state = app.dial_cb_status()
    if not app or app.state == DialStatus.STOPPED:
        server.call_error(404, 'Not found')
    else:
        app.dial_cb_stop()
        app.state = DialStatus.STOPPED
        server.call_response(STOP_RESPONSE.format(origin=origin_header))
    MUTEX.release()


def handle_app_hide(server, app_name, origin_header):
    if not MUTEX.acquire(False):
        server.call_error(500, '500 Internal Server Error')
        return
    app = find_app(app_name)
    if app:
        app.state = app.dial_cb_status()
    if not app or (app.state != DialStatus.RUNNING and app.state != DialStatus.HIDE):
        server.call_error(404, 'Not found')
    else:
        # Not implemented in reference
        status = app.dial_cb_hide()
        if status != DialStatus.HIDE:
            LOGGER.error('Hide not implemented for reference.')
            server.call_error(501, '501 Not Implemented')
        else:
            app.state = DialStatus.HIDE
            server.call_response(RESPONSE_OK.format(origin=origin_header))
    MUTEX.release()


def handle_dial_data(server, app_name, origin_header, use_payload):
    if not MUTEX.acquire(False):
        server.call_error(500, '500 Internal Server Error')
        return
    app = find_app(app_name)
    if app:
        app.state = app.dial_cb_status()
    if not app:
        server.call_error(404, 'Not found')
        MUTEX.release()
        return
    if not use_payload:
        data = urlparse(server.path).query
        if utils.get_string_size(data) > DIAL_DATA_MAX_PAYLOAD:
            server.call_error(413, '413 Request Entity Too Large')
            MUTEX.release()
            return
    else:
        if server.body_data_size > DIAL_DATA_MAX_PAYLOAD:
            server.call_error(413, '413 Request Entity Too Large')
            MUTEX.release()
            return
        data = server.body_data
    if not utils.is_ascii(data):
        server.call_error(400, '400 Bad Request')
        MUTEX.release()
        return
    # Data should be always as HTTP encoded url format
    parsed_data = urlparse(data.decode('ascii'))
    dial_data = dict(parse_qs(parsed_data.query))
    # We remove all the 'list' that enclose the values (generated by parse_qs)
    for key in dial_data.keys():
        dial_data[key] = dial_data[key][0]
    store_dial_data(app_name, dial_data)
    app.dial_data = dial_data
    server.call_response(RESPONSE_OK.format(origin=origin_header))
    MUTEX.release()


def is_allowed_origin(origin, app_name):
    LOGGER.debug('Checking {} for {}', origin, app_name)
    if not origin:
        return True
    if not MUTEX.acquire(False):
        # If we can't check, fail in favor of safety.
        return False
    result = False
    for app in APPS:
        if app_name == app.DIAL_APP_NAME:
            if app.DIAL_ORIGINS and is_uri_in_list(origin, app.DIAL_ORIGINS):
                result = True
                break
    MUTEX.release()
    return result


def is_uri_in_list(origin, origin_list):
    if not origin or not origin_list:
        return False
    is_https = origin.startswith('https://')
    # If the URI begins with https://, perform a host comparison because
    # any port numbers must be handled specially. Otherwise perform a regular match.
    for candidate in origin_list:
        if (is_https and host_matches(origin, candidate)) or (not is_https and origin_matches(origin, candidate)):
            return True
    return False


def host_matches(origin, candidate):
    # TODO: needed conversion from the same method of dial_server.c
    return True


def origin_matches(origin, candidate):
    return re.match(candidate, origin)


def find_app(app_name) -> 'DialApp':
    """
    Return the application in server app list
    :param app_name: the DIAL app name
    :return: the app instance or None if not found
    """
    return next((_app for _app in APPS if _app.DIAL_APP_NAME == app_name), None)


def register_apps(kodi_interface):
    """Register DIAL applications based on the Kodi add-ons that support Cast feature"""
    # We find out which add-ons has "script.appcast" optional dependency,
    # then for each add-on we try import the "DialApp" class included in the path "resources/lib/dial_app_test/"
    addons = kodi_ops.json_rpc('Addons.GetAddons', {'type': 'unknown',
                                                    'properties': ['name', 'dependencies', 'enabled', 'path']})
    MUTEX.acquire()
    # # Clear previous sys modules added
    # for name in list(sys.modules.keys()):
    #     if name.startswith('dial_app_'):
    #         del sys.modules[name]

    for addon in addons['addons']:
        if not addon['enabled']:
            continue
        if any(dep['addonid'] == 'script.appcast' for dep in addon['dependencies']):
            # Try add the DIAL app included in the add-on
            try:
                name = addon['addonid'].split('.')[-1]
                package = 'dial_app_' + name
                module_path_folder1 = file_ops.join_folders_paths(addon['path'],
                                                                  package,
                                                                  package + '.py')
                module_path_folder2 = file_ops.join_folders_paths(addon['path'],
                                                                  'resources/lib/' + package,
                                                                  package + '.py')
                # Check if the add-on has the package file
                if file_ops.file_exists(module_path_folder1):
                    module_path = module_path_folder1
                elif file_ops.file_exists(module_path_folder2):
                    module_path = module_path_folder2
                else:
                    LOGGER.error('register_apps: missing module file {}.py on {} add-on',
                                 package, addon['addonid'])
                    continue
                # Load the external module (and allow it's own relative imports)
                spec = importlib.util.spec_from_file_location(package, module_path, submodule_search_locations=[])
                module = importlib.util.module_from_spec(spec)
                sys.modules[module.__name__] = module
                spec.loader.exec_module(module)
                # Get the "DialApp" class from the loaded module
                app_class = getattr(module, 'DialApp', None)
                if app_class is None:
                    LOGGER.error('register_apps: "DialApp" class not found in {}.py file of {} add-on',
                                 package, addon['addonid'])
                    continue
                register_app(app_class, kodi_interface)
            except Exception:
                LOGGER.error('register_apps: could not import the DIAL app from {}', addon['addonid'])
                import traceback
                LOG.error(traceback.format_exc())
    MUTEX.release()


def register_internal_apps(kodi_interface):
    """Register the internal DIAL applications based on the installed Kodi add-ons"""
    # The DIAL apps will be loaded from "resources/lib/apps" sub-folders
    directory_base = file_ops.join_folders_paths(G.ADDON_DATA_PATH, 'resources/lib/apps')
    dirs, _ = file_ops.list_dir(directory_base)
    MUTEX.acquire()
    for dir_name in dirs:
        try:
            if dir_name.startswith('_') or dir_name == 'dial_app_test':
                continue
            class_file_path = file_ops.join_folders_paths(directory_base, dir_name, dir_name + '.py')
            if not file_ops.file_exists(class_file_path):
                LOG.error('register_internal_apps: missing module file {}.py on {} folder', dir_name, dir_name)
                continue
            # Load the internal module
            loaded_module = importlib.import_module('resources.lib.apps.' + dir_name + '.' + dir_name)
            app_class = getattr(loaded_module, 'DialApp', None)
            if app_class is None:
                LOGGER.error('register_internal_apps: "DialApp" class not found in {}.py file', dir_name)
                continue
            register_app(app_class, kodi_interface)
        except Exception:
            LOGGER.error('register_internal_apps: could not import the DIAL app from {} folder', dir_name)
            import traceback
            LOG.error(traceback.format_exc())
    MUTEX.release()


def register_app(app_class: Type['DialApp'], kodi_interface):
    if not app_class.KODI_ADDON_ID or not app_class.DIAL_APP_NAME:
        LOGGER.error('register_app: KODI_ADDON_ID or DIAL_APP_NAME not specified on {} app class of {} add-on',
                     app_class.DIAL_APP_NAME, app_class.KODI_ADDON_ID)
        return
    existing_app = next((_app for _app in APPS if _app.DIAL_APP_NAME == app_class.DIAL_APP_NAME), None)
    if existing_app:
        LOGGER.warn('register_app: skipped DIAL app {} is already registered by {} add-on',
                    app_class.DIAL_APP_NAME, existing_app.KODI_ADDON_ID)
        return
    if app_class.ENABLE_DATABASE:
        database = db_sqlite.SQLiteDatabase('app_{}.sqlite3'.format(app_class.DIAL_APP_NAME.lower()))
    else:
        database = None
    _app = app_class(kodi_interface, database)
    _app.state = DialStatus.STOPPED  # On class init we have to set it as Stopped
    # dial_data: Is a dict where the values cannot contain any spaces.
    #   They are expected to be URL-escaped strings, so any spaces would be represented as the '+' character.
    #   They have a max length of 255 characters.
    _app.dial_data = retrieve_dial_data(_app.DIAL_APP_NAME)
    APPS.append(_app)
    LOGGER.info('Registered "{}" DIAL app to "{}" add-on', _app.DIAL_APP_NAME, _app.KODI_ADDON_ID)


def start_app(data=None):
    """IPC callback to start a DIAL app"""
    # Todo
    pass


def stop_app(data=None):
    """IPC callback to stop a DIAL app"""
    # Todo
    pass


def reload_app(data=None):
    """IPC callback to reload a DIAL app"""
    # When an add-on will be updated is needed reload the DIAL app, or will remains in memory the old script code
    if data and data.get('skip_version_check'):
        execute_reload = True
    else:
        # Todo: execute reload only if the add-on version is changed
        addon_id = data['addon_id']
        execute_reload = True
    if not execute_reload:
        return
    # Todo
