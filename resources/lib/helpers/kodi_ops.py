# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    Generic Kodi operations

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
import json

import xbmc

from resources.lib.globals import G


def json_rpc(method, params=None):
    """
    Executes a JSON-RPC in Kodi

    :param method: The JSON-RPC method to call
    :type method: string
    :param params: The parameters of the method call (optional)
    :type params: dict
    :returns: dict -- Method call result
    """
    request_data = {'jsonrpc': '2.0', 'method': method, 'id': 1,
                    'params': params or {}}
    request = json.dumps(request_data)
    # LOG.debug('Executing JSON-RPC: {}', request)
    raw_response = xbmc.executeJSONRPC(request)
    # LOG.debug('JSON-RPC response: {}', raw_response)
    response = json.loads(raw_response)
    if 'error' in response:
        raise IOError('JSONRPC-Error {}: {}'
                      .format(response['error']['code'],
                              response['error']['message']))
    return response['result']


def get_local_string(string_id, is_kodi_id=False):
    """Retrieve a localized string by its id"""
    src = xbmc if is_kodi_id else G.ADDON
    return src.getLocalizedString(string_id)


def show_notification(msg, title='AppCast', time=3000):
    """Show a notification"""
    xbmc.executebuiltin('Notification({}, {}, {}, {})'.format(title, msg, time, G.ICON))


def get_local_ip():
    return xbmc.getIPAddress()


def is_addon_enabled(addon_id):
    return xbmc.getCondVisibility('System.AddonIsEnabled({})'.format(addon_id))
