# -*- coding: utf-8 -*-
from json import loads

from django.test import TestCase
from hexbytes import HexBytes

from ..decoder import Decoder


class TestDecoder(TestCase):
    test_abi = loads(
        '[{"inputs": [{"type": "address", "name": ""}], "constant": true, "name": "isInstantiation", "payable": '
        'false, "outputs": [{"type": "bool", "name": ""}], "type": "function"}, {"inputs": [{"type": "address[]", '
        '"name": "_owners"}, {"type": "uint256", "name": "_required"}, {"type": "uint256", "name": "_dailyLimit"}], '
        '"constant": false, "name": "create", "payable": false, "outputs": [{"type": "address", "name": "wallet"}], '
        '"type": "function"}, {"inputs": [{"type": "address", "name": ""}, {"type": "uint256", "name": ""}], '
        '"constant": true, "name": "instantiations", "payable": false, "outputs": [{"type": "address", "name": ""}], '
        '"type": "function"}, {"inputs": [{"type": "address", "name": "creator"}], "constant": true, '
        '"name": "getInstantiationCount", "payable": false, "outputs": [{"type": "uint256", "name": ""}], '
        '"type": "function"}, {"inputs": [{"indexed": false, "type": "address", "name": "sender"}, {"indexed": false, '
        '"type": "address", "name": "instantiation"}], "type": "event", "name": "ContractInstantiation", "anonymous": '
        'false}]')
    decoder = Decoder()

    def setUp(self):
        self.decoder.reset()

    def test_add_abis(self):
        self.decoder.add_abi([])
        self.assertEqual(len(self.decoder.methods), 0)
        self.assertEqual(self.decoder.add_abi(self.test_abi), 5)
        # Make sure second time same abi is not processed
        self.assertEqual(self.decoder.add_abi(self.test_abi), 0)
        self.assertEqual(len(self.decoder.methods), 5)
        self.decoder.remove_abi([])
        self.assertEqual(len(self.decoder.methods), 5)
        self.decoder.remove_abi(loads('[{"inputs": [{"type": "address", "name": ""}], "constant": true, "name": "isInstantiation", "payable": false, "outputs": [{"type": "bool", "name": ""}], "type": "function"}]'))
        self.assertEqual(len(self.decoder.methods), 4)
        self.decoder.remove_abi(self.test_abi)
        self.assertEqual(len(self.decoder.methods), 0)

    def test_decode_logs(self):
        logs = [
          {
            'address': '0xa6d9c5f7d4de3cef51ad3b7235d79ccc95114de5',
            'data': u"0x00000000000000000000000065039084cc6f4773291a6ed7dcf5bc3a2e894ff300000000000000000000000017e054b16ca658789c927c854976450adbda7df0",
            'transactionHash': '0x54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa',
            'topics': [
                HexBytes('0x4fb057ad4a26ed17a57957fa69c306f11987596069b89521c511fc9a894e6161')
            ]
          }
        ]
        self.assertListEqual([], self.decoder.decode_logs(logs))
        self.decoder.add_abi(self.test_abi)
        decoded = self.decoder.decode_logs(logs)
        self.assertIsNotNone(decoded)
        self.assertListEqual(
            [
                {
                    'address': 'a6d9c5f7d4de3cef51ad3b7235d79ccc95114de5',
                    'name': 'ContractInstantiation',
                    'transaction_hash': logs[0]['transactionHash'][2:], # without `0x`
                    'params': [
                        {
                            'name': 'sender',
                            'value': '65039084cc6f4773291a6ed7dcf5bc3a2e894ff3'
                        },
                        {
                            'name': 'instantiation',
                            'value': '17e054b16ca658789c927c854976450adbda7df0'
                        }
                    ]
                }
            ],
            decoded
        )

    def test_decode_transaction_hash(self):
        self.decoder.add_abi(self.test_abi)

        base_logs = [
          {
            'address': '0xa6d9c5f7d4de3cef51ad3b7235d79ccc95114de5',
            'data': u"0x00000000000000000000000065039084cc6f4773291a6ed7dcf5bc3a2e894ff300000000000000000000000017e054b16ca658789c927c854976450adbda7df0",
            'transactionHash': '0x54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa',
            'topics': [
                HexBytes('0x4fb057ad4a26ed17a57957fa69c306f11987596069b89521c511fc9a894e6161')
            ]
          }
        ]

        logs_with_hex_tx_hash = [{
            **base_logs[0],
            'transactionHash': HexBytes('0x54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa')
        }]
        decoded = self.decoder.decode_logs(logs_with_hex_tx_hash)
        # Test decoded transaction_hash is without `0x` prefix
        self.assertEqual(decoded[0]['transaction_hash'], logs_with_hex_tx_hash[0]['transactionHash'].hex()[2:])
        self.assertFalse(decoded[0]['transaction_hash'].startswith('0x'))

        logs_with_hex_tx_hash = [{
            **base_logs[0],
            'transactionHash': bytes(HexBytes('54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa')).hex()
        }]
        decoded = self.decoder.decode_logs(logs_with_hex_tx_hash)
        # Test decoded transaction_hash is without `0x` prefix
        self.assertEqual(decoded[0]['transaction_hash'], logs_with_hex_tx_hash[0]['transactionHash'])
        self.assertFalse(decoded[0]['transaction_hash'].startswith('0x'))

        logs_with_hex_tx_hash = [{
            **base_logs[0],
            'transactionHash': bytes(HexBytes('54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa'))
        }]
        decoded = self.decoder.decode_logs(logs_with_hex_tx_hash)
        # Test decoded transaction_hash is without `0x` prefix
        self.assertEqual(decoded[0]['transaction_hash'], logs_with_hex_tx_hash[0]['transactionHash'].hex())
        self.assertFalse(decoded[0]['transaction_hash'].startswith('0x'))

        logs_with_hex_tx_hash = [{
            **base_logs[0],
            'transactionHash': bytes(HexBytes('0x54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa'))
        }]
        decoded = self.decoder.decode_logs(logs_with_hex_tx_hash)
        # Test decoded transaction_hash is without `0x` prefix
        self.assertEqual(decoded[0]['transaction_hash'], logs_with_hex_tx_hash[0]['transactionHash'].hex())
        self.assertFalse(decoded[0]['transaction_hash'].startswith('0x'))
        self.assertIsInstance(decoded[0]['transaction_hash'], str)

    def test_validation_errors(self):
        self.decoder.add_abi(self.test_abi)
        # Create base not decoded log, which contains camelcase `transactionHash`
        base_log = {
            'address': '0xa6d9c5f7d4de3cef51ad3b7235d79ccc95114de5',
            'transactionHash': '0x54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa',
            'data': u"0x00000000000000000000000065039084cc6f4773291a6ed7dcf5bc3a2e894ff300000000000000000000000017e054b16ca658789c927c854976450adbda7df0",
            'topics': [
                HexBytes('0x4fb057ad4a26ed17a57957fa69c306f11987596069b89521c511fc9a894e6161')
            ]
        }

        logs_with_invalid_address = [
            {
                **base_log,
                'address': '0x'
            }
        ]
        self.assertRaises(ValueError, self.decoder.decode_logs, logs_with_invalid_address)

        logs_with_invalid_address = [
            {
                **base_log,
                'address': None
            }
        ]
        self.assertRaises(ValueError, self.decoder.decode_logs, logs_with_invalid_address)

        logs_with_valid_address = [base_log]
        self.assertIsNotNone(self.decoder.decode_logs(logs_with_valid_address))

        logs_with_invalid_tx_hash = [
            {
                **base_log,
                'transactionHash': '0x'
            }
        ]
        self.assertRaises(ValueError, self.decoder.decode_logs, logs_with_invalid_tx_hash)

        logs_with_invalid_tx_hash = [
            {
                **base_log,
                'transactionHash': '0x0123456789'
            }
        ]
        self.assertRaises(ValueError, self.decoder.decode_logs, logs_with_invalid_tx_hash)

        logs_with_invalid_tx_hash = [
            {
                **base_log,
                'transactionHash': None
            }
        ]
        self.assertRaises(ValueError, self.decoder.decode_logs, logs_with_invalid_tx_hash)

        logs_with_valid_tx_hash = [
            {
                **base_log,
                'transactionHash': HexBytes('0x54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa')
            }
        ]
        self.assertIsNotNone(self.decoder.decode_logs(logs_with_valid_tx_hash))

        logs_with_valid_tx_hash = [
            {
                **base_log,
                'transactionHash': HexBytes('54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa')
            }
        ]
        self.assertIsNotNone(self.decoder.decode_logs(logs_with_valid_tx_hash))

        logs_with_valid_tx_hash = [
            {
                **base_log,
                'transactionHash': HexBytes('0x54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa').hex()
            }
        ]
        self.assertIsNotNone(self.decoder.decode_logs(logs_with_valid_tx_hash))

        logs_with_valid_tx_hash = [
            {
                **base_log,
                'transactionHash': bytes(HexBytes('0x54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa')).hex()
            }
        ]
        self.assertIsNotNone(self.decoder.decode_logs(logs_with_valid_tx_hash))

        logs_with_valid_tx_hash = [
            {
                **base_log,
                'transactionHash': bytes(HexBytes('54041b3ce0976ee17212100f42b3793fa4ee5f869a6d107249a75caa5fc1b8aa')).hex()
            }
        ]
        self.assertIsNotNone(self.decoder.decode_logs(logs_with_valid_tx_hash))