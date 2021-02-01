# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    Global constants

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
# Everything that is to be globally accessible must be defined in this module.
# Using the Kodi reuseLanguageInvoker feature, only the code in the addon.py or service.py module
# will be run every time the addon is called.
# All other modules (imports) are initialized only on the first invocation of the add-on.
import xbmc
import xbmcaddon

from resources.lib.helpers.uuid_device import get_system_appcast_uuid


class GlobalVariables:
    DIAL_SERVER_PORT = 56789
    # SSDP_SERVER_PORT = 56790
    SSDP_BROADCAST_ADDR = '239.255.255.250'
    SSDP_UPNP_PORT = 1900

    def __init__(self):
        """Do nothing on constructing the object"""
        # The class initialization (GlobalVariables) will only take place at the first initialization of this module
        # on subsequent add-on invocations (invoked by reuseLanguageInvoker) will have no effect.
        # Define here also any other variables necessary for the correct loading of the other project modules
        self.ADDON_ID = None
        self.PLUGIN = None
        self.ICON = None
        self.ADDON = None
        self.ADDON_DATA_PATH = None
        self.DATA_PATH = None
        self.IS_SERVICE = None
        self.SP_FRIENDLY_NAME = None
        self.SP_MODEL_NAME = None
        self.SP_MANUFACTURER_NAME = None
        self.DEVICE_UUID = None
        self.sp_upnp_boot_id = 1

    def init_globals(self):
        """Initialized globally used module variables. Needs to be called at start of each plugin instance!"""
        # xbmcaddon.Addon must be created at every instance otherwise it does not read any new changes to the settings
        self.ADDON = xbmcaddon.Addon()
        self.ADDON_ID = self.ADDON.getAddonInfo('id')
        self.PLUGIN = self.ADDON.getAddonInfo('name')
        self.ICON = self.ADDON.getAddonInfo('icon')
        self.ADDON_DATA_PATH = self.ADDON.getAddonInfo('path')  # Add-on folder
        self.DATA_PATH = self.ADDON.getAddonInfo('profile')  # Add-on user data folder
        try:
            self.IS_SERVICE = False
        except IndexError:
            self.IS_SERVICE = True
        # Initialize the log
        from resources.lib.helpers.logging import LOG
        LOG.initialize(self.ADDON_ID,
                       G.ADDON.getSettingBool('enable_debug'),
                       G.ADDON.getSettingBool('debug_dial_server'),
                       G.ADDON.getSettingBool('debug_ssdp_server'),
                       G.ADDON.getSettingBool('debug_apps'))
        # Set SSDP server variables
        self.SP_FRIENDLY_NAME = xbmc.getInfoLabel("System.FriendlyName") or 'Kodi (AppCast)'
        self.SP_MODEL_NAME = 'MyDeviceModel'
        self.SP_MANUFACTURER_NAME = ' '
        self.DEVICE_UUID = get_system_appcast_uuid()


# We initialize an instance importable of GlobalVariables from run_addon.py and run_service.py,
# where G.init_globals() MUST be called before you do anything else.
G = GlobalVariables()
