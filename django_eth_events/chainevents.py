from abc import ABCMeta, abstractmethod

from .singleton import SingletonABCMeta


class AbstractAddressesGetter(object):
    """Abstract AddressesGetter class."""
    __metaclass__ = SingletonABCMeta

    @abstractmethod
    def get_addresses(self): pass

    @abstractmethod
    def __contains__(self, address): pass


class AbstractEventReceiver(object):
    """Abstract EventReceiver class."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def save(self, decoded_event, block_info): pass

    @abstractmethod
    def rollback(self, decoded_event, block_info): pass
