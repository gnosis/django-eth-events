from http.server import BaseHTTPRequestHandler
from json import dumps, loads

from django.core.cache import cache


class MockedTestrpc(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        # Doesn't do anything with posted data
        self._set_headers()
        content_len = int(self.headers.get('content-length', 0))
        post_body = loads(self.rfile.read(content_len))
        print(post_body)
        print(post_body['method'])
        if post_body['method'] == 'eth_blockNumber':
            self.wfile.write(dumps({"result":
                                    cache.get('block_number')}).encode())
        elif post_body['method'] == 'eth_getBlockByNumber':
            hash = cache.get(post_body['params'][0])
            self.wfile.write(dumps({'result': {'hash': hash}}).encode())
        elif post_body['method'] == 'web3_clientVersion':
            self.wfile.write(dumps({
                'jsonrpc': '2.0'
            }).encode())
        else:
            self.wfile.write('{"code":32601}'.encode())
