# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    Misc utils

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
from functools import wraps
from urllib.parse import unquote
from xml.sax.saxutils import escape

import xbmcaddon
import AddonSignals

from resources.lib.helpers import exceptions
from resources.lib.helpers.logging import LOG

IPC_TIMEOUT_SECS = 20
IPC_EXCEPTION_PLACEHOLDER = 'IPC_EXCEPTION_PLACEHOLDER'
IPC_ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')


def url_decode_xml_encode(string_value):
    """URL-unescape the string, then XML-escape it"""
    return escape(unquote(string_value))


def get_string_size(string_value):
    """Return the byte size of a string (encoded with utf-8)"""
    return len(string_value.encode('utf-8'))


def fix_return_chars(string_value):
    """Replace existing return chars with return chars for HTTP"""
    # This is needed because some apps not parse the message correctly
    return '\r\n'.join(string_value.splitlines())


class FormatMapSubCls(dict):
    """Subclass needed for str.format_map command"""
    def __missing__(self, key):
        return key


def is_ascii(byte_string):
    """Check if a byte string is ascii"""
    try:
        byte_string.decode('ascii')
    except UnicodeEncodeError:
        return False
    return True


def is_less_version(version, max_version):
    """Return True if version is less to max_version"""
    return list(map(int, version.split('.'))) < list(map(int, max_version.split('.')))


def register_addonsignals_slot(callback, signal=None, source_id=None):
    """Register a callback with AddonSignals for return calls"""
    name = signal if signal else callback.__name__
    AddonSignals.registerSlot(
        signaler_id=source_id or IPC_ADDON_ID,
        signal=name,
        callback=callback)
    LOG.debug('Registered AddonSignals slot {} to {}'.format(name, callback))


def send_addonsignals_signal(signal, data=None):
    """Send a signal via AddonSignals"""
    AddonSignals.sendSignal(
        source_id=IPC_ADDON_ID,
        signal=signal,
        data=data)


def make_addonsignals_call(callname, data=None):
    """Make an IPC call via AddonSignals and wait for it to return.
    The contents of data will be expanded to kwargs and passed into the target function."""
    LOG.debug('Handling AddonSignals IPC call to {}'.format(callname))
    try:
        result = AddonSignals.makeCall(
            source_id=IPC_ADDON_ID,
            signal=callname,
            data=data,
            timeout_ms=IPC_TIMEOUT_SECS * 1000,
            use_timeout_exception=True)
        _raise_for_error(result)
    except AddonSignals.WaitTimeoutError:
        raise Exception('Addon Signals call timeout')
    return result


def _raise_for_error(result):
    # The json exception data format is set by ipc_convert_exc_to_json function
    if isinstance(result, dict) and IPC_EXCEPTION_PLACEHOLDER in result:
        result = result[IPC_EXCEPTION_PLACEHOLDER]
        if result['class'] in exceptions.__dict__:
            raise exceptions.__dict__[result['class']](result['message'])
        raise Exception(result['class'] + '\r\nError details:\r\n' + result.get('message', '--'))


def ipc_return_call_decorator(func):
    """
    Decorator to make a func return callable through IPC
    and handles catching, conversion and forwarding of exceptions
    """
    @wraps(func)
    def make_return_call(instance, data):
        _perform_ipc_return_call_instance(instance, func, data)
    return make_return_call


def _perform_ipc_return_call_instance(instance, func, data):
    try:
        result = _call_with_instance(instance, func, data)
    except Exception as exc:  # pylint: disable=broad-except
        LOG.error('IPC callback raised exception: {exc}', exc=exc)
        import traceback
        LOG.error(traceback.format_exc())
        result = ipc_convert_exc_to_json(exc)
    AddonSignals.returnCall(signal=func.__name__, source_id=IPC_ADDON_ID, data=result)
    return result


def _call_with_instance(instance, func, data):
    if isinstance(data, dict):
        return func(instance, **data)
    if data is not None:
        return func(instance, data)
    return func(instance)


def ipc_convert_exc_to_json(exc=None, class_name=None, message=None):
    """
    Convert an exception to a json data exception
    :param exc: exception class

    or else, build a json data exception
    :param class_name: custom class name
    :param message: custom message
    """
    return {IPC_EXCEPTION_PLACEHOLDER: {
        'class': class_name or exc.__class__.__name__,
        'message': message or str(exc),
    }}
