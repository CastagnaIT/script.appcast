# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    An example to make a new DIAL app

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
# Todo: ---------------------------- DO NOT EDIT OR DELETE THIS FILE/FOLDER ! ----------------------------
#   Please copy this 'dial_app_test' folder to another new one in resources/lib/apps/ folder
#     the name of the new folder have to respect some rules follow instructions on how to make new app on GitHub Wiki.
#   This script will live inside script.appcast add-on also when you place the script files under your add-on folder,
#   despite this is not needed to change references to the imported modules.
#   Following python packages can also be used: requests, AddonSignals
from typing import TYPE_CHECKING

from resources.lib.helpers import kodi_ops
from resources.lib.helpers.logging import GetLogger, LOG
from resources.lib.servers.dial_helper import DialStatus

if TYPE_CHECKING:  # This variable/imports are used only by the editor, so not at runtime
    from resources.lib.database.db_base_sqlite import SQLiteDatabase
    from resources.lib.helpers.kodi_interface import KodiInterface

LOGGER = GetLogger('APP-Test', LOG.TYPE_APPS)


class DialApp:
    # ---- APP CONFIGURATION VARIABLES ----
    KODI_ADDON_ID = None  # Kodi add-on id that will be associated to this DIAL app name
    DIAL_APP_NAME = None  # The DIAL app name, list: http://www.dial-multiscreen.org/dial-registry/namespace-database
    # DIAL_ORIGINS: Is the list of allowed origins, the values can be specified also as raw regex pattern,
    #   if you do not know them you will have to try run this add-on and try Cast with e.g. mobile app
    #   and read the value in the Kodi log on the messages "Checking xyz for xyz" by enabling add-on debug settings
    DIAL_ORIGINS = []
    # USE_ADDITIONAL_DATA: If enabled return the server endpoint on dial_cb_start(),
    #   with this endpoint an add-on can add DIAL data to the server, the server will save the data for reuse next time,
    #   this data will be added on each 'STATUS_RESPONSE' server response from dial_server.py,
    #   this feature is implemented but not tested.
    USE_ADDITIONAL_DATA = False
    CB_TICK_SECS = None  # See on_playback_tick callback description
    ADDON_PLAY_PATH = None  # The plugin path of the add-on to run the playback
    ENABLE_DATABASE = False  # If enabled provide a persistent database to save data, see __init__

    # ---- DIAL SERVER VARIABLES, PLEASE DO NOT CHANGE THE VALUES ----
    state = None
    last_payload = None
    dial_data = {}

    def __init__(self, kodi_interface: 'KodiInterface', database: 'SQLiteDatabase'):
        self.kodi = kodi_interface  # Provide some methods to interact with Kodi player
        self.db = database  # Provide a persistent database to get/save any type of data

    # ---- DIAL SERVER CALLBACK'S ----
    # TODO: (for new apps) WARNING !
    #  The code in these DIAL callback's methods are implementations to test if the server communication works only,
    #  each new application will have to have its own implementation, all callbacks methods must be kept.

    def dial_cb_start(self, payload, query_params, additional_data_param):
        """Callback used to start an application / Kodi add-on"""
        # To know if you need to relaunch the app/add-on or reset his variables,
        # you could compare the content of 'self.last_payload' with 'payload' argument content
        LOGGER.debug('DIAL app name: {}, Kodi add-on id: {}, query params: {}',
                     self.DIAL_APP_NAME, self.KODI_ADDON_ID, query_params)
        LOGGER.debug('payload: {}', payload)
        LOGGER.debug('additional_data_param: {}', additional_data_param)
        if kodi_ops.is_addon_enabled(self.KODI_ADDON_ID):
            # Todo: start to perform operations with the add-on here
            return DialStatus.RUNNING
        else:
            return DialStatus.ERROR

    def dial_cb_stop(self):
        """Callback used to terminate an application / Kodi add-on"""
        pass

    def dial_cb_status(self):
        """Callback used to check if an application / Kodi add-on is running and update the current state"""
        is_app_terminated = True  # Todo: << check if add-on is running
        return DialStatus.STOPPED if is_app_terminated else DialStatus.RUNNING

    def dial_cb_hide(self):
        """Callback hide - ONLY FOR FUTURE REFERENCE -- DO NOT USE IT"""
        return DialStatus.ERROR_NOT_IMPLEMENTED

    # ---- KODI CALLBACK'S ----
    # TODO: The app will start to receive Kodi callbacks when you call "self.kodi.play_url" and automatically will stop,
    #       warning that these calls come from a different thread, the variables (like dict) should be protected,
    #       all callbacks methods must be kept.
    # The 'data' argument of each Kodi callback can contains a dictionary with
    #   Kodi callback data ref. https://codedocs.xyz/xbmc/xbmc/group__python___player_c_b.html
    #                           https://kodi.wiki/view/JSON-RPC_API/v12
    #   and in addition also some "extra data" see comments below

    def on_playback_started(self, data):
        pass

    def on_playback_tick(self, data):
        """
        Called every (n) secs only when the player is playing,
        to enable this callback set the preferred tick seconds to CB_TICK_SECS
        """
        # Extra data: 'is_playback_paused' - bool True if the player is currently in pause
        pass

    def on_playback_paused(self, data):
        pass

    def on_playback_resumed(self, data):
        pass

    def on_playback_seek(self, data):
        pass

    def on_playback_stopped(self, data):
        # Extra data: 'status' - string the value can be:
        #    stopped - The user has stopped the video
        #    ended - Kodi has stopped the video, usually when the video has reach the end
        #    error - The video has been stopped due to an error
        pass

    def on_volume_changed(self, data):
        pass

    def on_kodi_close(self, data):
        # Extra data:
        #   'was_in_playing' - bool True if Kodi will be closed when in playing (Stop callback not happen),
        #                      NOTE: this key will be sent only to the specified app that has run the playback
        pass
