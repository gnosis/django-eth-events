# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from django.test import TestCase
from django_eth_events.factories import DaemonFactory
from django_eth_events.event_listener import EventListener
from django_eth_events.web3_service import Web3Service
from django_eth_events.models import Daemon, Block
from django_eth_events.tests.utils import CentralizedOracle
from web3 import TestRPCProvider
from json import loads
from django_eth_events.tests.utils import centralized_oracle_abi, centralized_oracle_bytecode
from django_eth_events.utils import remove_0x_head


class TestDaemonExec(TestCase):
    def setUp(self):
        os.environ.update({'TESTRPC_GAS_LIMIT': '10000000000'})
        self.provider = TestRPCProvider()
        web3_service = Web3Service(self.provider)
        self.web3 = web3_service.web3
        # Mock web3
        self.daemon = DaemonFactory()

        self.tx_data = {'from': self.web3.eth.accounts[0], 'gas': 1000000}

        # create oracles
        centralized_contract_factory = self.web3.eth.contract(abi=centralized_oracle_abi, bytecode=centralized_oracle_bytecode)
        tx_hash = centralized_contract_factory.deploy()
        self.centralized_oracle_factory_address = self.web3.eth.getTransactionReceipt(tx_hash).get('contractAddress')
        self.centralized_oracle_factory = self.web3.eth.contract(self.centralized_oracle_factory_address, abi=centralized_oracle_abi)

        self.contracts = [
            {
                'NAME': 'Centralized Oracle Factory',
                'EVENT_ABI': centralized_oracle_abi,
                'EVENT_DATA_RECEIVER': 'django_eth_events.tests.utils.CentralizedOraclesReceiver',
                'ADDRESSES': [self.centralized_oracle_factory_address[2::]]
            }
        ]
        self.listener_under_test = EventListener(contract_map=self.contracts, provider=self.provider)
        CentralizedOracle().reset()

    def tearDown(self):
        self.provider.server.shutdown()
        self.provider.server.server_close()
        self.provider = None

    def test_create_centralized_oracle(self):
        self.assertEqual(CentralizedOracle().length(), 0)
        self.assertEqual(0, Daemon.get_solo().block_number)
        self.assertEqual(0, Block.objects.all().count())

        # Create centralized oracle
        tx_hash = self.centralized_oracle_factory.transact(self.tx_data).createCentralizedOracle('QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG')
        self.assertIsNotNone(tx_hash)
        self.listener_under_test.execute()
        self.assertEqual(CentralizedOracle().length(), 1)
        self.assertEqual(1, Daemon.get_solo().block_number)

        # Check backup
        self.assertEqual(1, Block.objects.all().count())
        block = Block.objects.get(block_number=1)
        self.assertEqual(1, len(loads(block.decoded_logs)))

    def test_reorg_centralized_oracle(self):
        # initial transaction, to set reorg init
        accounts = self.web3.eth.accounts
        self.web3.eth.sendTransaction({'from': accounts[0], 'to': accounts[1], 'value': 5000000})
        self.assertEqual(0, Block.objects.all().count())
        self.assertEqual(CentralizedOracle().length(), 0)
        self.assertEqual(1, self.web3.eth.blockNumber)

        # Create centralized oracle
        tx_hash = self.centralized_oracle_factory.transact(self.tx_data).createCentralizedOracle(
            'QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG')
        self.assertIsNotNone(tx_hash)
        self.listener_under_test.execute()
        self.assertEqual(CentralizedOracle().length(), 1)
        self.assertEqual(2, Daemon.get_solo().block_number)
        self.assertEqual(2, Block.objects.all().count())
        self.assertEqual(2, self.web3.eth.blockNumber)

        # Reset blockchain (simulates reorg)
        self.provider.server.shutdown()
        self.provider.server.server_close()
        self.provider = TestRPCProvider()
        web3_service = Web3Service(self.provider)
        self.web3 = web3_service.web3
        self.assertEqual(0, self.web3.eth.blockNumber)

        self.web3.eth.sendTransaction({'from': accounts[0], 'to': accounts[1], 'value': 1000000})
        self.web3.eth.sendTransaction({'from': accounts[0], 'to': accounts[1], 'value': 1000000})
        self.web3.eth.sendTransaction({'from': accounts[0], 'to': accounts[1], 'value': 1000000})
        self.assertEqual(2, self.web3.eth.blockNumber)

        # force block_hash change (cannot recreate a real reorg with python testrpc)
        block_hash = remove_0x_head(self.web3.eth.getBlock(1)['hash'])
        Block.objects.filter(block_number=1).update(block_hash=block_hash)

        self.listener_under_test.execute()
        self.assertEqual(CentralizedOracle().length(), 0)
        self.assertEqual(2, Daemon.get_solo().block_number)
        self.assertEqual(2, Block.objects.all().count())
