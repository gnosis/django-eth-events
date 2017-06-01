from utils import Singleton
from models import Daemon
from decoder import Decoder
from json import loads
from web3 import Web3, RPCProvider
from django.conf import settings
from django.apps import apps
from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)

alert_model_app_name = getattr(settings, 'ALERT_MODEL_APP', 'django_ether_logs')
AlertModelAppConfig = apps.get_app_config(alert_model_app_name)

alert_model_name = getattr(settings, 'ALERT_MODEL', 'Alert')
AlertModel = AlertModelAppConfig.get_model(alert_model_name)


class UnknownBlock(Exception):
    pass


class Bot(Singleton):

    def __init__(self):
        super(Bot, self).__init__()
        self.decoder = Decoder()
        self.web3 = Web3(
            RPCProvider(
                host=settings.ETHEREUM_NODE_HOST,
                port=settings.ETHEREUM_NODE_PORT,
                ssl=settings.ETHEREUM_NODE_SSL
            )
        )
        self.callback_per_block = getattr(settings, 'CALLBACK_PER_BLOCK', None)
        self.callback_per_exec = getattr(settings, 'CALLBACK_PER_EXEC', None)
        self.filter_logs = getattr(settings, 'LOG_FILTER_FUNCTION', None)

    def next_block(self):
        return Daemon.get_solo().block_number

    def update_block(self):
        daemon = Daemon.get_solo()
        current = self.web3.eth.blockNumber
        if daemon.block_number < current:
            blocks_to_update = range(daemon.block_number+1, current+1)
            logger.info("block range {}-{} {}".format(daemon.block_number, current, blocks_to_update))
            daemon.block_number = current
            daemon.save()
            return blocks_to_update
        else:
            return []

    def load_abis(self, contracts):
        alerts = AlertModel.objects.filter(contract__in=contracts)
        added = 0
        for alert in alerts:
            try:
                added += self.decoder.add_abi(loads(alert.abi))
            except ValueError:
                pass
        return added

    def get_logs(self, block_number):
        block = self.web3.eth.getBlock(block_number)
        logs = []
        if block and block.get(u'hash'):
            for tx in block[u'transactions']:
                receipt = self.web3.eth.getTransactionReceipt(tx)
                if receipt.get('logs'):
                    logs.extend(receipt[u'logs'])
            return logs
        else:
            raise UnknownBlock

    def execute(self):
        # update block number
        # get blocks and decode logs
        for block in self.update_block():
            logger.info("block {}".format(block))
            # first get un-decoded logs
            logs = self.get_logs(block)

            # get contract addresses
            contracts = []
            for log in logs:
                contracts.append(log[u'address'])
            contracts = set(contracts)

            # load abi's from alerts with contract addresses
            self.load_abis(contracts)

            # decode logs
            decoded = self.decoder.decode_logs(logs)

            # If decoded, filter correct logs
            filtered = self.filter_logs(decoded, contracts) if callable(self.filter_logs) else decoded

            if callable(self.callback_per_block):
                self.callback_per_block(filtered)

        if callable(self.callback_per_exec):
            self.callback_per_exec()
