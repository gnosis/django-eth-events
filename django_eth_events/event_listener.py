from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils.module_loading import import_string
from ethereum.utils import remove_0x_head

from django_eth_events.decoder import Decoder
from django_eth_events.models import Daemon
from django_eth_events.singleton import Singleton
from django_eth_events.web3_service import Web3Service

logger = get_task_logger(__name__)


class UnknownBlock(Exception):
    pass


class EventListener(Singleton):

    def __init__(self, contract_map=settings.ETH_EVENTS):
        super(EventListener, self).__init__()
        self.decoder = Decoder()  # Decodes Ethereum logs
        self.web3 = Web3Service().web3  # Gets transaction and block info from ethereum
        self.contract_map = contract_map  # Taken from settings, it's the contracts we listen to

    def next_block(self):
        return Daemon.get_solo().block_number

    def update_and_next_block(self):
        """
        Increases ethereum block saved on database to current one and returns the block numbers of
        blocks mined since last event_listener execution
        :return: [int]
        """
        daemon = Daemon.get_solo()
        current = self.web3.eth.blockNumber
        if daemon.block_number < current:
            blocks_to_update = range(daemon.block_number+1, current+1)
            daemon.block_number = current
            daemon.save()
            return blocks_to_update
        else:
            return []

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

    def execute(self):
        # update block number
        # get blocks and decode logs
        for block in self.update_and_next_block():
            # first get un-decoded logs and the block info
            logs, block_info = self.get_logs(block)

            ###########################
            # Decode logs #
            ###########################
            for contract in self.contract_map:
                # Add ABI
                self.decoder.add_abi(contract['EVENT_ABI'])

                # Get watched contract addresses
                watched_addresses = self.get_watched_contract_addresses(contract)

                # Filter logs by relevant addresses
                target_logs = [log for log in logs if remove_0x_head(log['address']) in watched_addresses]

                # Decode logs
                decoded_logs = self.decoder.decode_logs(target_logs)

                # Save events
                self.save_events(contract, decoded_logs, block_info)
