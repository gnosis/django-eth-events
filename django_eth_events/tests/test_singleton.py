# -*- coding: utf-8 -*-
from django.test import TestCase
from eth_tester import EthereumTester
from web3 import HTTPProvider, IPCProvider
from web3.providers.eth_tester import EthereumTesterProvider

from ..event_listener import EventListener
from ..web3_service import Web3Service, Web3ServiceProvider


class TestSingleton(TestCase):

    def test_single_instance(self):
        service1 = Web3ServiceProvider()
        service2 = Web3ServiceProvider()
        self.assertEqual(service1.web3, service2.web3)

    def test_arg_ipc_provider(self):
        ipc_provider = IPCProvider(
            ipc_path=None,
            testnet=True
        )

        service1 = Web3ServiceProvider()
        self.assertIsInstance(service1.web3.providers[0], HTTPProvider)
        service2 = Web3Service(ipc_provider)
        self.assertIsInstance(service2.web3.providers[0], IPCProvider)
        self.assertEqual(service2.web3.providers[0], ipc_provider)

    def test_eth_tester_provider(self):
        eth_tester_provider = EthereumTesterProvider(EthereumTester())

        service1 = Web3ServiceProvider()
        self.assertIsInstance(service1.web3.providers[0], HTTPProvider)
        service2 = Web3Service(eth_tester_provider)
        self.assertIsInstance(service2.web3.providers[0], EthereumTesterProvider)
        self.assertEqual(service2.web3.providers[0], eth_tester_provider)

    def test_event_listener_singleton(self):
        ipc_provider = IPCProvider(
            ipc_path=None,
            testnet=True
        )

        listener1 = EventListener()
        listener2 = EventListener()
        self.assertEqual(listener1, listener2)
        listener3 = EventListener(provider=ipc_provider)
        self.assertNotEqual(listener2, listener3)

        # For a different contract we need a different instance of the singleton even if provider is the same
        contract_map = [
            {'NAME': 'Tester Oracle Factory', 'EVENT_ABI': [],
             'EVENT_DATA_RECEIVER': 'django_eth_events.tests.test_celery.DummyEventReceiver',
             'ADDRESSES': ['c305c901078781C232A2a521C2aF7980f8385ee9']
             }
        ]
        listener4 = EventListener(provider=ipc_provider, contract_map=contract_map)
        self.assertNotEqual(listener3, listener4)
        listener5 = EventListener(provider=ipc_provider, contract_map=contract_map)
        self.assertEqual(listener4, listener5)
