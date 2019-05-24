import errno
from django.test import TestCase
from hexbytes import HexBytes
from urllib3.exceptions import HTTPError, LocationValueError, PoolError

from ..utils import normalize_address_without_0x, remove_0x_head, is_network_error
from ..exceptions import Web3ConnectionException


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

    def test_network_error_exception_detector(self):
        http_error = HTTPError()
        self.assertTrue(is_network_error(http_error))

        location_value_error = LocationValueError()
        self.assertTrue(is_network_error(location_value_error))

        pool_error = PoolError(None, 'an error')
        self.assertTrue(is_network_error(pool_error))

        exception = Exception()
        self.assertFalse(is_network_error(exception))

        w3_conn_error = Web3ConnectionException()
        self.assertFalse(is_network_error(w3_conn_error))

        setattr(w3_conn_error, 'errno', errno.ECONNABORTED)
        self.assertTrue(is_network_error(w3_conn_error))

        setattr(w3_conn_error, 'errno', errno.EPERM)
        self.assertFalse(is_network_error(w3_conn_error))
