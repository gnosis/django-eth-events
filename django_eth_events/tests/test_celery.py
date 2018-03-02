# -*- coding: utf-8 -*-
from time import sleep

from django.conf import settings
from django.test import TestCase
from eth_tester import EthereumTester
from web3.providers.eth_tester import EthereumTesterProvider

from ..chainevents import AbstractEventReceiver
from ..factories import DaemonFactory
from ..models import Block, Daemon
from ..tasks import deadlock_checker, event_listener
from ..web3_service import Web3Service
from .utils import centralized_oracle_abi, centralized_oracle_bytecode


class DummyEventReceiver(AbstractEventReceiver):
    def save(self, decoded_event, block_info):
        return decoded_event

    def rollback(self, decoded_event, block_info):
        pass


class TestCelery(TestCase):

    def setUp(self):
        self.web3 = Web3Service(provider=EthereumTesterProvider(EthereumTester())).web3
        self.provider = self.web3.providers[0]
        self.web3.eth.defaultAccount = self.web3.eth.coinbase
        self.tx_data = {'from': self.web3.eth.coinbase,
                        'gas': 1000000}
        self.event_receivers = []

    def tearDown(self):
        # Delete centralized oracles
        self.provider.ethereum_tester.reset_to_genesis()
        self.assertEqual(0, self.web3.eth.blockNumber)

    def test_deadlock_checker(self):
        daemon = DaemonFactory(listener_lock=True)
        # sleep process to simulate old Daemon instance
        sleep(2)
        deadlock_checker(2000)  # 2 seconds
        daemon_test = Daemon.get_solo()
        # Test deadlock detection
        self.assertEqual(daemon_test.listener_lock, False)

        daemon.listener_lock = True
        daemon.save()
        deadlock_checker()
        daemon_test = Daemon.get_solo()
        self.assertEqual(daemon_test.listener_lock, True)

    def test_event_listener(self):
        daemon_factory = DaemonFactory(listener_lock=False)
        # Number of blocks analyzed by Event Listener
        n_blocks = Block.objects.all().count()
        # Create centralized oracle factory contract
        centralized_contract_factory = self.web3.eth.contract(abi=centralized_oracle_abi,
                                                              bytecode=centralized_oracle_bytecode)
        tx_hash = centralized_contract_factory.deploy()
        centralized_oracle_factory_address = self.web3.eth.getTransactionReceipt(tx_hash).get('contractAddress')
        centralized_oracle_factory = self.web3.eth.contract(centralized_oracle_factory_address,
                                                            abi=centralized_oracle_abi)

        # Event receiver
        centralized_event_receiver = {
            'NAME': 'Centralized Oracle Factory',
            'EVENT_ABI': centralized_oracle_abi,
            'EVENT_DATA_RECEIVER': 'django_eth_events.tests.test_celery.DummyEventReceiver',
            'ADDRESSES': [centralized_oracle_factory_address[2::]]
        }

        self.event_receivers.append(centralized_event_receiver)
        setattr(settings, 'ETH_EVENTS', self.event_receivers)

        # Start Celery Task
        event_listener(self.provider)
        # Create centralized oracle
        centralized_oracle_factory.transact(self.tx_data).createCentralizedOracle('QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG')
        # Run event listener again
        event_listener(self.provider)
        # Do checks
        daemon = Daemon.get_solo()
        self.assertEqual(daemon.status, 'EXECUTING')
        self.assertEqual(daemon.block_number, daemon_factory.block_number + 2)
        self.assertEqual(Block.objects.all().count(), n_blocks + 2)
        self.assertFalse(daemon.listener_lock)
