from json import JSONEncoder

# Better use from django_eth_events.utils import remove_0x_head,
# but in pyEthereum version <= 1.6.1 is bugged for Python3


def remove_0x_head(s):
    return s[2:] if s[:2] in (b'0x', '0x') else s


class JsonBytesEncoder(JSONEncoder):
        def default(self, obj):
            if isinstance(obj, bytes):
                return obj.decode('ascii')
            # Let the base class default method raise the TypeError
            return JSONEncoder.default(self, obj)
