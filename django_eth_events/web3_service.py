from django.conf import settings
from web3 import Web3, RPCProvider


class Web3Service(object):
    """
    Singleton Web3 object manager, returns a new object if
    the argument provider is different than the current used provider.
    """
    instance = None

    class __Web3Service:
        web3 = None
        default_provider = RPCProvider

        def __init__(self, provider=None):
            if not provider:
                provider = self.default_provider(
                    host=settings.ETHEREUM_NODE_HOST,
                    port=settings.ETHEREUM_NODE_PORT,
                    ssl=settings.ETHEREUM_NODE_SSL
                )

            self.web3 = Web3(provider)

    def __new__(cls, provider=None):
        if not Web3Service.instance:
            Web3Service.instance = Web3Service.__Web3Service(provider)
        elif provider and not isinstance(provider, Web3Service.instance.web3.currentProvider.__class__):
            Web3Service.instance = Web3Service.__Web3Service(provider)
        elif not provider and not isinstance(Web3Service.instance.web3.currentProvider, Web3Service.instance.default_provider):
            Web3Service.instance = Web3Service.__Web3Service(provider)
        return Web3Service.instance

    def __getattr__(self, item):
        return getattr(self.instance, item)
