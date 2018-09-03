"""
Common settings for the openedx-blockstore-relay app.
"""

from __future__ import absolute_import, unicode_literals

from os.path import sep as path_separator

USE_TZ = True
USE_I18N = True

INSTALLED_APPS = ()

ROOT_URLCONF = 'openedx_blockstore_relay.urls'

SECRET_KEY = 'insecure-secret-key'

BLOCKSTORE_API_URL = 'http://localhost:8888/api/v1'

# Apply private settings overrides
try:
    from .private import *  # pylint: disable=wildcard-import
except ImportError:
    pass


# Append trailing slash
if not BLOCKSTORE_API_URL.endswith(path_separator):
    BLOCKSTORE_API_URL = '{}{}'.format(BLOCKSTORE_API_URL, path_separator)


def plugin_settings(settings):
    """
    Passes specific settings when app is used as a plugin to edx-platform.
    See: https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/plugins/README.rst
    """
    settings.BLOCKSTORE_API_URL = BLOCKSTORE_API_URL
