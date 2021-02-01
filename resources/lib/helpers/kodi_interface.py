# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    An interface to provide a communication between Kodi and a DIAL app

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
import json
import threading
from copy import deepcopy

import xbmc

import resources.lib.helpers.kodi_ops as kodi_ops
from resources.lib.globals import G
from resources.lib.helpers.logging import LOG


class KodiInterface:
    """
    Provides callbacks on Kodi events and methods to obtaining data from Kodi (see 'kodi' variable in app.py)
    """
    def __init__(self, apps):
        self._apps = apps
        self._mutex = threading.Lock()
        # Todo: make event callbacks switchable when we change app with another app
        self._active_app = None
        self.player = Player(self)
        self.monitor = Monitor(self)

    @property
    def active_app(self):
        return self._active_app

    @active_app.setter
    def active_app(self, value):
        self.player._active_app = value
        self._active_app = value

    def play_url(self, app, **kwargs):
        """
        Play a video
        :param app: Specify the DialApp class (use 'self')
        :param kwargs: kwargs to format ADDON_PLAY_PATH string (not mandatory)
        """
        # Before call the add-on to run the video,
        # we must inform our player class interface that we start a video by a DIAL app
        # Todo: make event callbacks switchable when we change app with another app
        if self.active_app is None or (self.active_app and not isinstance(self.active_app, app.__class__)):
            self.active_app = app
        self.player.notify_video_started()
        self.player.play(app.ADDON_PLAY_PATH.format(**kwargs))

    def notify_play(self, app):
        """Notify the interface that will be played a new audio/video content"""
        if self.active_app is None or (self.active_app and not isinstance(self.active_app, app.__class__)):
            self.active_app = app
        self.player.notify_video_started()

    def _notify_apps(self, callback_name, data=None):
        if self._active_app is None:
            LOG.warn('Ignored Kodi callback {}, no app currently active', callback_name)
            return False
        self._mutex.acquire()
        LOG.debug('Notify Kodi callback {} to {} with data: {}', callback_name, self._active_app.DIAL_APP_NAME, data)
        ret = self._execute_notify(self._active_app, callback_name, data)
        self._mutex.release()
        return ret

    def _notify_all_apps(self, callback_name, data=None, extra_data_app=None):
        for _app in self._apps:
            _data = deepcopy(data)
            if extra_data_app[0] == self._active_app:
                # If current app then send extra data only for this app
                _data.update(extra_data_app[1])
            LOG.debug('Notify Kodi callback {} to {} with data: {}', callback_name, _app.DIAL_APP_NAME, _data)
            self._execute_notify(_app, callback_name, _data)

    @staticmethod
    def _execute_notify(app, callback_name, data):
        try:
            method = getattr(app, callback_name)
            method(data)
            return True
        except Exception:  # pylint: disable=broad-except
            LOG.error('The app {} has raised the following error on {} callback:',
                      app.DIAL_APP_NAME, callback_name)
            import traceback
            LOG.error(traceback.format_exc())
            return False

    @staticmethod
    def get_volume():
        """Get the current value of the Kodi volume and mute state"""
        return kodi_ops.json_rpc('Application.GetProperties', {'properties': ['volume', 'muted']})

    @staticmethod
    def set_volume(value):
        """Change the Kodi volume"""
        kodi_ops.json_rpc('Application.SetVolume', {'volume': value})

    @staticmethod
    def set_mute(value):
        """Change the Kodi mute state"""
        kodi_ops.json_rpc('Application.SetMute', {'mute': value})

    @staticmethod
    def show_notification_connected(**kwargs):
        kodi_ops.show_notification(kodi_ops.get_local_string(32000).format(**kwargs))

    @staticmethod
    def show_notification_disconnected(**kwargs):
        kodi_ops.show_notification(kodi_ops.get_local_string(32001).format(**kwargs))

    @property
    def get_ssdp_friendly_name(self):
        return G.SP_FRIENDLY_NAME

    @property
    def get_ssdp_device_uuid(self):
        return G.DEVICE_UUID


