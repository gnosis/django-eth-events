from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils.module_loading import import_string

from django_eth_events.decoder import Decoder
from django_eth_events.models import Daemon, Block
from django_eth_events.web3_service import Web3Service
from django_eth_events.reorgs import check_reorg
from django_eth_events.utils import (JsonBytesEncoder,
                                     remove_0x_head,
                                     normalize_address_without_0x)

from json import dumps, loads

logger = get_task_logger(__name__)


class UnknownBlock(Exception):
    pass


class UnknownTransaction(Exception):
    pass


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

        if provider and self.instance and not isinstance(provider, self.instance.provider.__class__):
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
            contract_map = settings.ETH_EVENTS

        self.contract_map = contract_map  # Taken from settings, it's the contracts we listen to
        self.provider = provider

    @staticmethod
    def next_block(self):
        return Daemon.get_solo().block_number

    def get_last_mined_blocks(self):
        """
        Returns the block numbers of blocks mined since last event_listener execution
        :return: [int]
        """
        daemon = Daemon.get_solo()
        current = self.web3.eth.blockNumber

        logger.info('blocks mined, daemon: {} current: {}'.format(daemon.block_number, current))
        if daemon.block_number < current:
            max_blocks_to_process = int(getattr(settings, 'ETH_PROCESS_BLOCKS', '10000'))
            if current - daemon.block_number > max_blocks_to_process:
                blocks_to_update = range(daemon.block_number + 1, daemon.block_number + max_blocks_to_process)
            else:
                blocks_to_update = range(daemon.block_number + 1, current + 1)
            return blocks_to_update
        else:
            return []

    def update_block_number(self, block_number):
        daemon = Daemon.get_solo()
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
            raise UnknownBlock
        logs = []

        if block and block.get(u'hash'):
            for tx in block[u'transactions']:
                # receipt sometimes is none, might be because a reorg, we exit the loop with a controlled exeception
                try:
                    receipt = self.web3.eth.getTransactionReceipt(tx)
                except:
                    raise UnknownTransaction
                if receipt is None:
                    raise UnknownTransaction
                if receipt.get('logs'):
                    logs.extend(receipt[u'logs'])
            return logs, block
        else:
            raise UnknownBlock

    def get_watched_contract_addresses(self, contract):
        addresses = None
        try:
            if contract.get('ADDRESSES'):
                addresses = contract['ADDRESSES']
            elif contract.get('ADDRESSES_GETTER'):
                addresses_getter = import_string(contract['ADDRESSES_GETTER'])
                addresses = addresses_getter().get_addresses()
        except Exception as e:
            logger.error(e)
            raise LookupError("Could not retrieve watched addresses for contract {}".format(contract))

        normalized_addresses = [normalize_address_without_0x(address)
                                for address in addresses]
        return normalized_addresses

    def save_event(self, contract, decoded_log, block_info):
        EventReceiver = import_string(contract['EVENT_DATA_RECEIVER'])
        instance = EventReceiver().save(decoded_event=decoded_log, block_info=block_info)
        return instance

    def revert_events(self, event_receiver_string, decoded_event, block_info):
        EventReceiver = import_string(event_receiver_string)
        EventReceiver().rollback(decoded_event=decoded_event, block_info=block_info)

    def rollback(self, block_number):
        # get all blocks to rollback
        blocks = Block.objects.filter(block_number__gt=block_number).order_by('-block_number')
        logger.info('rolling back {} blocks, until block number {}'.format(blocks.count(), block_number))
        for block in blocks:
            decoded_logs = loads(block.decoded_logs)
            logger.info('rolling back {} block, {} logs'.format(block.block_number, len(decoded_logs)))
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
        daemon = Daemon.get_solo()
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

    def clean_old_backups(self):
        max_blocks_backup = int(getattr(settings, 'ETH_BACKUP_BLOCKS', '100'))
        current_block = Daemon.get_solo().block_number

        Block.objects.filter(block_number__lt=current_block-max_blocks_backup).delete()

    def execute(self):
        # Check daemon status
        daemon = Daemon.get_solo()
        if daemon.status == 'EXECUTING':
            # Check reorg
            had_reorg, reorg_block_number = check_reorg(provider=self.provider)

            if had_reorg:
                self.rollback(reorg_block_number)

            # update block number
            # get blocks and decode logs
            last_mined_blocks = self.get_last_mined_blocks()
            if len(last_mined_blocks):
                logger.info('{} blocks mined from {} to {}'.format(len(last_mined_blocks), last_mined_blocks[0], last_mined_blocks[-1]))
            else:
                logger.info('no blocks mined')
            for block in last_mined_blocks:
                # first get un-decoded logs and the block info
                logs, block_info = self.get_logs(block)
                logger.info('got {} logs in block {}'.format(len(logs), block_info['number']))

                ###########################
                # Decode logs #
                ###########################
                if len(logs):
                    for contract in self.contract_map:
                        # Add ABI
                        self.decoder.add_abi(contract['EVENT_ABI'])

                        # Get watched contract addresses
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
                daemon = Daemon.get_solo()
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
                logger.info('update daemon block_number={}'.format(last_mined_blocks[-1]))
                self.update_block_number(last_mined_blocks[-1])

                # Remove older backups
                self.clean_old_backups()
