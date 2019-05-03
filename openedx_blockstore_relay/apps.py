# -*- coding: utf-8 -*-
"""
openedx_blockstore_relay Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig

from openedx.core.djangoapps.plugins.constants import PluginSettings, ProjectType, SettingsType


class OpenEdxBlockstoreRelayAppConfig(AppConfig):
    """
    Configuration for the openedx_blockstore_relay Django plugin application.

    See: https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/plugins/README.rst
    """

    name = 'openedx_blockstore_relay'
    plugin_app = {
        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: 'settings'},
                SettingsType.PRODUCTION: {PluginSettings.RELATIVE_PATH: 'settings'},
            },
            ProjectType.CMS: {
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: 'settings'},
                SettingsType.PRODUCTION: {PluginSettings.RELATIVE_PATH: 'settings'},
            },
        },
    }

    def ready(self):
        """
        Load signal handlers when the app is ready.
        """
        pass
