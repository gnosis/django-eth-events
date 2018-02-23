# -*- coding: utf-8 -*-
from json import loads

from django.test import TestCase

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
        self.decoder.methods = {}

    def test_add_abis(self):
        self.decoder.add_abi([])
        self.assertEqual(len(self.decoder.methods), 0)
        self.decoder.add_abi(self.test_abi)
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
            'address' : '0xa6d9c5f7d4de3cef51ad3b7235d79ccc95114de5',
            'data' : u"0x00000000000000000000000065039084cc6f4773291a6ed7dcf5bc3a2e894ff300000000000000000000000017e054b16ca658789c927c854976450adbda7df0",
            'topics' : [
                '0x4fb057ad4a26ed17a57957fa69c306f11987596069b89521c511fc9a894e6161'
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
