# -*- coding: utf-8 -*-
from json import loads

from django.test import TestCase
from eth_tester import EthereumTester
from web3.providers.eth_tester import EthereumTesterProvider

from ..event_listener import EventListener
from ..factories import DaemonFactory
from ..models import Block, Daemon
from ..utils import remove_0x_head
from ..web3_service import Web3Service
from .utils import (CentralizedOracle, centralized_oracle_abi,
                    centralized_oracle_bytecode)


class TestDaemonExec(TestCase):
    def setUp(self):
        self.web3 = Web3Service(provider=EthereumTesterProvider(EthereumTester())).web3
        self.provider = self.web3.providers[0]
        self.web3.eth.defaultAccount = self.web3.eth.coinbase

        # Mock web3
        self.daemon = DaemonFactory()
        self.tx_data = {'from': self.web3.eth.accounts[0],
                        'gas': 1000000}

        # create oracles
        centralized_contract_factory = self.web3.eth.contract(abi=centralized_oracle_abi,
                                                              bytecode=centralized_oracle_bytecode)
        tx_hash = centralized_contract_factory.deploy()
        self.centralized_oracle_factory_address = self.web3.eth.getTransactionReceipt(tx_hash).get('contractAddress')
        self.centralized_oracle_factory = self.web3.eth.contract(self.centralized_oracle_factory_address,
                                                                 abi=centralized_oracle_abi)

        self.contracts = [
            {
                'NAME': 'Centralized Oracle Factory',
                'EVENT_ABI': centralized_oracle_abi,
                'EVENT_DATA_RECEIVER': 'django_eth_events.tests.utils.CentralizedOraclesReceiver',
                'ADDRESSES': [self.centralized_oracle_factory_address[2::]]
            }
        ]
        self.listener_under_test = EventListener(contract_map=self.contracts,
                                                 provider=self.provider)
        CentralizedOracle().reset()
        self.assertEqual(CentralizedOracle().length(), 0)
        self.assertEqual(1, self.web3.eth.blockNumber)

    def tearDown(self):
        self.provider.ethereum_tester.reset_to_genesis()
        self.assertEqual(0, self.web3.eth.blockNumber)

    def test_create_centralized_oracle(self):
        self.assertEqual(CentralizedOracle().length(), 0)
        self.assertEqual(0, Daemon.get_solo().block_number)
        self.assertEqual(0, Block.objects.all().count())

        # Create centralized oracle
        tx_hash = self.centralized_oracle_factory.transact(self.tx_data).createCentralizedOracle('QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG')
        self.assertIsNotNone(tx_hash)
        self.listener_under_test.execute()
        self.assertEqual(CentralizedOracle().length(), 1)
        self.assertEqual(2, Daemon.get_solo().block_number)

        # Check backup
        self.assertEqual(2, Block.objects.all().count())
        block = Block.objects.get(block_number=2)
        self.assertEqual(1, len(loads(block.decoded_logs)))

    def test_reorg_centralized_oracle(self):
        # initial transaction, to set reorg init
        accounts = self.web3.eth.accounts
        self.web3.eth.sendTransaction({'from': accounts[0], 'to': accounts[1], 'value': 5000000})
        self.assertEqual(0, Block.objects.all().count())
        self.assertEqual(CentralizedOracle().length(), 0)
        self.assertEqual(2, self.web3.eth.blockNumber)

        # Create centralized oracle
        tx_hash = self.centralized_oracle_factory.transact(self.tx_data).createCentralizedOracle(
            'QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG')
        self.assertIsNotNone(tx_hash)
        self.listener_under_test.execute()
        self.assertEqual(CentralizedOracle().length(), 1)
        self.assertEqual(3, Daemon.get_solo().block_number)
        self.assertEqual(3, Block.objects.all().count())
        self.assertEqual(3, self.web3.eth.blockNumber)

        # Reset blockchain (simulates reorg)
        self.tearDown()

        self.web3.eth.sendTransaction({'from': accounts[0], 'to': accounts[1], 'value': 1000000})
        self.web3.eth.sendTransaction({'from': accounts[0], 'to': accounts[1], 'value': 1000000})
        self.web3.eth.sendTransaction({'from': accounts[0], 'to': accounts[1], 'value': 1000000})
        self.assertEqual(3, self.web3.eth.blockNumber)

        # Force block_hash change (cannot recreate a real reorg with python testrpc)
        # TODO Check if it can be done with eth-tester
        block_hash = remove_0x_head(self.web3.eth.getBlock(1)['hash'])
        Block.objects.filter(block_number=1).update(block_hash=block_hash)

        self.listener_under_test.execute()
        self.assertEqual(CentralizedOracle().length(), 0)
        self.assertEqual(3, Daemon.get_solo().block_number)
        self.assertEqual(3, Block.objects.all().count())
