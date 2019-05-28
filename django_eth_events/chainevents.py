from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .singleton import SingletonABC


class AbstractAddressesGetter(SingletonABC):
    """Abstract AddressesGetter class."""

    @abstractmethod
    def get_addresses(self) -> List[str]: pass

    @abstractmethod
    def __contains__(self, address: str) -> bool: pass


class AbstractEventReceiver(ABC):
    """Abstract EventReceiver class."""

    @abstractmethod
    def save(self, decoded_event: Dict, block_info: Dict) -> Optional[object]:
        """
        Let the inheriting EventReceiver save data. The way data is handled is up to the EventReceiver.
        :param decoded_event: See django_eth_events.decoder.Decoder
        :type decoded_event: dict
        :param block_info: Contains data representing a Block. See https://web3py.readthedocs.io/en/stable/examples.html#looking-up-blocks
        :type block_info: dict
        :return: the updated instance or None
        """
        pass

    @abstractmethod
    def rollback(self, decoded_event: Dict, block_info: Dict) -> Optional[object]:
        """
        Let the inheriting EventReceiver undo saved data. The way data is handled is up to the EventReceiver.
        :param decoded_event: See django_eth_events.decoder.Decoder
        :type decoded_event: dict
        :param block_info: Contains data representing a Block. See https://web3py.readthedocs.io/en/stable/examples.html#looking-up-blocks
        :type block_info: dict
        """
        pass
