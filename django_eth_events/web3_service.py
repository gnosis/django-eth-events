from django.conf import settings
from web3 import HTTPProvider, IPCProvider, Web3


class Web3Service(object):
    """
    Singleton Web3 object manager, returns a new object if
    the argument provider is different than the current used provider.
    """
    instance = None

    class __Web3Service:
        web3 = None
        default_provider_class = HTTPProvider

        def __init__(self, provider=None):
            if not provider:
                ethereum_ipc_path = getattr(settings, 'ETHEREUM_IPC_PATH', None)
                if ethereum_ipc_path:
                    self.default_provider_class = IPCProvider
                    provider = self.default_provider_class(
                        ipc_path=settings.ETHEREUM_IPC_PATH
                    )
                else:
                    protocol = 'https' if settings.ETHEREUM_NODE_SSL else 'http'
                    endpoint_uri = "{}://{}:{}".format(protocol,
                                                       settings.ETHEREUM_NODE_HOST,
                                                       settings.ETHEREUM_NODE_PORT)
                    provider = self.default_provider_class(endpoint_uri)

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
