from django.conf import settings
from web3 import IPCProvider, RPCProvider, Web3


class Web3Service(object):
    """
    Singleton Web3 object manager, returns a new object if
    the argument provider is different than the current used provider.
    """
    instance = None

    class __Web3Service:
        web3 = None
        default_provider_class = RPCProvider

        def __init__(self, provider=None):
            if not provider:
                if hasattr(settings, 'ETHEREUM_IPC_PATH'):
                    self.default_provider_class = IPCProvider
                    provider = self.default_provider_class(
                        ipc_path=settings.ETHEREUM_IPC_PATH
                    )
                else:
                    provider = self.default_provider_class(
                        host=settings.ETHEREUM_NODE_HOST,
                        port=settings.ETHEREUM_NODE_PORT,
                        ssl=settings.ETHEREUM_NODE_SSL
                    )

            self.web3 = Web3(provider)

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
