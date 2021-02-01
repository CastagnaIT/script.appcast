# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    Functions for starting the script service

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
import threading

import xbmc

import resources.lib.servers.dial_server as dial_server
import resources.lib.servers.ssdp_server as ssdp_server
from resources.lib.globals import G
from resources.lib.helpers.logging import LOG


class AppCastService:
    HOST_ADDRESS = '0.0.0.0'

    def __init__(self):
        self.dial_srv_instance = None
        self.dial_srv_thread = None
        self.ssdp_udp_srv_instance = None
        self.ssdp_udp_srv_thread = None

    def init_servers(self):
        """Initialize the servers"""
        try:
            self.dial_srv_instance = dial_server.DialTCPServer((self.HOST_ADDRESS, G.DIAL_SERVER_PORT))
            self.dial_srv_instance.allow_reuse_address = True
            self.dial_srv_thread = threading.Thread(target=self.dial_srv_instance.serve_forever)
            self.ssdp_udp_srv_instance = ssdp_server.SSDPUDPServer()
            self.ssdp_udp_srv_instance.allow_reuse_address = True
            self.ssdp_udp_srv_thread = threading.Thread(target=self.ssdp_udp_srv_instance.serve_forever)
            return True
        except Exception:  # pylint: disable=broad-except
            import traceback
            LOG.error(traceback.format_exc())
        return False

    def start_services(self):
        """Start the background services"""
        self.dial_srv_instance.server_activate()
        self.dial_srv_thread.start()
        LOG.info('[DialServer] service started')
        self.ssdp_udp_srv_thread.start()
        LOG.info('[SSDPUDPServer] service started')

    def shutdown(self):
        """Stop the background services"""
        self.dial_srv_instance.shutdown()
        self.dial_srv_instance.server_close()
        self.dial_srv_instance = None
        self.dial_srv_thread.join()
        self.dial_srv_thread = None
        LOG.info('[DialServer] service stopped')
        self.ssdp_udp_srv_instance.shutdown()
        self.ssdp_udp_srv_instance.server_close()
        self.ssdp_udp_srv_instance = None
        self.ssdp_udp_srv_thread.join()
        self.ssdp_udp_srv_thread = None
        LOG.info('[SSDPUPDServer] service stopped')

    def run(self):
        """Main loop. Runs until xbmc.Monitor requests abort"""
        try:
            self.start_services()
            monitor = xbmc.Monitor()
            while not monitor.abortRequested():
                monitor.waitForAbort(1)
            self.shutdown()
        except Exception:  # pylint: disable=broad-except
            import traceback
            LOG.error(traceback.format_exc())


def run():
    G.init_globals()
    appcast_service = AppCastService()
    if appcast_service.init_servers():
        appcast_service.run()
