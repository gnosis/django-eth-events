from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils.module_loading import import_string
from ethereum.utils import remove_0x_head

from django_eth_events.decoder import Decoder
from django_eth_events.models import Daemon, Block
from django_eth_events.singleton import Singleton
from django_eth_events.web3_service import Web3Service
from django_eth_events.reorgs import check_reorg

from json import dumps, loads

logger = get_task_logger(__name__)


class UnknownBlock(Exception):
    pass


class EventListener(Singleton):

    def __init__(self, contract_map=settings.ETH_EVENTS):
        super(EventListener, self).__init__()
        self.decoder = Decoder()  # Decodes Ethereum logs
        self.web3 = Web3Service().web3  # Gets transaction and block info from ethereum
        self.contract_map = contract_map  # Taken from settings, it's the contracts we listen to

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

        logger.info('no blocks mined, daemon: {} current: {}'.format(daemon.block_number, current))
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
        block = self.web3.eth.getBlock(block_number)
        logs = []

        if block and block.get(u'hash'):
            for tx in block[u'transactions']:
                receipt = self.web3.eth.getTransactionReceipt(tx)
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
        return addresses

    def save_events(self, contract, decoded_logs, block_info):
        EventReceiver = import_string(contract['EVENT_DATA_RECEIVER'])
        for decoded_log in decoded_logs:
            EventReceiver().save(decoded_event=decoded_log, block_info=block_info)

    def revert_events(self, event_receiver_string, decoded_logs, block_info):
        EventReceiver = import_string(event_receiver_string)
        for decoded_log in decoded_logs:
            EventReceiver().rollback(decoded_event=decoded_log, block_info=block_info)

    def rollback(self, block_number):
        # get all blocks to rollback
        blocks = Block.objects.filter(block_number__gt=block_number)
        logger.info('rolling back {} blocks, until block number {}'.format(blocks.count(), block_number))
        for block in blocks:
            decoded_logs = loads(block.decoded_logs)
            logger.info('rolling back {} block, {} logs'.format(block.block_number, len(decoded_logs)))
            if len(decoded_logs):
                for event_receiver, logs in decoded_logs.iteritems():
                    self.revert_events(event_receiver, logs, block.block_number)

        # Remove backups from future blocks (old chain)
        blocks.delete()

    def backup(self, block_hash, block_number, decoded_logs, event_receiver_string):
        # Get block or create new one
        block, _ = Block.objects.get_or_create(block_hash=block_hash, defaults={'block_number': block_number})

        saved_logs = loads(block.decoded_logs)

        if saved_logs.get(event_receiver_string) is None:
            saved_logs[event_receiver_string] = []

        saved_logs[event_receiver_string].extend(decoded_logs)

        block.decoded_logs = dumps(saved_logs)
        block.save()

    def clean_old_backups(self):
        max_blocks_backup = int(getattr(settings, 'ETH_BACKUP_BLOCKS', '100'))
        current_block = Daemon.get_solo().block_number

        Block.objects.filter(block_number__lt=current_block-max_blocks_backup).delete()

    def execute(self):
        # Check reorg
        had_reorg, reorg_block_number = check_reorg()

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
                    target_logs = [log for log in logs if remove_0x_head(log['address']) in watched_addresses]

                    logger.info('{} logs'.format(len(target_logs)))

                    # Decode logs
                    decoded_logs = self.decoder.decode_logs(target_logs)

                    logger.info('{} decoded logs'.format(len(decoded_logs)))

                    if len(decoded_logs):
                        # Save events
                        self.save_events(contract, decoded_logs, block_info)

                        max_blocks_to_backup = int(getattr(settings, 'ETH_BACKUP_BLOCKS', '100'))
                        if (block - last_mined_blocks[-1]) < max_blocks_to_backup:
                            self.backup(block_info['hash'], block_info['number'], decoded_logs, contract['EVENT_DATA_RECEIVER'])

            # backup block if haven't been backed up (no logs, but we saved the hash for reorg checking anyway)
            Block.objects.get_or_create(block_number=block, block_hash=block_info['hash'])

        if len(last_mined_blocks):
            # Update block number after execution
            logger.info('update daemon block_number={}'.format(last_mined_blocks[-1]))
            self.update_block_number(last_mined_blocks[-1])

            # Remove older backups
            self.clean_old_backups()