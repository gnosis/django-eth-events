# -*- coding: utf-8 -*-
from django.test import TestCase
from eth_tester import EthereumTester
from web3.providers.eth_tester import EthereumTesterProvider

from ..event_listener import EventListener
from ..factories import DaemonFactory
from ..models import Daemon
from ..utils import normalize_address_without_0x
from .utils import abi, bin_hex


class TestDaemon(TestCase):
    def setUp(self):
        self.daemon = DaemonFactory()
        self.el = EventListener(provider=EthereumTesterProvider(EthereumTester()))
        self.provider = self.el.provider
        self.el.web3.eth.defaultAccount = self.el.web3.eth.coinbase
        self.el.decoder.methods = {}
        self.maxDiff = None

    def tearDown(self):
        self.provider.ethereum_tester.reset_to_genesis()
        self.assertEqual(0, self.el.web3.eth.blockNumber)

    def test_next_block(self):
        daemon = Daemon.get_solo()
        self.assertListEqual(list(self.el.get_last_mined_block_numbers(daemon.block_number,
                                                                       self.el.get_current_block_number())),
                             [])
        factory = self.el.web3.eth.contract(abi, bytecode=bin_hex)
        tx_hash = factory.deploy()
        self.el.web3.eth.getTransactionReceipt(tx_hash)
        tx_hash2 = factory.deploy()
        self.el.web3.eth.getTransactionReceipt(tx_hash2)
        self.assertEqual(list(self.el.get_last_mined_block_numbers(daemon.block_number,
                                                                   self.el.get_current_block_number())),
                         [1, 2])
        self.el.update_block_number(daemon, 2)
        self.assertEqual(list(self.el.get_last_mined_block_numbers(daemon.block_number,
                                                                   self.el.get_current_block_number())),
                         [])

    def test_load_abis(self):
        self.assertIsNotNone(self.el.decoder)
        self.assertEqual(len(self.el.decoder.methods), 0)
        self.assertEqual(self.el.decoder.add_abi([]), 0)
        self.assertEqual(len(self.el.decoder.methods), 0)
        # No ABIs
        self.assertEqual(self.el.decoder.add_abi(abi), 6)
        self.assertEqual(len(self.el.decoder.methods), 6)
        self.assertEqual(self.el.decoder.add_abi([{'nothing': 'wrong'}]), 0)

        self.assertEqual(self.el.decoder.add_abi(abi), 6)
        self.assertEqual(self.el.decoder.add_abi([{'nothing': 'wrong'}]), 0)

    def test_get_logs(self):
        # no logs before transactions
        block_info = self.el.web3_service.get_block(0)
        logs = self.el.get_logs(block_info)
        self.assertListEqual([], logs)

        # create Wallet Factory contract
        factory = self.el.web3.eth.contract(abi, bytecode=bin_hex)
        self.assertIsNotNone(factory)
        tx_hash = factory.deploy()
        self.assertIsNotNone(tx_hash)
        receipt = self.el.web3.eth.getTransactionReceipt(tx_hash)
        self.assertIsNotNone(receipt)
        self.assertIsNotNone(receipt.get('contractAddress'))
        factory_address = receipt['contractAddress']

        block_info = self.el.web3_service.get_block(0)
        logs = self.el.get_logs(block_info)
        self.assertListEqual([], logs)

        # send deploy() function, will trigger two events
        self.el.decoder.add_abi(abi)
        factory_instance = self.el.web3.eth.contract(abi, factory_address)
        owners = self.el.web3.eth.accounts[0:2]
        required_confirmations = 1
        daily_limit = 0
        tx_hash = factory_instance.transact().create(owners, required_confirmations, daily_limit)
        receipt = self.el.web3.eth.getTransactionReceipt(tx_hash)
        self.assertIsNotNone(receipt)
        daemon = Daemon.get_solo()
        self.assertEqual(list(self.el.get_last_mined_block_numbers(daemon.block_number,
                                                                   self.el.get_current_block_number())),
                         [1, 2])
        self.el.update_block_number(daemon, 2)
        self.assertEqual(list(self.el.get_last_mined_block_numbers(daemon.block_number,
                                                                   self.el.get_current_block_number())),
                         [])

        block_info = self.el.web3_service.get_current_block()
        logs = self.el.get_logs(block_info)
        self.assertEqual(2, len(logs))
        decoded = self.el.decoder.decode_logs(logs)
        self.assertEqual(2, len(decoded))
        self.assertDictEqual(
            {
                'address': normalize_address_without_0x(factory_address),
                'name': 'OwnersInit',
                'params': [
                    {
                        'name': 'owners',
                        'value': [normalize_address_without_0x(account)
                                  for account
                                  in self.el.web3.eth.accounts[0:2]]
                    }
                ]
            },
            decoded[0]
        )
        self.assertDictEqual(
            {
                'address': normalize_address_without_0x(factory_address),
                'name': 'ContractInstantiation',
                'params': [
                    {
                        'name': 'sender',
                        'value': normalize_address_without_0x(self.el.web3.eth.coinbase)
                    },
                    {
                        'name': 'instantiation',
                        'value': normalize_address_without_0x(decoded[1]['params'][1]['value'])
                    }
                ]
            },
            decoded[1]
        )
