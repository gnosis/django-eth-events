# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.test import TestCase
from django_eth_events.tasks import deadlock_checker
from django_eth_events.factories import DaemonFactory
from django_eth_events.models import Daemon, Block
from django_eth_events.tasks import event_listener
from django_eth_events.web3_service import Web3Service
from django_eth_events.tests.utils import centralized_oracle_abi, centralized_oracle_bytecode
from django_eth_events.chainevents import AbstractEventReceiver
from django.conf import settings
from web3 import TestRPCProvider
from time import sleep
import os


class DummyEventReceiver(AbstractEventReceiver):
    def save(self, decoded_event, block_info):
        return decoded_event

    def rollback(self, decoded_event, block_info):
        pass


class TestCelery(TestCase):

    def setUp(self):
        os.environ.update({'TESTRPC_GAS_LIMIT': '10000000000'})
        self.rpc = TestRPCProvider()
        self.web3 = Web3Service().web3
        self.tx_data = {'from': self.web3.eth.accounts[0], 'gas': 1000000}
        self.event_receivers = []

    def tearDown(self):
        self.rpc.server.shutdown()
        self.rpc.server.server_close()
        self.rpc = None

        # Delete centralized oracles

    def test_deadlock_checker(self):
        daemon = DaemonFactory(listener_lock=True)
        # sleep process to simulate old Daemon instance
        sleep(2)
        deadlock_checker(2000) # 2 seconds
        daemon_test = Daemon.get_solo()
        # Test deadlock detection
        self.assertEquals(daemon_test.listener_lock, False)

        daemon.listener_lock = True
        daemon.save()
        deadlock_checker()
        daemon_test = Daemon.get_solo()
        self.assertEquals(daemon_test.listener_lock, True)

    def test_event_listener(self):
        daemon_factory = DaemonFactory(listener_lock=False)
        # Number of blocks analyzed by Event Listener
        n_blocks = Block.objects.all().count()
        # Create centralized oracle factory contract
        centralized_contract_factory = self.web3.eth.contract(abi=centralized_oracle_abi, bytecode=centralized_oracle_bytecode)
        tx_hash = centralized_contract_factory.deploy()
        centralized_oracle_factory_address = self.web3.eth.getTransactionReceipt(tx_hash).get('contractAddress')
        centralized_oracle_factory = self.web3.eth.contract(centralized_oracle_factory_address, abi=centralized_oracle_abi)

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
        event_listener()
        # Create centralized oracle
        centralized_oracle_factory.transact(self.tx_data).createCentralizedOracle('QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG')
        # Run event listener again
        event_listener()
        # Do checks
        daemon = Daemon.get_solo()
        self.assertEquals(daemon.block_number, daemon_factory.block_number+1)
        self.assertEquals(Block.objects.all().count(), n_blocks+1)
        self.assertFalse(daemon.listener_lock)
