# -*- coding: utf-8 -*-
from django.test import TestCase
from eth_tester import EthereumTester
from web3.providers.eth_tester import EthereumTesterProvider

from ..event_listener import EventListener
from ..factories import DaemonFactory
from ..utils import normalize_address_without_0x
from .utils import abi, bin_hex


class TestDaemon(TestCase):
    def setUp(self):
        self.daemon = DaemonFactory()
        self.bot = EventListener(provider=EthereumTesterProvider(EthereumTester()))
        self.provider = self.bot.web3.providers[0]
        self.bot.web3.eth.defaultAccount = self.bot.web3.eth.coinbase
        self.bot.decoder.methods = {}
        self.maxDiff = None

    def tearDown(self):
        self.provider.ethereum_tester.reset_to_genesis()
        self.assertEqual(0, self.bot.web3.eth.blockNumber)

    def test_next_block(self):
        self.assertListEqual(list(self.bot.get_last_mined_blocks()), [])
        factory = self.bot.web3.eth.contract(abi, bytecode=bin_hex)
        tx_hash = factory.deploy()
        self.bot.web3.eth.getTransactionReceipt(tx_hash)
        tx_hash2 = factory.deploy()
        self.bot.web3.eth.getTransactionReceipt(tx_hash2)
        self.assertEqual(list(self.bot.get_last_mined_blocks()), [1, 2])
        self.bot.update_block_number(2)
        self.assertEqual(list(self.bot.get_last_mined_blocks()), [])

    def test_load_abis(self):
        self.assertIsNotNone(self.bot.decoder)
        self.assertEqual(len(self.bot.decoder.methods), 0)
        self.assertEqual(self.bot.decoder.add_abi([]), 0)
        self.assertEqual(len(self.bot.decoder.methods), 0)
        # No ABIs
        self.assertEqual(self.bot.decoder.add_abi(abi), 6)
        self.assertEqual(len(self.bot.decoder.methods), 6)
        self.assertEqual(self.bot.decoder.add_abi([{'nothing': 'wrong'}]), 0)

        self.assertEqual(self.bot.decoder.add_abi(abi), 6)
        self.assertEqual(self.bot.decoder.add_abi([{'nothing': 'wrong'}]), 0)

    def test_get_logs(self):
        # no logs before transactions
        logs, block_info = self.bot.get_logs(0)
        self.assertListEqual([], logs)

        # create Wallet Factory contract
        factory = self.bot.web3.eth.contract(abi, bytecode=bin_hex)
        self.assertIsNotNone(factory)
        tx_hash = factory.deploy()
        self.assertIsNotNone(tx_hash)
        receipt = self.bot.web3.eth.getTransactionReceipt(tx_hash)
        self.assertIsNotNone(receipt)
        self.assertIsNotNone(receipt.get('contractAddress'))
        factory_address = receipt['contractAddress']

        logs, block_info = self.bot.get_logs(0)
        self.assertListEqual([], logs)

        # send deploy() function, will trigger two events
        self.bot.decoder.add_abi(abi)
        factory_instance = self.bot.web3.eth.contract(abi, factory_address)
        owners = self.bot.web3.eth.accounts[0:2]
        required_confirmations = 1
        daily_limit = 0
        tx_hash = factory_instance.transact().create(owners, required_confirmations, daily_limit)
        receipt = self.bot.web3.eth.getTransactionReceipt(tx_hash)
        self.assertIsNotNone(receipt)
        self.assertListEqual(list(self.bot.get_last_mined_blocks()), [1, 2])
        self.bot.update_block_number(2)
        self.assertListEqual(list(self.bot.get_last_mined_blocks()), [])
        logs, block_info = self.bot.get_logs(self.bot.web3.eth.blockNumber)
        self.assertEqual(2, len(logs))
        decoded = self.bot.decoder.decode_logs(logs)
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
                                   in self.bot.web3.eth.accounts[0:2]]
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
                        'value': normalize_address_without_0x(self.bot.web3.eth.coinbase)
                    },
                    {
                        'name': 'instantiation',
                        'value': normalize_address_without_0x(decoded[1]['params'][1]['value'])
                    }
                ]
            },
            decoded[1]
        )
