# -*- coding: utf-8 -*-
from django.test import TestCase
from eth_tester import EthereumTester
from web3.providers.eth_tester import EthereumTesterProvider

from ..exceptions import UnknownBlock
from ..web3_service import Web3Service


class TestSingleton(TestCase):

    def setUp(self):
        self.web3_service = Web3Service(provider=EthereumTesterProvider(EthereumTester()))
        self.web3 = self.web3_service.web3
        self.web3.eth.defaultAccount = self.web3.eth.coinbase
        self.provider = self.web3.providers[0]
        self.tx_data = {'from': self.web3.eth.coinbase,
                        'gas': 1000000}
        self.event_receivers = []

    def tearDown(self):
        # Delete centralized oracles
        self.provider.ethereum_tester.reset_to_genesis()
        self.assertEqual(0, self.web3.eth.blockNumber)

    def test_unknown_block(self):
        current_block_number = self.web3_service.get_current_block_number()
        self.assertRaises(UnknownBlock, self.web3_service.get_block, current_block_number + 10)

    def test_unknown_blocks(self):
        current_block_number = self.web3_service.get_current_block_number()
        self.assertRaises(UnknownBlock, self.web3_service.get_block, range(current_block_number + 10))
