import concurrent.futures
import logging
import socket
from typing import Dict, List, Tuple

import requests
from django.core.exceptions import ImproperlyConfigured
from eth_tester import EthereumTester
from requests.exceptions import ConnectionError
from web3 import HTTPProvider, IPCProvider, Web3
from web3.exceptions import UnhandledRequest
from web3.middleware import geth_poa_middleware
from web3.providers.eth_tester import EthereumTesterProvider

from .exceptions import (UnknownBlock, UnknownTransaction,
                         Web3ConnectionException)

logger = logging.getLogger(__name__)

RINKEBY_CHAIN_ID = 4


class Web3ServiceProvider:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            from django.conf import settings
            provider = Web3Service.get_provider_from_uri(settings.ETHEREUM_NODE_URL)
            cls.instance = Web3Service(provider,
                                       settings.ETHEREUM_MAX_WORKERS,
                                       settings.ETHEREUM_MAX_BATCH_REQUESTS)
        return cls.instance


class Web3Service:
    connection_exceptions: Tuple[Exception] = (UnhandledRequest, socket.timeout, ConnectionError)

    @staticmethod
    def get_provider_from_uri(node_uri: str):
        if node_uri.startswith('http'):
            return HTTPProvider(node_uri)
        elif node_uri.startswith('ipc'):
            path = node_uri.replace('ipc://', '')
            return IPCProvider(ipc_path=path)
        elif node_uri.startswith('test'):
            return EthereumTesterProvider(EthereumTester())
        else:
            raise ValueError('%s uri is not supported. Must start by http, ipc, or test' % node_uri)

    def __init__(self, provider,
                 max_workers: int=10, max_batch_requests: int=10, slow_provider_timeout: int=400):
        """
        :param node_uri: Node http address. If uri starts with 'test', EthereumTester will be used
        :param max_workers: Max workers for multithread calls. 1 -> No multithread
        :param max_batch_requests: Max requests in the same batch for RPC
        :param self.slow_provider_timeout: Timeout for time lasting requests (like filters)
        """
        self.provider = provider
        self.max_workers = max_workers
        self.max_batch_requests = max_batch_requests
        self.slow_provider_timeout = slow_provider_timeout
        self.node_uri = self.get_node_uri()

        self.web3 = Web3(provider)
        self.web3_slow = Web3(self.slow_provider)
        self.http_session = requests.session()

        # If rinkeby, inject Geth PoA middleware
        # http://web3py.readthedocs.io/en/latest/middleware.html#geth-style-proof-of-authority
        try:
            if int(self.web3.net.version) == RINKEBY_CHAIN_ID:
                self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)
        # For tests using dummy connections (like IPC)
        except (UnhandledRequest, ConnectionError, ConnectionRefusedError, FileNotFoundError):
            pass

    @property
    def slow_provider(self):
        if isinstance(self.provider, HTTPProvider):
            return HTTPProvider(endpoint_uri=self.provider.endpoint_uri,
                                request_kwargs={'timeout': self.slow_provider_timeout})
        elif isinstance(self.provider, IPCProvider):
            return IPCProvider(ipc_path=self.provider.ipc_path, timeout=self.slow_provider_timeout)
        else:
            return self.provider

    @property
    def main_provider(self):
        return self.web3.providers[0]

    def get_node_uri(self) -> str:
        if isinstance(self.provider, HTTPProvider):
            return self.provider.endpoint_uri

    def has_http_provider(self):
        return isinstance(self.main_provider, HTTPProvider)

    def make_sure_cheksumed_address(self, address: str) -> str:
        """
        Makes sure an address is checksumed. If not, returns it checksumed
        and logs a warning
        :param address: ethereum address
        :return: checksumed 0x address
        """
        if self.web3.isChecksumAddress(address):
            return address
        else:
            checksumed_address = self.web3.toChecksumAddress(address)
            logger.warning("Address %s is not checksumed, should be %s", address, checksumed_address)
            return checksumed_address

    def is_connected(self) -> bool:
        try:
            return self.web3.isConnected()
        except socket.timeout:
            return False

    def get_current_block_number(self) -> int:
        """
        :raises Web3ConnectionException
        :return: <int>
        """
        try:
            return self.web3.eth.blockNumber
        except self.connection_exceptions as e:
            raise Web3ConnectionException('Web3 provider is not connected') from e

    def get_transaction_receipt(self, transaction_hash):
        """
        :param transaction_hash:
        :raises Web3ConnectionException
        :raises UnknownTransaction
        :return:
        """
        try:
            receipt = self.web3.eth.getTransactionReceipt(transaction_hash)

            if not receipt:
                # Might be because a reorg
                raise UnknownTransaction
            return receipt
        except self.connection_exceptions as e:
            raise Web3ConnectionException('Web3 provider is not connected') from e
        except Exception as e:
            raise UnknownTransaction from e

    def get_transaction_receipts(self, tx_hashes):
        tx_with_receipt = {}

        if self.has_http_provider():
            # Query limit for RPC is 131072
            for tx_hashes_chunk in self._chunks(tx_hashes, self.max_batch_requests):
                rpc_request = [self._build_tx_receipt_request(tx_hash) for tx_hash in tx_hashes_chunk]
                for rpc_response in self._do_request(rpc_request):
                    tx = rpc_response['result']
                    if not tx:
                        raise UnknownTransaction
                    tx_hash = tx['transactionHash']
                    tx_with_receipt[tx_hash] = tx
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_receipts_with_tx = {executor.submit(self.get_transaction_receipt, tx): tx
                                           for tx in tx_hashes}

                for future in concurrent.futures.as_completed(future_receipts_with_tx):
                    tx = future_receipts_with_tx[future]
                    receipt = future.result()
                    if not receipt:
                        raise UnknownTransaction
                    tx_with_receipt[tx] = receipt

        return tx_with_receipt

    def get_block(self, block_identifier, full_transactions=False):
        """
        :param block_identifier:
        :param full_transactions:
        :raises Web3ConnectionException
        :raises UnknownBlock
        :return:
        """
        try:
            block = self.web3.eth.getBlock(block_identifier, full_transactions)
            if not block:
                raise UnknownBlock
            return block
        except self.connection_exceptions:
            raise Web3ConnectionException('Web3 provider is not connected')
        except Exception as e:
            raise UnknownBlock from e

    def get_blocks(self, block_identifiers, full_transactions=False):
        """
        :param block_identifiers:
        :param full_transactions:
        :raises Web3ConnectionException
        :raises UnknownBlock
        :return:
        """

        blocks = {}

        if self.has_http_provider():
            # Query limit for RPC is 131072
            for block_numbers_chunk in self._chunks(block_identifiers, self.max_batch_requests):
                rpc_request = [self._build_block_request(block_number) for block_number in block_numbers_chunk]
                for rpc_response in self._do_request(rpc_request):
                    block = rpc_response['result']
                    if not block:
                        raise UnknownBlock

                    block_number = int(block['number'], 16)
                    block['number'] = block_number
                    block['timestamp'] = int(block['timestamp'], 16)
                    blocks[block_number] = block
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Get blocks from ethereum node and mark each future with its block_id
                future_to_block_id = {executor.submit(self.get_block, block_id, full_transactions): block_id
                                      for block_id in block_identifiers}
                for future in concurrent.futures.as_completed(future_to_block_id):
                    block_id = future_to_block_id[future]
                    block = future.result()
                    if not block:
                        raise UnknownBlock
                    blocks[block_id] = block

        return blocks

    def get_current_block(self, full_transactions=False):
        """
        :param full_transactions:
        :raises Web3ConnectionException
        :raises UnknownBlock
        :return:
        """
        return self.get_block(self.get_current_block_number(), full_transactions)

    def get_logs_for_block(self, block):
        """
        Extract raw logs from web3 ethereum block
        :param block: web3 block to get logs from
        :return: list of log dictionaries
        """

        logs = []
        tx_with_receipt = self.get_transaction_receipts(block['transactions'])

        for tx in block['transactions']:
            receipt = tx_with_receipt[tx]
            logs.extend(receipt.get('logs', []))

        return logs

    def get_logs_for_blocks(self, blocks):
        """
        Recover logs for every block
        :param blocks: web3 blocks to get logs from
        :return: a dictionary, the key is the block number and value is list of
        """

        block_number_with_logs = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Get blocks from ethereum node and mark each future with its block_id
            future_logs_to_block = {executor.submit(self.get_logs_for_block, block): block for block in blocks}
            for future in concurrent.futures.as_completed(future_logs_to_block):
                block = future_logs_to_block[future]
                logs = future.result()
                block_number_with_logs[block['number']] = logs

        return block_number_with_logs

    def get_logs_for_address_using_filter(self, from_block: int, to_block: int, address: str) -> List[any]:
        """
        Recover logs using filter for address
        """
        return self.web3_slow.eth.getLogs({'fromBlock': from_block,
                                           'toBlock': to_block,
                                           'address': address})

    def get_logs_for_event_using_filter(self, from_block: int, to_block: int, event_hash: str) -> List[any]:
        """
        Recover logs using filter for event
        """
        logs_filter = {'fromBlock': from_block,
                       'toBlock': to_block,
                       'topics': [event_hash]}
        return self.web3_slow.eth.getLogs(logs_filter)

    def _do_request(self, rpc_request):
        if self.has_http_provider():
            return self.http_session.post(self.node_uri, json=rpc_request).json()
        else:
            raise ImproperlyConfigured('Not valid provider')

    def _build_block_request(self, block_number: int, full_transactions: bool=False) -> Dict[str, any]:
        block_number_hex = '0x{:x}'.format(block_number)
        return {"jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [block_number_hex, full_transactions],
                "id": 1
                }

    def _build_tx_receipt_request(self, tx_hash: str) -> Dict[str, any]:
        return {"jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1}

    def _chunks(self, iterable, size):
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]