class Player(xbmc.Player):
    def __init__(self, kodi_interface: KodiInterface):
        self._kodi_interface = kodi_interface
        self._is_tracking_enabled = False
        self._started_by_app = False
        self._init_count = 0
        self._playback_tick = None
        super().__init__()

    def notify_video_started(self):
        """Notify that a video is started by a call from a DIAL app (see 'play_url' in app.py)"""
        self._started_by_app = True
        self._is_tracking_enabled = True

    def onPlayBackStarted(self):
        """Will be called when Kodi player starts. Video or audio might not be available at this point."""
        if not self._is_tracking_enabled:
            return
        if self._init_count > 0:
            # In this case the user has chosen to play another video while another one is in playing,
            # then we send the missing Stop event for the current video
            self._on_stop('stopped')
        if self._started_by_app:
            self._init_count += 1
            self._started_by_app = False

    def onAVStarted(self):
        """Kodi is actually playing a media file (i.e stream is available)"""
        if not self._is_tracking_enabled:
            return
        self._notify_apps('on_playback_started')
        if (self._kodi_interface.active_app.CB_TICK_SECS is not None
                and (self._playback_tick is None or not self._playback_tick.is_alive())):
            self._playback_tick = PlaybackTick(self._kodi_interface._notify_apps,
                                               self._kodi_interface.active_app.CB_TICK_SECS)
            self._playback_tick.setDaemon(True)
            self._playback_tick.start()

    def onPlayBackPaused(self):
        if not self._is_tracking_enabled:
            return
        self._playback_tick.is_playback_paused = True
        self._kodi_interface._notify_apps('on_playback_paused')

    def onPlayBackResumed(self):
        if not self._is_tracking_enabled:
            return
        # Kodi call this event instead the "Player.OnStop" event when you try to play a video
        # while another one is in playing
        if not self._playback_tick.is_playback_paused:
            return
        self._kodi_interface._notify_apps('on_playback_resumed')
        self._playback_tick.is_playback_paused = False

    def onPlayBackSeek(self, time, seek_offset):
        if not self._is_tracking_enabled:
            return
        self._kodi_interface._notify_apps('on_playback_seek', {'time': time, 'seek_offset': seek_offset})

    def onPlayBackEnded(self):
        """Will be called when Kodi stops playing a file (at the end)"""
        if not self._is_tracking_enabled:
            return
        self._on_stop('ended')

    def onPlayBackStopped(self):
        """Will be called when User stops Kodi playing a file"""
        if not self._is_tracking_enabled:
            return
        self._on_stop('stopped')

    def onPlayBackError(self):
        """Will be called when playback stops due to an error"""
        if not self._is_tracking_enabled:
            return
        self._on_stop('error')

    def _on_stop(self, state):
        if not self._is_tracking_enabled:
            return
        self._init_count -= 1
        if self._init_count == 0:  # If 0 means that no next video will be played from us
            self._is_tracking_enabled = False
        if self._playback_tick and self._playback_tick.is_alive():
            self._playback_tick.stop_join()
            self._playback_tick = None
        self._kodi_interface._notify_apps('on_playback_stopped', {'status': state})

    @property
    def is_in_playing(self):
        """Whether the player is currently playing.
        This is different from `self.isPlaying()`
        in that it returns `False` if the player is paused or otherwise not actively playing."""
        return xbmc.getCondVisibility('Player.Playing')

    @property
    def is_paused(self):
        return xbmc.getCondVisibility("Player.Paused")

    @property
    def is_tracking_enabled(self):
        return self._is_tracking_enabled


class Monitor(xbmc.Monitor):
    def __init__(self, kodi_interface: KodiInterface):
        self._kodi_interface = kodi_interface
        super().__init__()

    def onNotification(self, sender, method, data):
        if method == 'Application.OnVolumeChanged':
            self._kodi_interface._notify_apps('on_volume_changed', json.loads(data))
        elif method == 'System.OnQuit':
            extra_data_app = (self._kodi_interface.active_app,
                              {'was_in_playing': self._kodi_interface.player.is_tracking_enabled})
            self._kodi_interface._notify_all_apps('on_kodi_close', json.loads(data), extra_data_app)


class PlaybackTick(threading.Thread):
    """Thread to send a notification every (n) secs of playback"""
    def __init__(self, notify_apps, timeout_secs):
        self._notify_apps = notify_apps
        self._timeout_secs = timeout_secs
        self._stop_event = threading.Event()
        self.is_playback_paused = False
        super().__init__()

    def run(self):
        while not self._stop_event.is_set():
            if not self._notify_apps('on_playback_tick', {'is_playback_paused': self.is_playback_paused}):
                LOG.warn('PlaybackTick: Interrupted due to an error')
                break
            if self._stop_event.wait(self._timeout_secs):
                break  # Stop requested by stop_join

    def stop_join(self):
        self._stop_event.set()
        self.join()
