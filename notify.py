import hashlib
import hmac
import json
import os
import sys
import time

import requests


class NotifyApi:
    def __init__(self, apikey: str, apisecret: str):
        self.apikey = apikey
        self.apisecret = apisecret
        self.baseurl = 'https://atyx.ru/notify/'

        self.session = requests.Session()
        self.session.headers.update(
            {
                'Content-Type': 'application/json;charset=utf-8',
                'X-ATYX-APIKEY': self.apikey,
            }
        )

    def send_message(self, message):
        return self.post('', {'message': message})

    def check_signature(
        self,
        signature: str,
        timestamp: int,
        uri: str,
        method: str,
        data: dict[str, str],
    ):
        contenthash = self._get_contenthash(data)
        signature2 = self._get_signature(timestamp, uri, method, contenthash)
        return signature == signature2

    def post(self, url: str, data: dict[str, str]) -> requests.Response:
        timestamp = self._timestamp()
        method = 'post'
        uri = ''.join((self.baseurl, url))

        contenthash = self._get_contenthash(data)

        self.session.headers['X-ATYX-TIMESTAMP'] = str(timestamp)
        self.session.headers['X-ATYX-SIGNATURE'] = self._get_signature(
            timestamp, uri, method, contenthash
        )

        response = self.session.post(uri, json=data)
        return response

    def _get_signature(self, timestamp: int, uri: str, method: str, contenthash: str):
        presign = '|'.join((str(timestamp), uri, method, contenthash))
        hash_object = hmac.new(
            self.apisecret.encode('utf-8'),
            presign.encode('utf-8'),
            hashlib.sha512,
        )
        return hash_object.hexdigest()

    @staticmethod
    def _timestamp() -> int:
        return int(time.time() * 1000)

    def _get_contenthash(self, data: dict[str, str]):
        hash_object = hashlib.sha512(json.dumps(data).encode('utf-8'))
        return hash_object.hexdigest()


if __name__ == '__main__':
    api_key = os.environ.get('INPUT_API_KEY')
    api_secret = os.environ.get('INPUT_API_SECRET')
    message = os.environ.get('INPUT_MESSAGE')

    if not all([api_key, api_secret, message]):
        print(
            'Error: INPUT_API_KEY, INPUT_API_SECRET, and INPUT_MESSAGE env vars are required'
        )
        sys.exit(1)

    print('apikey: ', api_key[:10], 'secret: ', api_secret[:10])

    api = NotifyApi(api_key, api_secret)
    response = api.send_message(message)
    print(f'Status: {response.status_code}')
    print(response.text)
