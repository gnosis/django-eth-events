from json import JSONEncoder

from eth_utils import to_normalized_address
from ethereum.utils import remove_0x_head as remove_0x


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
                return obj.decode('ascii')
            # Let the base class default method raise the TypeError
            return JSONEncoder.default(self, obj)
