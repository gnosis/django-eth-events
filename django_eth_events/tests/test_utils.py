from django.test import TestCase
from hexbytes import HexBytes

from ..utils import normalize_address_without_0x, remove_0x_head


class TestSingleton(TestCase):

    def test_remove_0x_head(self):
        self.assertEqual('b58d5491D17ebF46E9DB7F18CeA7C556AE80d53B',
                         remove_0x_head('0xb58d5491D17ebF46E9DB7F18CeA7C556AE80d53B'))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         remove_0x_head('0xb58d5491d17ebf46e9db7f18cea7c556ae80d53b'))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53B',
                         remove_0x_head('0xb58d5491d17ebf46e9db7f18cea7c556ae80d53B'))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         remove_0x_head(HexBytes('0xb58d5491D17ebF46E9DB7F18CeA7C556AE80d53B')))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         remove_0x_head(HexBytes('0xb58d5491d17ebf46e9db7f18cea7c556ae80d53B')))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         remove_0x_head(HexBytes('0xb58d5491d17ebf46e9db7f18cea7c556ae80d53B')))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         remove_0x_head(HexBytes('b58d5491d17ebf46e9db7f18cea7c556ae80d53B')))

    def test_normalize_address_without_0x(self):
        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         normalize_address_without_0x('0xb58d5491D17ebF46E9DB7F18CeA7C556AE80d53B'))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         normalize_address_without_0x('0xb58d5491d17ebf46e9db7f18cea7c556ae80d53b'))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         normalize_address_without_0x(HexBytes('0xb58d5491d17ebf46e9db7f18cea7c556ae80d53b')))

        self.assertEqual('b58d5491d17ebf46e9db7f18cea7c556ae80d53b',
                         normalize_address_without_0x(HexBytes('b58d5491d17ebf46e9db7f18cea7c556ae80d53b')))
