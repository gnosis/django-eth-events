# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.test import TestCase
from web3 import RPCProvider
from django_eth_events.factories import DaemonFactory
from django_eth_events.web3_service import Web3Service
from mocked_testrpc_reorg import MockedTestrpc
from BaseHTTPServer import HTTPServer
from multiprocessing import Process
from time import sleep
from django.core.cache import cache

def start_mock_server():
    server_address = ('127.0.0.1', 8545)
    httpd = HTTPServer(server_address, MockedTestrpc)
    httpd.serve_forever()
    print 'served internal'


class TestReorgDetector(TestCase):

    def setUp(self):
        # Run mocked testrpc for reorgs
        print 'Starting httpd...'
        self.p = Process(target=start_mock_server)
        self.p.start()
        cache.set('block_number', '0x0')
        sleep(1)
        print 'served'
        self.rpc = RPCProvider(
            host='127.0.0.1',
            port='8545',
            ssl=0
        )
        web3_service = Web3Service(self.rpc)
        self.web3 = web3_service.web3
        # Mock web3
        self.daemon = DaemonFactory()

    def test_mocked_block_number(self):
        self.assertEqual(self.web3.eth.blockNumber, 0)
        cache.set('block_number', '0x9')
        self.assertEqual(self.web3.eth.blockNumber, 9)

    def test_mocked_block_hash(self):
        block_hash_0 = '{:040d}'.format(0)
        cache.set('0x0', block_hash_0)
        self.assertEqual(self.web3.eth.getBlock(0)['hash'], block_hash_0)
        block_hash_1 = '{:040d}'.format(1)
        cache.set('0x1', block_hash_1)
        self.assertEqual(self.web3.eth.getBlock(1)['hash'], block_hash_1)
        self.assertNotEqual(block_hash_0, block_hash_1)

    def test_reorg_ok(self):
        # Last block hash haven't changed
        pass

    def test_reorg_happened(self):
        # Last block hash changed
        pass

    def test_reorg_exception(self):
        # Last block has changed, not enough blocks in backup
        pass

    def test_reorg_mined_multiple_blocks(self):
        # new block number changed more than one unit
        pass

    def test_reorg_block_number_decreased(self):
        # block number of the node is lower than the one saved, maybe node changed manually, sync issues, skip
        pass

    def tearDown(self):
        self.p.terminate()
        self.p = None
        sleep(1)
