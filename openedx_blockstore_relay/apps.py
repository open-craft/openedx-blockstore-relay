# -*- coding: utf-8 -*-
"""
openedx_blockstore_relay Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class OpenEdxBlockstoreRelayAppConfig(AppConfig):
    """
    Configuration for the openedx_blockstore_relay Django plugin application.

    See: https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/plugins/README.rst
    """

    name = 'openedx_blockstore_relay'
    plugin_app = {
        'url_config': {
            'lms.djangoapp': {
                'namespace': 'blockstore_relay',
                'app_name': 'blockstore_relay',
                'regex': r'^blockstore_relay/',
                'relative_path': 'urls',
            },
            'cms.djangoapp': {
                'namespace': 'blockstore_relay',
                'app_name': 'blockstore_relay',
                'regex': r'^blockstore_relay/',
                'relative_path': 'urls',
            },
        },
        'settings_config': {
            'lms.djangoapp': {
                'common': {'relative_path': 'settings.common'},
                'aws': {'relative_path': 'settings.production'},
            },
            'cms.djangoapp': {
                'common': {'relative_path': 'settings.common'},
                'aws': {'relative_path': 'settings.production'},
            },
        },
    }

    def ready(self):
        """
        Load signal handlers when the app is ready.
        """
        pass
