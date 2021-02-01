# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    Logger

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
import xbmc


class Logging:
    """A helper class for logging"""
    TYPE_DIAL_SERVER = 'debug_dial_server'
    TYPE_SSDP_SERVER = 'debug_ssdp_server'
    TYPE_APPS = 'debug_apps'

    def __init__(self):
        self.__addon_id = None
        self.is_enabled = False
        self.debug_dial_server = False
        self.debug_ssdp_server = False
        self.debug_apps = False
        self.debug = self._debug
        self.info = self._info
        self.warn = self._warn

    def initialize(self, addon_id, is_enabled, debug_dial_server, debug_ssdp_server, debug_apps):
        self.__addon_id = addon_id
        self.is_enabled = is_enabled
        self.debug_dial_server = debug_dial_server and is_enabled
        self.debug_ssdp_server = debug_ssdp_server and is_enabled
        self.debug_apps = debug_apps and is_enabled
        self.__log('The debug logging is {}'.format(is_enabled), xbmc.LOGINFO)
        # To avoid adding extra workload to the cpu when logging is not required,
        # we replace the log methods with a empty method
        if not is_enabled:
            self.debug = self.__not_to_process
            self.info = self.__not_to_process
            self.warn = self.__not_to_process

    def __log(self, msg, log_level, *args, **kwargs):
        """Log a message to the Kodi logfile."""
        if args or kwargs:
            msg = msg.format(*args, **kwargs)
        message = '[{identifier}] {msg}'.format(
            identifier=self.__addon_id,
            msg=msg)
        xbmc.log(message, log_level)

    def _debug(self, msg, *args, **kwargs):
        """Log a debug message."""
        self.__log(msg, xbmc.LOGDEBUG, *args, **kwargs)

    def _info(self, msg, *args, **kwargs):
        """Log an info message."""
        self.__log(msg, xbmc.LOGINFO, *args, **kwargs)

    def _warn(self, msg, *args, **kwargs):
        """Log a warning message."""
        self.__log(msg, xbmc.LOGWARNING, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log an error message."""
        self.__log(msg, xbmc.LOGERROR, *args, **kwargs)

    def __not_to_process(self, msg, *args, **kwargs):
        pass


class GetLogger:
    """Make a new logger by using a prefix name"""
    def __init__(self, name, debug_type):
        self.name = '{}: '.format(name)
        self.debug_type = debug_type
        self.debug = self._debug
        self.info = self._info
        self.warn = self._warn

    def _debug(self, msg, *args, **kwargs):
        """Log a debug message."""
        if not getattr(LOG, self.debug_type):
            self.debug = self.__not_to_process
            return
        LOG.debug(self.name + msg, *args, **kwargs)

    def _info(self, msg, *args, **kwargs):
        """Log an info message."""
        if not getattr(LOG, self.debug_type):
            self.info = self.__not_to_process
            return
        LOG.info(self.name + msg, *args, **kwargs)

    def _warn(self, msg, *args, **kwargs):
        """Log a warning message."""
        if not getattr(LOG, self.debug_type):
            self.warn = self.__not_to_process
            return
        LOG.warn(self.name + msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log an error message."""
        LOG.error(self.name + msg, *args, **kwargs)

    def __not_to_process(self, msg, *args, **kwargs):
        pass


LOG = Logging()
