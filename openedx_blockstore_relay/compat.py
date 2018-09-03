"""
Code used to interface with edx-platform.

This needs to be stubbed out for tests.  If a module, `caller` calls:

    from openedx_blockstore_relay import compat

It can be stubbed out using:

    import test_utils.compat
    mock.patch('caller.compat', test_utils.compat.StubCompat())

`StubCompat` is a class which implements all the below methods in a way that
eliminates external dependencies
"""
from __future__ import absolute_import, unicode_literals

import logging

LOG = logging.getLogger(__name__)


class EdXPlatformImportError(ImportError):
    """
    Custom exception class to explain ImportErrors from edx-platform code.
    """

    def __init__(self, import_error):
        """
        Construct a message from the given import_error's message.
        """
        message = 'Must run inside an edx-platform virtualenv: {}'.format(import_error.message)
        super(EdXPlatformImportError, self).__init__(message)


def get_block(usage_key):
    """
    Return block from the modulestore.
    """
    try:
        from xmodule.modulestore.django import modulestore as store
    except ImportError as exc:
        raise EdXPlatformImportError(exc)

    return store().get_item(usage_key)


def get_asset_content_from_path(course_key, asset_path):
    """
    Locate the given asset content, load it into memory, and return it.

    Returns None if the asset is not found.
    """
    try:
        from xmodule.contentstore.content import StaticContent
        from xmodule.assetstore.assetmgr import AssetManager
        from xmodule.modulestore.exceptions import ItemNotFoundError
        from xmodule.exceptions import NotFoundError
    except ImportError as exc:
        raise EdXPlatformImportError(exc)

    try:
        asset_key = StaticContent.get_asset_key_from_path(course_key, asset_path)
        return AssetManager.find(asset_key)
    except (ItemNotFoundError, NotFoundError) as exc:
        return None


def collect_assets_from_text(text, course_id):
    """
    Yield dicts of asset content and path from static asset paths found in the given text.
    """
    try:
        from static_replace import replace_static_urls
    except ImportError as exc:
        raise EdXPlatformImportError(exc)

    static_paths = []
    replace_static_urls(text=text, course_id=course_id, static_paths=static_paths)
    for (path, uri) in static_paths:
        content = get_asset_content_from_path(course_id, path)
        if content is None:
            LOG.error("Static asset not found: (%s, %s)", path, uri)
        else:
            yield {'content': content, 'path': path}


def collect_assets_from_video_block(block):
    """
    Trapse through the guts of the Video XBlock to dredge up the translation assets.

    Yield dicts containing the content and filename for each asset found in contentstore.

    Pieced together from code found in xmodule.video_module.transcripts_utils.
    """
    try:
        from xmodule.video_module.transcripts_utils import get_transcript, Transcript
        from xmodule.contentstore.content import StaticContent
        from xmodule.exceptions import NotFoundError
    except ImportError as exc:
        raise EdXPlatformImportError(exc)

    if hasattr(block, 'get_transcripts_info'):
        output_format = Transcript.SJSON
        transcripts = block.get_transcripts_info()
        sub, other_langs = transcripts["sub"], transcripts["transcripts"]
        all_langs = dict(**other_langs)
        if sub:
            all_langs.update({'en': sub})

        for language in all_langs:
            filename = all_langs[language]
            try:
                (data, transcript_name, mimetype) = get_transcript(block,
                                                                   lang=language,
                                                                   output_format=output_format)
                if data:
                    content = StaticContent(transcript_name, filename, mimetype, data)
                    yield {
                        'content': content,
                        'path': transcript_name,
                    }

            except NotFoundError:
                LOG.warning("No transcript found for lang=%s, filename=%s (%s)", language, filename, block.location)
                continue
    else:
        LOG.error("Unable to run video get_transcripts_info (%s)", block.location)
