# -*- coding: utf-8 -*-
from django.test import TestCase
from eth_tester import EthereumTester
from web3 import HTTPProvider, IPCProvider, WebsocketProvider
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

    def test_provider_http(self):
        with self.settings(ETHEREUM_NODE_URL='http://localhost:8545'):
            web3_service = Web3Service()
            provider = web3_service.web3.providers[0]
            self.assertTrue(isinstance(provider, HTTPProvider))

        with self.settings(ETHEREUM_NODE_URL='https://localhost:8545'):
            web3_service = Web3Service()
            provider = web3_service.web3.providers[0]
            self.assertTrue(isinstance(provider, HTTPProvider))

    def test_provider_ipc(self):
        socket_path = '/tmp/socket.ipc'
        with self.settings(ETHEREUM_NODE_URL='ipc://' + socket_path):
            web3_service = Web3Service()
            provider = web3_service.web3.providers[0]
            self.assertTrue(isinstance(provider, IPCProvider))
            self.assertEqual(provider.ipc_path, socket_path)

    def test_provider_websocket(self):
        with self.settings(ETHEREUM_NODE_URL='ws://localhost:8456'):
            web3_service = Web3Service()
            provider = web3_service.web3.providers[0]
            self.assertTrue(isinstance(provider, WebsocketProvider))
