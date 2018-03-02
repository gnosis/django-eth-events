# from celery.utils.log import get_task_logger
import binascii

from eth_abi import decode_abi
from ethereum.utils import sha3

from .singleton import Singleton
from .utils import normalize_address_without_0x

# logger = get_task_logger(__name__)


class Decoder(Singleton):
    """
    This module allows to decode ethereum logs (hexadecimal) into readable dictionaries, by using
    Contract's ABIs
    """

    methods = {}

    @staticmethod
    def get_method_id(item):
        if item.get('inputs'):
            # Generate methodID and link it with the abi
            method_header = "{}({})".format(item['name'],
                                            ','.join(map(lambda method_input: method_input['type'], item['inputs'])))
        else:
            method_header = "{}()".format(item['name'])

        return binascii.hexlify(sha3(method_header)).decode('ascii')

    def add_abi(self, abi):
        """
        Add ABI array into the decoder collection, in this step the method id is generated from:
        sha3(function_name + '(' + param_type1 + ... + param_typeN + ')')
        :param abi: Array of dictionaries
        :return: Integer (items added)
        """
        added = 0
        for item in abi:
            if item.get('name'):
                method_id = self.get_method_id(item)
                self.methods[method_id] = item
                added += 1
        return added

    def remove_abi(self, abis):
        """
        For testing purposes, we won't sometimes to remove the ABI methods from the decoder
        :param abis: Array of Ethereum address
        :return: None
        """
        for item in abis:
            if item.get('name'):
                method_id = self.get_method_id(item)
                if self.methods.get(method_id):
                    del self.methods[method_id]

    def decode_log(self, log):
        """
        Decodes an ethereum log and returns the recovered parameters along with the method from the abi that was used
        in decoding. Raises a LookupError if the log's topic is unknown,
        :param log: ethereum log
        :return: dictionary of decoded parameters, decoding method reference
        """
        method_id = log['topics'][0][2:]

        if method_id not in self.methods:
            raise LookupError("Unknown log topic.")

        # method item has the event name, inputs and types
        method = self.methods[method_id]
        decoded_params = []
        data_i = 0
        topics_i = 1
        data_types = []

        # get param types from properties not indexed
        for param in method['inputs']:
            if not param['indexed']:
                data_types.append(param['type'])

        # decode_abi expect data in bytes format instead of str starting by 0x
        log_data_bytes = bytes.fromhex(log['data'][2:])
        decoded_data = decode_abi(data_types, log_data_bytes)

        for param in method['inputs']:
            decoded_p = {
                'name': param['name']
            }
            if param['indexed']:
                decoded_p['value'] = log['topics'][topics_i]
                topics_i += 1
            else:
                decoded_p['value'] = decoded_data[data_i]
                data_i += 1

            if '[]' in param['type']:
                if 'address' in param['type']:
                    decoded_p['value'] = list([normalize_address_without_0x(account) for account in decoded_p['value']])
                else:
                    decoded_p['value'] = list(decoded_p['value'])
            elif 'address' == param['type']:
                address = normalize_address_without_0x(decoded_p['value'])
                if len(address) == 40:
                    decoded_p['value'] = address
                elif len(address) == 64:
                    decoded_p['value'] = decoded_p['value'][26::]

            decoded_params.append(decoded_p)

        decoded_event = {
            'params': decoded_params,
            'name': method['name'],
            'address': normalize_address_without_0x(log['address'])
        }

        return decoded_event

    def decode_logs(self, logs):
        """
        Processes and array of ethereum logs and returns an array of dictionaries of logs that could be decoded
        from the ABIs loaded. Logs that could not be decoded are omitted from the result.
        :param logs: array of ethereum logs
        :return: array of dictionaries
        """
        decoded = []
        for log in logs:
            try:
                decoded.append(self.decode_log(log))
            except LookupError:
                pass

        return decoded
