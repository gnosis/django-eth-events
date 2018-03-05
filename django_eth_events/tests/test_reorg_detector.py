# -*- coding: utf-8 -*-
from http.server import HTTPServer
from multiprocessing import Process
from time import sleep

from django.core.cache import cache
from django.test import TestCase
from eth_tester import EthereumTester
from web3 import HTTPProvider
from web3.providers.eth_tester import EthereumTesterProvider

from ..chainevents import AbstractEventReceiver
from ..exceptions import NoBackupException, Web3ConnectionException
from ..factories import DaemonFactory
from ..models import Block, Daemon
from ..reorgs import check_reorg
from ..web3_service import Web3Service
from .mocked_testrpc_reorg import MockedTestrpc


def start_mock_server():
    server_address = ('127.0.0.1', 8545)
    httpd = HTTPServer(server_address, MockedTestrpc)
    httpd.serve_forever()
    print('served internal')


class DummyEventReceiver(AbstractEventReceiver):
    def __init__(self, *args, **kwars):
        super(DummyEventReceiver, self).__init__(args, kwars)
        self.stage = 'initial'

    def save(self, decoded_event, block_info):
        self.stage = 'processed'

    def rollback(self, decoded_event, block_info):
        self.stage = 'rollback'


class TestReorgDetector(TestCase):

    def setUp(self):
        # Run mocked testrpc for reorgs
        print('Starting httpd...')
        self.server_process = Process(target=start_mock_server)
        self.server_process.start()
        cache.set('block_number', '0x0')
        sleep(1)
        print('served')
        self.provider = HTTPProvider('http://localhost:8545')
        self.web3_service = Web3Service(self.provider)
        # Mock web3
        self.daemon = DaemonFactory()

    def tearDown(self):
        self.server_process.terminate()
        self.server_process = None
        cache.clear()
        sleep(1)

    def test_mocked_block_number(self):
        self.assertEqual(self.web3_service.get_current_block_number(), 0)
        cache.set('block_number', '0x9')
        self.assertEqual(self.web3_service.get_current_block_number(), 9)

    def test_mocked_block_hash(self):
        block_hash_0 = '{:040d}'.format(0)
        cache.set('0x0', block_hash_0)
        self.assertEqual(self.web3_service.get_block(0)['hash'], block_hash_0)
        block_hash_1 = '{:040d}'.format(1)
        cache.set('0x1', block_hash_1)
        self.assertEqual(self.web3_service.get_block(1)['hash'], block_hash_1)
        self.assertNotEqual(block_hash_0, block_hash_1)

    def test_reorg_ok(self):
        # Last block hash haven't changed
        block_hash_0 = '{:040d}'.format(0)
        cache.set('0x0', block_hash_0)
        cache.set('block_number', '0x1')
        Block.objects.create(block_hash=block_hash_0, block_number=0, timestamp=0)
        Daemon.objects.all().update(block_number=0)
        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)

        block_hash_1 = '{:040d}'.format(1)
        cache.set('0x1', block_hash_1)
        cache.set('block_number', '0x2')
        Block.objects.create(block_hash=block_hash_1, block_number=1, timestamp=0)
        Daemon.objects.all().update(block_number=1)
        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)

    def test_reorg_happened(self):
        # Last block hash haven't changed
        block_hash_0 = '{:040d}'.format(0)
        cache.set('0x0', block_hash_0)
        cache.set('block_number', '0x1')
        Block.objects.create(block_hash=block_hash_0, block_number=0, timestamp=0)
        Daemon.objects.all().update(block_number=0)
        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)

        # Last block hash changed
        block_hash_1 = '{:040d}'.format(1)
        cache.set('0x1', block_hash_1)
        cache.set('block_number', '0x2')
        block_hash_reorg = '{:040d}'.format(1313)
        Block.objects.create(block_hash=block_hash_reorg, block_number=1, timestamp=0)
        Daemon.objects.all().update(block_number=1)
        (had_reorg, block_number) = check_reorg(Daemon.get_solo().block_number)
        self.assertTrue(had_reorg)
        self.assertEqual(block_number, 0)

        Block.objects.filter(block_number=1).update(block_hash=block_hash_1, timestamp=0)
        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)

    def test_reorg_exception(self):
        block_hash_0 = '{:040d}'.format(0)
        cache.set('0x0', block_hash_0)
        cache.set('block_number', '0x1')

        # Last block hash changed
        block_hash_1 = '{:040d}'.format(1)
        cache.set('0x1', block_hash_1)
        cache.set('block_number', '0x2')
        block_hash_reorg = '{:040d}'.format(1313)
        Block.objects.create(block_hash=block_hash_reorg, block_number=1, timestamp=0)
        Daemon.objects.all().update(block_number=1)
        self.assertRaises(NoBackupException, check_reorg, Daemon.get_solo().block_number)

    def test_network_connection_exception(self):
        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)
        self.server_process.terminate()
        self.assertRaises(Web3ConnectionException, check_reorg, Daemon.get_solo().block_number)

    def test_reorg_mined_multiple_blocks_ok(self):
        # Last block hash haven't changed
        block_hash_0 = '{:040d}'.format(0)
        cache.set('0x0', block_hash_0)
        cache.set('block_number', '0x1')
        Block.objects.create(block_hash=block_hash_0, block_number=0, timestamp=0)
        Daemon.objects.all().update(block_number=0)
        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)

        # new block number changed more than one unit
        block_hash_1 = '{:040d}'.format(1)
        cache.set('0x1', block_hash_1)  # set_mocked_testrpc_block_hash
        cache.set('block_number', '0x9')
        Block.objects.create(block_hash=block_hash_1, block_number=1, timestamp=0)
        Daemon.objects.all().update(block_number=1)
        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)

    def test_mined_multiple_blocks_with_reorg(self):
        # Last block hash haven't changed
        block_hash_0 = '{:040d}'.format(0)
        cache.set('0x0', block_hash_0)
        cache.set('block_number', '0x1')
        Block.objects.create(block_hash=block_hash_0, block_number=0, timestamp=0)
        Daemon.objects.all().update(block_number=0)
        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)

        # Last block hash changed
        block_hash_1 = '{:040d}'.format(1)
        cache.set('0x1', block_hash_1)
        cache.set('block_number', '0x9')
        block_hash_reorg = '{:040d}'.format(1313)
        Block.objects.create(block_hash=block_hash_reorg, block_number=1, timestamp=0)
        Daemon.objects.all().update(block_number=1)
        (had_reorg, block_number) = check_reorg(Daemon.get_solo().block_number)
        self.assertTrue(had_reorg)
        self.assertEqual(block_number, 0)

        block_hash_2 = '{:040d}'.format(2)
        cache.set('0x2', block_hash_reorg)
        cache.set('block_number', '0x9')
        Block.objects.create(block_hash=block_hash_2, block_number=2, timestamp=0)
        Daemon.objects.all().update(block_number=2)
        (had_reorg, block_number) = check_reorg(Daemon.get_solo().block_number)
        self.assertTrue(had_reorg)
        self.assertEqual(block_number, 0)

        Block.objects.filter(block_number=1).update(block_hash=block_hash_1)

        (had_reorg, block_number) = check_reorg(Daemon.get_solo().block_number)
        self.assertTrue(had_reorg)
        self.assertEqual(block_number, 1)

        Block.objects.filter(block_number=2).update(block_hash=block_hash_2)
        cache.set('0x2', block_hash_2)
        (had_reorg, block_number) = check_reorg(Daemon.get_solo().block_number)
        self.assertFalse(had_reorg)

    def test_reorg_block_number_decreased(self):
        # block number of the node is lower than the one saved, we trust the node, we rollback to the common block
        # Last block hash haven't changed
        block_hash_0 = '{:040d}'.format(0)
        cache.set('0x0', block_hash_0)
        cache.set('block_number', '0x1')
        Block.objects.create(block_hash='wrong block', block_number=0, timestamp=0)
        Daemon.objects.all().update(block_number=3)
        # No common block
        self.assertRaises(NoBackupException, check_reorg, Daemon.get_solo().block_number)

        Block.objects.filter(block_number=0).update(block_hash=block_hash_0)

        block_hash_1 = '{:040d}'.format(1)
        cache.set('0x1', block_hash_1)
        cache.set('block_number', '0x2')
        Block.objects.create(block_hash=block_hash_1, block_number=1, timestamp=0)
        (had_reorg, block_number) = check_reorg(Daemon.get_solo().block_number)
        self.assertTrue(had_reorg)
        self.assertEqual(block_number, 1)

        cache.set('0x1', 'reorg_hash')

        (had_reorg, block_number) = check_reorg(Daemon.get_solo().block_number)
        self.assertTrue(had_reorg)
        self.assertEqual(block_number, 0)

    def test_reorg_web3_provider(self):
        # Stop running server
        self.server_process.terminate()
        ethereum_tester = EthereumTester()
        ethereum_tester_provider = EthereumTesterProvider(ethereum_tester)
        # Run check_reorg, should not raise exceptions
        (had_reorg, block_number) = check_reorg(Daemon.get_solo().block_number, provider=ethereum_tester_provider)
        self.assertFalse(had_reorg)
        # Reset genesis block to simulate reorg
        ethereum_tester.reset_to_genesis()

        # Restart rpc server
        self.server_process = None
        self.server_process = Process(target=start_mock_server)
        self.server_process.start()
        sleep(1)

        # Simulate reorg
        block_hash_0 = '{:040d}'.format(0)
        block_hash_1 = '{:040d}'.format(1)

        Block.objects.create(block_hash=block_hash_0, block_number=0, timestamp=0)
        Daemon.objects.all().update(block_number=0)

        cache.set('0x0', block_hash_0)
        cache.set('0x1', block_hash_1)
        cache.set('block_number', '0x2')
        block_hash_reorg = '{:040d}'.format(1313)
        Block.objects.create(block_hash=block_hash_reorg, block_number=1, timestamp=0)
        Daemon.objects.all().update(block_number=1)

        (had_reorg, _) = check_reorg(Daemon.get_solo().block_number)
        self.assertTrue(had_reorg)
