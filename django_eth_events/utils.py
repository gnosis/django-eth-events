from json import JSONEncoder

from eth_utils import to_normalized_address
from ethereum.utils import remove_0x_head


def normalize_address_without_0x(address):
    return remove_0x_head(to_normalized_address(address))


class JsonBytesEncoder(JSONEncoder):
        def default(self, obj):
            if isinstance(obj, bytes):
                return obj.decode('ascii')
            # Let the base class default method raise the TypeError
            return JSONEncoder.default(self, obj)
