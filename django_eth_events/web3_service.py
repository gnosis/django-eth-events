import concurrent.futures
import logging
import socket

from django.conf import settings
from requests.exceptions import ConnectionError
from web3 import HTTPProvider, IPCProvider, Web3
from web3.middleware import geth_poa_middleware

from .exceptions import (UnknownBlock, UnknownTransaction,
                         Web3ConnectionException)

logger = logging.getLogger(__name__)


class Web3Service(object):
    """
    Singleton Web3 object manager, returns a new object if
    the argument provider is different than the current used provider.
    """
    instance = None

    def __new__(cls, provider=None):
        if not Web3Service.instance:
            Web3Service.instance = Web3Service.__Web3Service(provider)
        elif provider and not isinstance(provider,
                                         Web3Service.instance.web3.providers[0].__class__):
            Web3Service.instance = Web3Service.__Web3Service(provider)
        elif not provider and not isinstance(Web3Service.instance.web3.providers[0],
                                             Web3Service.instance.default_provider_class):
            Web3Service.instance = Web3Service.__Web3Service(provider)
        return Web3Service.instance

    def __getattr__(self, item):
        return getattr(self.instance, item)

    class __Web3Service:
        default_provider_class = HTTPProvider
        max_workers = int(getattr(settings, 'ETHEREUM_MAX_WORKERS', 10))
        ethereum_ipc_path = getattr(settings, 'ETHEREUM_IPC_PATH', None)

        def __init__(self, provider=None):
            if not provider:
                if self.ethereum_ipc_path:
                    self.default_provider_class = IPCProvider
                    provider = self.default_provider_class(
                        ipc_path=self.ethereum_ipc_path
                    )
                else:
                    protocol = 'https' if settings.ETHEREUM_NODE_SSL else 'http'
                    endpoint_uri = "{}://{}:{}".format(protocol,
                                                       settings.ETHEREUM_NODE_HOST,
                                                       settings.ETHEREUM_NODE_PORT)
                    provider = self.default_provider_class(endpoint_uri)

            self.web3 = Web3(provider)

            # If not in the mainnet, inject Geth PoA middleware
            # http://web3py.readthedocs.io/en/latest/middleware.html#geth-style-proof-of-authority
            try:
                if self.web3.net.chainId != 1:
                    self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)
            # For tests using dummy connections (like IPC)
            except (ConnectionError, FileNotFoundError):
                pass

        @property
        def main_provider(self):
            return self.web3.providers[0]

        def make_sure_cheksumed_address(self, address):
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

        def is_connected(self):
            try:
                return self.web3.isConnected()
            except socket.timeout:
                return False

        def get_current_block_number(self):
            """
            :raises Web3ConnectionException
            :return: <int>
            """
            try:
                return self.web3.eth.blockNumber
            except Exception as e:
                if not self.is_connected():
                    raise Web3ConnectionException('Web3 provider is not connected')
                else:
                    raise e

        def get_transaction_receipt(self, transaction_hash):
            """
            :param transaction_hash:
            :raises Web3ConnectionException
            :raises UnknownTransaction
            :return:
            """
            try:
                receipt = self.web3.eth.getTransactionReceipt(transaction_hash)

                # receipt sometimes is none, might be because a reorg, we exit the loop with a controlled exception
                if receipt is None:
                    raise UnknownTransaction
                return receipt
            except Exception:
                if not self.is_connected():
                    raise Web3ConnectionException('Web3 provider is not connected')
                else:
                    raise UnknownTransaction

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
            except Exception:
                if not self.is_connected():
                    raise Web3ConnectionException('Web3 provider is not connected')
                else:
                    raise UnknownBlock

        def get_blocks(self, block_identifiers, full_transactions=False):
            """
            :param block_identifiers:
            :param full_transactions:
            :raises Web3ConnectionException
            :raises UnknownBlock
            :return:
            """
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Get blocks from ethereum node and mark each future with its block_id
                future_to_block_id = {executor.submit(self.get_block, block_id, full_transactions): block_id
                                      for block_id in block_identifiers}
                blocks = {}
                for future in concurrent.futures.as_completed(future_to_block_id):
                    block_id = future_to_block_id[future]
                    block = future.result()
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

        def get_logs(self, block):
            """
            Extract raw logs from web3 ethereum block
            :param block: web3 block to get logs from
            :return: list of log dictionaries
            """

            logs = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_receipts_with_tx = {executor.submit(self.get_transaction_receipt, tx): tx
                                           for tx in block['transactions']}

                tx_with_receipt = {}
                for future in concurrent.futures.as_completed(future_receipts_with_tx):
                    tx = future_receipts_with_tx[future]
                    receipt = future.result()
                    tx_with_receipt[tx] = receipt

                for tx in block['transactions']:
                    receipt = tx_with_receipt[tx]
                    logs.extend(receipt.get('logs', []))

            return logs
