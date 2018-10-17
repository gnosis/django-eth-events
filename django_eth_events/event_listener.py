from ethereum.utils import checksum_encode
from json import dumps, loads
from typing import Set

from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.utils.module_loading import import_string

from .decoder import Decoder
from .exceptions import InvalidAddressException
from .models import Block, Daemon
from .reorgs import check_reorg
from .utils import (JsonBytesEncoder, normalize_address_without_0x, remove_0x_head)
from .web3_service import Web3Service

logger = get_task_logger(__name__)


class SingletonListener(object):
    """
    Singleton class decorator for EventListener
    """
    def __init__(self, klass):
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kwargs):
        contract_map = kwargs.get('contract_map', None)
        provider = kwargs.get('provider', None)

        different_provider = self.instance and provider and not isinstance(provider, self.instance.provider.__class__)
        different_contract = self.instance and contract_map and (contract_map != self.instance.original_contract_map)

        if different_provider or different_contract:
            self.instance = self.klass(contract_map=contract_map, provider=provider)
        elif not self.instance:
            # In Python 3.4+ is not allowed to send args to __new__ if __init__
            # is defined
            # cls._instance = super().__new__(cls, *args, **kwargs)
            self.instance = self.klass(contract_map=contract_map, provider=provider)
        return self.instance


