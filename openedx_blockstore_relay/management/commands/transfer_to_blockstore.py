"""
Transfers a Block and its children from the Open edX modulestore to Blockstore.

Provide either --collection-uuid or --bundle-uuid.
"""
from __future__ import absolute_import, print_function, unicode_literals

import logging
from argparse import ArgumentError
from uuid import UUID

from django.core.management.base import BaseCommand
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import UsageKey

from ...transfer_data import transfer_to_blockstore


class Command(BaseCommand):
    """
    transfer_to_blockstore management command.
    """

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = {}
        self.help = __doc__
        self.logger = logging.getLogger()
        self.args = {}

    def add_arguments(self, parser):
        """
        Add named arguments.
        """
        self.args['block_key'] = parser.add_argument(
            '--block-key',
            type=str,
            required=True,
            metavar='USAGE_KEY',
            help='Usage key of the source Open edX Unit block, '
                 'e.g., "block-v1:edX+DemoX+Demo_Course+type@html+block@030e35c4756a4ddc8d40b95fbbfff4d4"'
        )
        self.args['bundle_uuid'] = parser.add_argument(
            '--bundle-uuid',
            type=str,
            required=False,
            metavar='UUID',
            help='UUID of the an existing Blockstore Bundle -- the block will be uploaded there. '
                 'E.g., "01234567-89ab-cdef-fedc-ba9876543210"'
        )
        self.args['collection_uuid'] = parser.add_argument(
            '--collection-uuid',
            type=str,
            required=False,
            metavar='UUID',
            help='UUID of an existing Blockstore Collection -- a new Bundle will be created for the block. '
                 'e.g., "01234567-89ab-cdef-fedc-ba9876543210"'
        )

    def handle(self, *args, **options):
        """
        Validate the arguments, and start the transfer.
        """
        self.set_logging(options['verbosity'])
        try:
            block_key = UsageKey.from_string(options['block_key'])
        except InvalidKeyError:
            raise ArgumentError(message='Invalid block usage key', argument=self.args['block_key'])
        try:
            bundle_uuid = options.get('bundle_uuid')
            if bundle_uuid:
                bundle_uuid = UUID(bundle_uuid)
        except ValueError:
            raise ArgumentError(message='Invalid bundle UUID', argument=self.args['bundle_uuid'])

        try:
            collection_uuid = options.get('collection_uuid')
            if collection_uuid:
                collection_uuid = UUID(collection_uuid)
        except ValueError:
            raise ArgumentError(message='Invalid collection UUID', argument=self.args['collection_uuid'])

        if bool(collection_uuid) is bool(bundle_uuid):
            raise ArgumentError(message='Either collection OR bundle UUID is required',
                                argument=self.args['collection_uuid'])

        transfer_to_blockstore(block_key=block_key, bundle_uuid=bundle_uuid, collection_uuid=collection_uuid)

    def set_logging(self, verbosity):
        """
        Set the logging level depending on the desired vebosity
        """
        handler = logging.StreamHandler()
        root_logger = logging.getLogger('')
        root_logger.addHandler(handler)
        handler.setFormatter(logging.Formatter('%(levelname)s|%(message)s'))

        if verbosity == 1:
            self.logger.setLevel(logging.WARNING)
        elif verbosity == 2:
            self.logger.setLevel(logging.INFO)
        elif verbosity == 3:
            self.logger.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter('%(name)s|%(asctime)s|%(levelname)s|%(message)s'))
