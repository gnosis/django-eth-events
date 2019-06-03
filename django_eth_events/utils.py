import errno

from hexbytes import HexBytes
from json import JSONEncoder
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError

from eth_utils import to_normalized_address
from ethereum.utils import remove_0x_head as remove_0x


def is_network_error(exception) -> bool:
    """
    :param exception: an exception error instance
    :return: True if exception detected as a network error, False otherwise
    """
    network_errors = [errno.ECONNABORTED, errno.ECONNREFUSED, errno.ENETRESET, errno.ECONNRESET,
                      errno.ENETUNREACH, errno.ENETDOWN]

    if isinstance(exception, HTTPError) or isinstance(exception, RequestException) or \
            hasattr(exception, 'errno') and exception.errno in network_errors:
        return True

    return False


def remove_0x_head(address) -> str:
    address = address.hex() if isinstance(address, bytes) else address
    return remove_0x(address)


def normalize_address_with_0x(address) -> str:
    address = address.hex() if isinstance(address, bytes) else address
    return to_normalized_address(address)


def normalize_address_without_0x(address) -> str:
    address = address.hex() if isinstance(address, bytes) else address
    return remove_0x_head(to_normalized_address(address))


class JsonBytesEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            try:
                return obj.decode()
            except UnicodeDecodeError:
                return HexBytes(obj).hex()

        # Let the base class default method raise the TypeError
        return super().default(self, obj)