from django.conf import settings
from web3 import Web3, HTTPProvider

from .singleton import Singleton


class Web3Service(Singleton):
    def __init__(
            self,
            rpc_provider = HTTPProvider(
                '{}://{}:{}'.format(
                    'https' if settings.ETHEREUM_NODE_SSL else 'http',
                    settings.ETHEREUM_NODE_HOST,
                    settings.ETHEREUM_NODE_PORT,
                )
            )):
        super(Web3Service, self).__init__()
        self.web3 = Web3(rpc_provider)