@SingletonListener
class EventListener(object):
    max_blocks_to_backup = settings.ETH_BACKUP_BLOCKS
    max_blocks_to_process = settings.ETH_PROCESS_BLOCKS
    blocks_to_process_with_filters = settings.ETH_FILTER_PROCESS_BLOCKS

    def __init__(self, contract_map=None, provider=None):
        self.web3_service = Web3Service(provider=provider)
        self.web3 = self.web3_service.web3  # Gets transaction and block info from ethereum

        if not contract_map:
            # Taken from settings, it's the contracts we listen to
            contract_map = settings.ETH_EVENTS

        self.original_contract_map = contract_map
        self.contract_map = self.parse_contract_map(contract_map) if contract_map else contract_map

        # Decodes Ethereum logs
        self.decoder = Decoder()

        # Prepare decoder for contracts
        for contract in self.contract_map:
            self.decoder.add_abi(contract['EVENT_ABI'])

    @property
    def provider(self):
        return self.web3_service.main_provider

    @staticmethod
    def import_class_from_string(class_string):
        try:
            return import_string(class_string)
        except ImportError as err:
            logger.error("Cannot load class for contract: %s", err.msg)
            raise err

    def get_current_block_number(self):
        return self.web3_service.get_current_block_number()

    @staticmethod
    def next_block(cls):
        return Daemon.get_solo().block_number

    def parse_contract_map(self, contract_map):
        """
        Resolves contracts string to their corresponding classes
        :param contract_map: list of dictionaries
        :return: parsed list of dictionaries
        """

        # Check no names repeated in contracts
        names = set()
        contracts_parsed = []
        for contract in contract_map:
            name = contract.get('NAME')
            if not name:
                logger.error("Missing `NAME` for event listener")
                raise ValueError
            else:
                if name in names:
                    logger.error("Duplicated `NAME` %s for event listener", name)
                    raise ValueError
                else:
                    names.add(name)

            contract_parsed = contract.copy()
            # Parse addresses (normalize and remove 0x). Throws exception if address is invalid
            if 'ADDRESSES' in contract:
                contract_parsed['ADDRESSES'] = []
                for address in contract['ADDRESSES']:
                    # TODO Wait for web3 to fix it https://github.com/ethereum/web3.py/issues/715
                    if self.web3.isAddress('0x' + remove_0x_head(address)):
                        contract_parsed['ADDRESSES'].append(normalize_address_without_0x(address))
                    else:
                        logger.error("Address %s is not valid", address)
                        raise InvalidAddressException(address)

                    # Remove duplicated
                    contract_parsed['ADDRESSES'] = list(set(contract_parsed['ADDRESSES']))

            if 'ADDRESSES_GETTER' in contract:
                contract_parsed['ADDRESSES_GETTER_CLASS'] = self.import_class_from_string(contract['ADDRESSES_GETTER'])()
            contract_parsed['EVENT_DATA_RECEIVER_CLASS'] = self.import_class_from_string(contract['EVENT_DATA_RECEIVER'])()
            contracts_parsed.append(contract_parsed)
        return contracts_parsed

    def get_next_mined_block_numbers(self, daemon_block_number, current_block_number):
        """
        Returns a range with the block numbers of blocks mined since last event_listener execution
        :return: iter(int)
        """
        logger.debug('Blocks mined, daemon-block-number=%d node-block-number=%d',
                     daemon_block_number, current_block_number)
        if daemon_block_number < current_block_number:
            if current_block_number - daemon_block_number > self.max_blocks_to_process:
                blocks_to_update = range(daemon_block_number + 1, daemon_block_number + self.max_blocks_to_process)
            else:
                blocks_to_update = range(daemon_block_number + 1, current_block_number + 1)
            return blocks_to_update
        else:
            return range(0)

    def get_watched_contract_addresses(self, contract) -> Set[str]:
        addresses = None
        try:
            if contract.get('ADDRESSES'):
                addresses = contract['ADDRESSES']
            elif contract.get('ADDRESSES_GETTER_CLASS'):
                addresses = contract['ADDRESSES_GETTER_CLASS'].get_addresses()
        except Exception as e:
            raise LookupError("Could not retrieve watched addresses for contract {}".format(contract['NAME'])) from e

        normalized_addresses = {checksum_encode(address) for address in addresses}
        return normalized_addresses

    @transaction.atomic
    def save_event(self, contract, decoded_log, block_info):
        event_receiver = contract['EVENT_DATA_RECEIVER_CLASS']
        return event_receiver.save(decoded_event=decoded_log, block_info=block_info)

    @transaction.atomic
    def revert_events(self, event_receiver_string, decoded_event, block_info):
        EventReceiver = import_string(event_receiver_string)
        EventReceiver().rollback(decoded_event=decoded_event, block_info=block_info)

    @transaction.atomic
    def rollback(self, daemon, block_number):
        """
        Rollback blocks and set daemon block_number to current one
        :param daemon:
        :param block_number:
        :return:
        """
        # get all blocks to rollback
        blocks = Block.objects.filter(block_number__gt=block_number).order_by('-block_number')
        logger.warning('Rolling back %d blocks, until block-number=%d', blocks.count(), block_number)
        for block in blocks:
            decoded_logs = loads(block.decoded_logs)
            logger.warning('Rolling back %d block and %d logs', block.block_number, len(decoded_logs))
            if len(decoded_logs):
                # We loop decoded logs on inverse order because there might be dependencies inside the same block
                # And must be processed from last applied to first applied
                for log in reversed(decoded_logs):
                    event = log['event']
                    block_info = {
                        'hash': block.block_hash,
                        'number': block.block_number,
                        'timestamp': block.timestamp
                    }
                    self.revert_events(log['event_receiver'], event, block_info)

        # Remove backups from future blocks (old chain)
        blocks.delete()

        # set daemon block_number to current one
        daemon.block_number = block_number
        daemon.save()

    def backup(self, block_hash, block_number, timestamp, decoded_event,
               event_receiver_string):
        # Get block or create new one
        block, _ = Block.objects.get_or_create(block_hash=block_hash,
                                               defaults={'block_number': block_number,
                                                         'timestamp': timestamp}
                                               )

        saved_logs = loads(block.decoded_logs)
        saved_logs.append({'event_receiver': event_receiver_string,
                           'event': decoded_event})

        block.decoded_logs = dumps(saved_logs, cls=JsonBytesEncoder)
        block.save()

    @transaction.atomic
    def backup_blocks(self, prefetched_blocks, last_block_number):
        """
        Backup block at batch if haven't been backed up (no logs, but we saved the hash for reorg checking anyway)
        :param prefetched_blocks: Every prefetched block
        :param last_block_number: Number of last block mined
        :return:
        """
        blocks_to_backup = []
        block_numbers_to_delete = []
        for block_number, prefetched_block in prefetched_blocks.items():
            if (block_number - last_block_number) < self.max_blocks_to_backup:
                blocks_to_backup.append(
                    Block(
                        block_number=block_number,
                        block_hash=remove_0x_head(prefetched_block['hash']),
                        timestamp=prefetched_block['timestamp'],
                    )
                )
                block_numbers_to_delete.append(block_number)
        Block.objects.filter(block_number__in=block_numbers_to_delete).delete()
        return Block.objects.bulk_create(blocks_to_backup)

    def clean_useless_blocks_backup(self, daemon_block_number):
        """
        If there's an error during block processing, some blocks will be stored and will be detected
        as a reorg, so this method will clean blocks stored with bigger block number than daemon block number
        :param daemon_block_number:
        :return:
        """
        return Block.objects.filter(
            block_number__gt=daemon_block_number
        ).delete()

    def clean_old_blocks_backup(self, daemon_block_number):
        return Block.objects.filter(
            block_number__lt=daemon_block_number - self.max_blocks_to_backup
        ).delete()

    @transaction.atomic
    def execute_with_filters(self, daemon: Daemon, end_block: int):
        start_block = daemon.block_number

        logger.info('Sync with filters, start-block=%d - end-block=%d', start_block, end_block)

        # Store addresses with retrieved logs
        block_number_with_logs = {}

        # Cache for contracts that need access to database
        contract_address_cache = {}

        # Every contract address. They will be used to know which blocks have to be retrieved for sure
        contract_addresses = set()
        block_numbers_to_be_prefetched = set()
        for contract in self.contract_map:
            contract_addresses.update(self.get_watched_contract_addresses(contract))

        # Load logs for every event
        events = self.decoder.events
        for event in events:
            logger.info('Using filter to get logs for event=%s from block=%d to block=%d',
                        event,
                        start_block,
                        end_block)
            logs = self.web3_service.get_logs_for_event_using_filter(start_block, end_block, event)
            logger.info('Found %d logs for event=%s', len(logs), event)
            for log in logs:
                block_number = log['blockNumber']
                block_number_with_logs.setdefault(block_number, []).append(log)
                if log['address'] in contract_addresses:
                    block_numbers_to_be_prefetched.add(block_number)

        logger.info('Start prefetching of %d blocks', len(block_numbers_to_be_prefetched))
        prefetched_blocks = self.web3_service.get_blocks(list(block_numbers_to_be_prefetched))
        logger.info('End block prefetching')

        # Start in the first block with logs.
        # For example, if we start in block 5 but no logs are found until 200, we start in the 200
        new_start_block = max(min(block_number_with_logs), start_block) if block_number_with_logs else end_block
        if new_start_block != start_block:
            logger.info('No logs found from block=%d to block=%d, so starting in block=%d',
                        start_block, new_start_block, new_start_block)

        for block_number in range(new_start_block, end_block):
            logger.debug('Processing block %d', block_number)
            logs = block_number_with_logs.get(block_number)
            if not logs:
                continue

            # Don't load block if not needed, can be `None` if not prefetched
            current_block = prefetched_blocks.get(block_number)

            ###########################
            # Decode logs #
            ###########################
            for contract in self.contract_map:
                # Query cache before retrieving contract addresses from database
                if contract['NAME'] not in contract_address_cache:
                    contract_address_cache[contract['NAME']] = self.get_watched_contract_addresses(contract)
                watched_addresses = contract_address_cache[contract['NAME']]

                # Filter logs by relevant addresses
                target_logs = [log for log in logs if log['address'] in watched_addresses]

                if target_logs:
                    logger.info('Contract=%s Block=%d -> Found %d relevant logs',
                                contract['NAME'],
                                block_number,
                                len(target_logs))

                decoded_logs = self.decoder.decode_logs(target_logs)

                if decoded_logs:
                    logger.info('Contract=%s Block=%d -> Decoded %d relevant logs',
                                contract['NAME'],
                                block_number,
                                len(decoded_logs))

                    # Save events
                    for decoded_log in decoded_logs:
                        # Fetch block if not recovered yet
                        if not current_block:
                            current_block = self.web3_service.get_block(block_number)

                        instance = self.save_event(contract, decoded_log, current_block)

                        # Only valid data is saved in backup
                        if instance is not None:
                            # Clear cache, maybe new addresses are stored
                            contract_address_cache.clear()

                            if (end_block - block_number) < self.max_blocks_to_backup:
                                self.backup(
                                    remove_0x_head(current_block['hash']),
                                    current_block['number'],
                                    current_block['timestamp'],
                                    decoded_log,
                                    contract['EVENT_DATA_RECEIVER']
                                )

                    logger.info('Contract=%s Block=%d -> Processed %d relevant logs',
                                contract['NAME'],
                                block_number,
                                len(decoded_logs))

            daemon.block_number = block_number
            logger.debug('Ended processing of block_number=%d', block_number)

        daemon.block_number = end_block
        daemon.save()

    def execute(self):
        """
        :raises: Web3ConnectionException
        """

        # When we have address getters caching can save us a lot of time
        contract_address_cache = {}

        daemon = Daemon.get_solo()
        if not daemon.is_executing():
            return

        self.clean_useless_blocks_backup(daemon.block_number)
        current_block_number = self.web3_service.get_current_block_number()

        # Use filters for first sync
        if (current_block_number - daemon.block_number) > self.max_blocks_to_backup:
            self.clean_old_blocks_backup(daemon.block_number)
            return self.execute_with_filters(daemon,
                                             min(daemon.block_number + self.blocks_to_process_with_filters,
                                                 current_block_number - self.max_blocks_to_backup)
                                             )

        had_reorg, reorg_block_number = check_reorg(daemon.block_number,
                                                    current_block_number,
                                                    provider=self.provider)
        if had_reorg:
            # Daemon block_number could be modified
            self.rollback(daemon, reorg_block_number)

        # Get block numbers of next mined blocks not processed yet
        next_mined_block_numbers = self.get_next_mined_block_numbers(daemon_block_number=daemon.block_number,
                                                                     current_block_number=current_block_number)
        if not next_mined_block_numbers:
            logger.info('No blocks mined, daemon-block-number=%d, node-block-number=%d',
                        daemon.block_number,
                        current_block_number)
        else:
            logger.info('Blocks mined from %d to %d, prefetching %d blocks, daemon-block-number=%d',
                        next_mined_block_numbers[0],
                        next_mined_block_numbers[-1],
                        len(next_mined_block_numbers),
                        daemon.block_number)

            last_mined_block_number = next_mined_block_numbers[-1]
            prefetched_blocks = self.web3_service.get_blocks(next_mined_block_numbers)
            logger.debug('Finished blocks prefetching')

            logger.info('Start log prefetching')
            prefetched_logs = self.web3_service.get_logs_for_blocks(prefetched_blocks.values())
            logger.info('End log prefetching')

            self.backup_blocks(prefetched_blocks, last_mined_block_number)
            logger.debug('Finished blocks backup')

            for current_block_number in next_mined_block_numbers:
                self.process_block(daemon,
                                   prefetched_blocks[current_block_number],
                                   prefetched_logs[current_block_number],
                                   current_block_number,
                                   last_mined_block_number,
                                   contract_address_cache)

            # Remove older backups
            self.clean_old_blocks_backup(daemon.block_number)

            logger.info('Ended processing of chunk, daemon-block-number=%d', daemon.block_number)

    @transaction.atomic
    def process_block(self, daemon, current_block, logs, current_block_number, last_mined_block_number,
                      contract_address_cache):
        # logger.debug('Getting every log for block_number=%d', current_block['number'])
        # logs = self.web3_service.get_logs(current_block)
        logger.debug('Got %d logs in block_number=%d', len(logs), current_block['number'])

        ###########################
        # Decode logs #
        ###########################
        if logs:
            for contract in self.contract_map:

                # Get watched contract addresses
                if contract['NAME'] not in contract_address_cache:
                    contract_address_cache[contract['NAME']] = self.get_watched_contract_addresses(contract)
                watched_addresses = contract_address_cache[contract['NAME']]

                # Filter logs by relevant addresses
                target_logs = [log for log in logs if self.web3.toChecksumAddress(log['address']) in watched_addresses]

                if target_logs:
                    logger.info('Found %d relevant logs in block %d', len(target_logs), current_block_number)

                # Decode logs
                decoded_logs = self.decoder.decode_logs(target_logs)

                if decoded_logs:
                    # Clear cache, maybe new addresses are stored
                    contract_address_cache.clear()

                    logger.info('Decoded %d relevant logs in block %d', len(decoded_logs), current_block_number)

                    for log in decoded_logs:
                        # Save events
                        instance = self.save_event(contract, log, current_block)

                        # Only valid data is saved in backup
                        if instance is not None:
                            if (current_block_number - last_mined_block_number) < self.max_blocks_to_backup:
                                self.backup(
                                    remove_0x_head(current_block['hash']),
                                    current_block['number'],
                                    current_block['timestamp'],
                                    log,
                                    contract['EVENT_DATA_RECEIVER']
                                )

                    logger.info('Processed %d relevant logs in block %d', len(decoded_logs), current_block_number)

        daemon.block_number = current_block_number
        # Make changes persistent, update block_number
        daemon.save()
        logger.debug('Ended processing of block_number=%d', current_block['number'])
