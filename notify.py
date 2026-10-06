import hashlib
import hmac
import json
import os
import sys
import time
from urllib.parse import urlparse

import requests


class NotifyApi:
    def __init__(self, apikey: str, apisecret: str):
        self.apikey = apikey
        self.apisecret = apisecret
        self.baseurl = os.environ.get('NOTIFY_BASEURL') or 'https://notify.atyx.ru/notify/'

        self.session = requests.Session()
        self.session.headers.update(
            {
                'Content-Type': 'application/json;charset=utf-8',
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

        signature = self._get_signature(timestamp, uri, method, contenthash)
        self.session.headers['X-ATYX-TOKEN'] = f'{self.apikey}:{timestamp}:{signature}'

        response = self.session.post(uri, json=data, timeout=(5, 20), allow_redirects=False)
        return response

    def _get_signature(self, timestamp: int, uri: str, method: str, contenthash: str):
        parsed = urlparse(uri)
        netloc = parsed.hostname
        uri = f'{parsed.scheme}://{netloc}{parsed.path}'

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


def main():
    api_key = os.environ.get('API_KEY')
    api_secret = os.environ.get('API_SECRET')
    message = os.environ.get('MESSAGE')

    if not all([api_key, api_secret, message]):
        print('Error: API_KEY, API_SECRET, and MESSAGE env vars are required')
        return 1

    api = NotifyApi(api_key, api_secret)
    try:
        response = api.send_message(message)
        print(f'Status: {response.status_code}')
        if response.status_code != 200:
            print('Error: Notify API returned an unsuccessful HTTP status')
            return 1
        result = response.json()
    except (requests.RequestException, ValueError):
        print('Error: Notify request failed or response is not JSON')
        return 1
    finally:
        api.session.close()

    if not isinstance(result, dict) or result.get('status') != 'ok':
        print('Error: Notify API did not confirm message delivery')
        return 1
    print('Notification sent')
    return 0


if __name__ == '__main__':
    sys.exit(main())
