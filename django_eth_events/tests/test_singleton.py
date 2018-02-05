# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.test import TestCase
from web3 import RPCProvider, IPCProvider
from django_eth_events.web3_service import Web3Service



class TestSingleton(TestCase):

    def test_single_istance(self):
        service1 = Web3Service()
        service2 = Web3Service()
        self.assertEquals(service1.web3, service2.web3)

    def test_arg_rpc_provider(self):
        rpc_provider = RPCProvider(
            host='localhost',
            port=8545,
            ssl=0
        )

        service1 = Web3Service()
        service2 = Web3Service(rpc_provider)
        self.assertEquals(service1.web3, service2.web3)

    def test_arg_ipc_provider(self):
        ipc_provider = IPCProvider(
            ipc_path='',
            testnet=True
        )

        service1 = Web3Service()
        self.assertIsInstance(service1.web3.currentProvider, RPCProvider)
        service2 = Web3Service(ipc_provider)
        self.assertIsInstance(service2.web3.currentProvider, IPCProvider)
        self.assertEquals(service2.web3.currentProvider, ipc_provider)