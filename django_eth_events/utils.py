from json import JSONEncoder

from eth_utils import to_normalized_address


def remove_0x_head(s):
    """
    Better use from django_eth_events.utils import remove_0x_head,
    because in pyEthereum version <= 1.6.1 is bugged for Python3
    """
    return s[2:] if s[:2] in (b'0x', '0x') else s


def normalize_address_without_0x(address):
    return remove_0x_head(to_normalized_address(address))


class JsonBytesEncoder(JSONEncoder):
        def default(self, obj):
            if isinstance(obj, bytes):
                return obj.decode('ascii')
            # Let the base class default method raise the TypeError
            return JSONEncoder.default(self, obj)
