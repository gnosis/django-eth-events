from json import dumps, loads
import socket

from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils.module_loading import import_string

from .decoder import Decoder
from .exceptions import (UnknownBlock, UnknownTransaction,
                         Web3ConnectionException)
from .models import Block, Daemon
from .reorgs import check_reorg
from .utils import (JsonBytesEncoder, normalize_address_without_0x,
                    remove_0x_head)
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
            # cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
            self.instance = self.klass(contract_map=contract_map, provider=provider)
        return self.instance


@SingletonListener
class EventListener(object):

    def __init__(self, contract_map=None, provider=None):
        self.decoder = Decoder()  # Decodes Ethereum logs
        self.web3 = Web3Service(provider=provider).web3  # Gets transaction and block info from ethereum

        if not contract_map:
            # Taken from settings, it's the contracts we listen to
            contract_map = settings.ETH_EVENTS

        self.original_contract_map = contract_map
        self.contract_map = self.parse_contract_map(contract_map) if contract_map else contract_map

    def parse_contract_map(self, contract_map):
        """
        Resolves contracts string to their corresponding classes
        :param contract_map: list of dictionaries
        :return: parsed list of dictionaries
        """
        contracts_parsed = []
        for contract in contract_map:
            contract_parsed = contract.copy()
            if 'ADDRESSES_GETTER' in contract:
                contract_parsed['ADDRESSES_GETTER_CLASS'] = self.import_class_from_string(contract['ADDRESSES_GETTER'])
            contract_parsed['EVENT_DATA_RECEIVER_CLASS'] = self.import_class_from_string(contract['EVENT_DATA_RECEIVER'])
            contracts_parsed.append(contract_parsed)
        return contracts_parsed

    def import_class_from_string(self, class_string):
        try:
            return import_string(class_string)
        except ImportError as err:
            logger.error("Cannot load class for contract: {}", err.msg)
            raise err

    @property
    def provider(self):
        return self.web3.providers[0]

    def get_current_block_number(self):
        try:
            return self.web3.eth.blockNumber
        except Exception as e:
            try:
                if not self.web3.isConnected():
                    raise Web3ConnectionException('Web3 provider is not connected')
                else:
                    raise e
            except socket.timeout:
                raise Web3ConnectionException('Web3 provider is not connected. Socket timeout')

    @staticmethod
    def next_block(cls):
        return Daemon.get_solo().block_number

    def get_last_mined_blocks(self, daemon_block_number, current_block_number):
        """
        Returns a range with the block numbers of blocks mined since last event_listener execution
        :return: [int]
        """
        logger.info('Blocks mined, daemon: {} current: {}'.format(daemon_block_number, current_block_number))
        if daemon_block_number < current_block_number:
            max_blocks_to_process = int(getattr(settings, 'ETH_PROCESS_BLOCKS', '10000'))
            if current_block_number - daemon_block_number > max_blocks_to_process:
                blocks_to_update = range(daemon_block_number + 1, daemon_block_number + max_blocks_to_process)
            else:
                blocks_to_update = range(daemon_block_number + 1, current_block_number + 1)
            return blocks_to_update
        else:
            return range(0)

    def update_block_number(self, daemon, block_number):
        logger.info('Update daemon block_number={}'.format(block_number))
        daemon.block_number = block_number
        daemon.save()

    def get_logs(self, block_number):
        """
        By a given block number returns a pair logs, block_info
        logs it's an array of decoded ethereum log dictionaries
        and block info it's a dic
        :param block_number:
        :return:
        """
        try:
            block = self.web3.eth.getBlock(block_number)
        except:
            try:
                if not self.web3.isConnected():
                    raise Web3ConnectionException('Web3 provider is not connected')
                else:
                    raise UnknownBlock
            except socket.timeout:
                raise Web3ConnectionException('Web3 provider is not connected. Socket timeout')

        logs = []

        if block and block.get('hash'):
            for tx in block['transactions']:
                # receipt sometimes is none, might be because a reorg, we exit the loop with a controlled exception
                try:
                    receipt = self.web3.eth.getTransactionReceipt(tx)
                except:
                    try:
                        if not self.web3.isConnected():
                            raise Web3ConnectionException('Web3 provider is not connected')
                        else:
                            raise UnknownTransaction
                    except socket.timeout:
                        raise Web3ConnectionException('Web3 provider is not connected. Socket timeout')

                if receipt is None:
                    raise UnknownTransaction
                if receipt.get('logs'):
                    logs.extend(receipt['logs'])
            return logs, block
        else:
            raise UnknownBlock

    def get_watched_contract_addresses(self, contract):
        addresses = None
        try:
            if contract.get('ADDRESSES'):
                addresses = contract['ADDRESSES']
            elif contract.get('ADDRESSES_GETTER_CLASS'):
                addresses_getter = contract['ADDRESSES_GETTER_CLASS']
                addresses = addresses_getter().get_addresses()
        except Exception as e:
            logger.error(e)
            raise LookupError("Could not retrieve watched addresses for contract {}".format(contract))

        normalized_addresses = [normalize_address_without_0x(address)
                                for address in addresses]
        return normalized_addresses

    def save_event(self, contract, decoded_log, block_info):
        EventReceiver = contract['EVENT_DATA_RECEIVER_CLASS']
        instance = EventReceiver().save(decoded_event=decoded_log, block_info=block_info)
        return instance

    def revert_events(self, event_receiver_string, decoded_event, block_info):
        EventReceiver = import_string(event_receiver_string)
        EventReceiver().rollback(decoded_event=decoded_event, block_info=block_info)

    def rollback(self, daemon, block_number):
        """
        Rollback blocks and set daemon block_number to current one
        :param daemon:
        :param block_number:
        :return:
        """
        # get all blocks to rollback
        blocks = Block.objects.filter(block_number__gt=block_number).order_by('-block_number')
        logger.warning('Rolling back {} blocks, until block number {}'.format(blocks.count(), block_number))
        for block in blocks:
            decoded_logs = loads(block.decoded_logs)
            logger.warning('Rolling back {} block, {} logs'.format(block.block_number, len(decoded_logs)))
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
        self.update_block_number(daemon, block_number)

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

    def clean_old_backups(self, daemon_block_number):
        max_blocks_backup = int(getattr(settings, 'ETH_BACKUP_BLOCKS', '100'))
        return Block.objects.filter(block_number__lt=daemon_block_number-max_blocks_backup).delete()

    def execute(self):
        """
        :raises: Web3ConnectionException
        """
        # Check daemon status
        daemon = Daemon.get_solo()
        if daemon.status == 'EXECUTING':
            current_block_number = self.get_current_block_number()
            # Check reorg
            had_reorg, reorg_block_number = check_reorg(daemon.block_number,
                                                        current_block_number,
                                                        provider=self.provider)

            if had_reorg:
                # Daemon block_number could be modified
                self.rollback(daemon, reorg_block_number)

            # Get block numbers of last mined blocks not processed yet
            last_mined_blocks = self.get_last_mined_blocks(daemon_block_number=daemon.block_number,
                                                           current_block_number=current_block_number)
            if last_mined_blocks:
                logger.info('{} blocks mined from {} to {}'.format(len(last_mined_blocks),
                                                                   last_mined_blocks[0],
                                                                   last_mined_blocks[-1]))
            else:
                logger.info('No blocks mined')
            for block in last_mined_blocks:
                # first get un-decoded logs and the block info
                logs, block_info = self.get_logs(block)
                logger.info('Got {} logs in block {}'.format(len(logs), block_info['number']))

                ###########################
                # Decode logs #
                ###########################
                if len(logs):
                    for contract in self.contract_map:
                        # Add ABI
                        self.decoder.add_abi(contract['EVENT_ABI'])

                        # Get watched contract addresses
                        # TODO Use set to search by index instead of in list (O(1) vs O(n))
                        watched_addresses = self.get_watched_contract_addresses(contract)

                        # Filter logs by relevant addresses
                        target_logs = [log for log in logs if
                                       normalize_address_without_0x(log['address']) in watched_addresses]

                        logger.info('{} logs'.format(len(target_logs)))

                        # Decode logs
                        decoded_logs = self.decoder.decode_logs(target_logs)

                        logger.info('{} decoded logs'.format(len(decoded_logs)))

                        if len(decoded_logs):
                            for log in decoded_logs:
                                # Save events
                                instance = self.save_event(contract, log, block_info)

                                # Only valid data is saved in backup
                                if instance is not None:
                                    max_blocks_to_backup = int(getattr(settings, 'ETH_BACKUP_BLOCKS', '100'))
                                    if (block - last_mined_blocks[-1]) < max_blocks_to_backup:
                                        self.backup(
                                            remove_0x_head(block_info['hash']),
                                            block_info['number'],
                                            block_info['timestamp'],
                                            log,
                                            contract['EVENT_DATA_RECEIVER']
                                        )

                # TODO refactor to be faster
                daemon.block_number = block
                daemon.save()

                max_blocks_to_backup = int(getattr(settings, 'ETH_BACKUP_BLOCKS', '100'))
                if (block - last_mined_blocks[-1]) < max_blocks_to_backup:
                    # backup block if haven't been backed up (no logs, but we saved the hash for reorg checking anyway)
                    Block.objects.get_or_create(
                        block_number=block,
                        block_hash=remove_0x_head(block_info['hash']),
                        defaults={'timestamp': block_info['timestamp']}
                    )

            if len(last_mined_blocks):
                # Update block number after execution
                self.update_block_number(daemon, last_mined_blocks[-1])

                # Remove older backups
                self.clean_old_backups(daemon.block_number)
