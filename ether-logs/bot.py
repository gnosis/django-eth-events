from utils import Singleton
from . import models
from events.models import Alert
from decoder import Decoder
from json import loads
from web3 import Web3, HTTPProvider, RPCProvider
from django.conf import settings
from eth.mail_batch import MailBatch
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


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
        self.batch = MailBatch()

    def next_block(self):
        return models.Daemon.get_solo().block_number

    def update_block(self):
        daemon = models.Daemon.get_solo()
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
        alerts = Alert.objects.filter(contract__in=contracts)
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

    def filter_logs(self, logs, contracts):
        # filter by contracts
        all_alerts = Alert.objects.filter(contract__in=contracts).prefetch_related('events__event_values').prefetch_related('dapp')
        filtered = {}
        for log in logs:
            # get alerts for same log contract (can be many)
            alerts = all_alerts.filter(contract=log[u'address'])

            for alert in alerts:
                # Get event names
                events = alert.events.filter(name=log[u'name'])
                if events.count():
                    # Get event property, if event property, discard unmatched values
                    add_event = True
                    if events[0].event_values.count():
                        # check that all parameters check in value or doesn't exist
                        for event_value in events[0].event_values.iterator():
                            for param in log[u'params']:
                                if event_value.property == param[u'name']:
                                    if event_value.value != param[u'value']:
                                        add_event = False

                    # add log
                    if add_event:
                        email = alert.dapp.user.email
                        dapp_name = alert.dapp.name
                        dapp_code = alert.dapp.authentication_code
                        if not filtered.get(email):
                            filtered[email] = {}
                        if not filtered[email].get(dapp_name):
                            # filtered[email][dapp_name] = []
                            filtered[email][dapp_name] = dict(authentication_code=dapp_code, logs=[])

                        # filtered[email][dapp_name].append(log)
                        filtered[email][dapp_name].get('logs').append(log)

        return filtered

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

            # If decoded, filter correct logs and group by dapp and mail
            filtered = self.filter_logs(decoded, contracts)

            # add filtered logs to send mail
            for mail, dapp_logs in filtered.iteritems():
                self.batch.add_mail(mail, dapp_logs)

        # if blocknumber is the same, do nothing
        # Send mails in batch
        self.batch.send_mail()
