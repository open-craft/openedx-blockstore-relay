"""
Common settings for the openedx-blockstore-relay app.

See apps.py for details on how this sort of plugin configures itself for
integration with Open edX.
"""
from __future__ import absolute_import, print_function, unicode_literals
from os.path import sep as path_separator

# Declare defaults: ############################################################

BLOCKSTORE_API_URL = 'http://edx.devstack.blockstore:18250/api/v1/'
# Append trailing slash
if not BLOCKSTORE_API_URL.endswith(path_separator):
    BLOCKSTORE_API_URL = '{}{}'.format(BLOCKSTORE_API_URL, path_separator)

# Register settings: ###########################################################


def plugin_settings(settings):
    """
    Add our default settings to the edx-platform settings. Other settings files
    may override these values later, e.g. via envs/private.py.
    """
    settings.BLOCKSTORE_API_URL = BLOCKSTORE_API_URL
