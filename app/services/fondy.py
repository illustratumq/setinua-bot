import hashlib
import logging
from datetime import datetime

import aiohttp
import ujson

from app.models import User

log = logging.getLogger(__name__)


class FondyAPIWrapper:

    def __init__(self, merchant_id: str, secret_key: str, credit_key: str):
        self.merchant_id = merchant_id
        self.secret_key = secret_key
        self.credit_key = credit_key
        self.headers = {'Content-Type': 'application/json'}

    @staticmethod
    async def _post_request(url: str, body_data: dict, headers: dict) -> dict:
        session = aiohttp.ClientSession(json_serialize=ujson.dumps)
        async with session.post(url, json=body_data, headers=headers) as resp:
            result = await resp.json()
        await session.close()
        return result

    @staticmethod
    def _check_status(answer: dict) -> bool:
        if answer.get('order_status') == 'approved':
            return True
        else:
            return False

    @staticmethod
    def _check_result(result: dict, p2p: bool = False):
        if result.get('response_status', None) == 'failure':
            log.exception(result)
            return False
        elif result['response_status'] == 'success':
            if p2p:
                return True
            return result['checkout_url']

    async def create_order(self, description: str, amount: int, user: User, event_id: str):
        amount *= 100
        date = datetime.now().isoformat()
        url = 'https://pay.fondy.eu/api/checkout/url/'
        order_desc = description
        order_id = f'event_{event_id}_user_{user.user_id}_date_{date}'
        signature = self._generate_signature(
            self.secret_key, str(amount), 'UAH', self.merchant_id, order_desc, order_id
        )
        data = {
            'request': {
                'order_id': order_id,
                'order_desc': order_desc,
                'currency': 'UAH',
                'amount': str(amount),
                'signature': signature,
                'merchant_id': self.merchant_id,
            }
        }
        response = await self._post_request(url, data, self.headers)
        url = self._check_result(response.get('response', dict()))
        return dict(order_id=order_id, url=url)

    async def check_order(self, order_id: str):
        url = 'https://pay.fondy.eu/api/status/order_id'
        signature = self._generate_signature(
            self.secret_key, self.merchant_id, order_id
        )
        data = {
            'request': {
                'order_id': order_id,
                'merchant_id': self.merchant_id,
                'signature': signature
            }
        }
        response = await self._post_request(url, data, self.headers)
        return self._check_status(response.get('response', dict()))

    async def withdraw(self, amount: int, receiver_card_number: str, user_id: int):
        date = datetime.now().strftime('%d%m%y%H%S%M')
        url = 'https://pay.fondy.eu/api/p2pcredit/'
        order_desc = f'user_{user_id}'
        order_id = 'test_order' + date
        signature = self._generate_signature(
            self.credit_key, str(amount), 'UAH', self.merchant_id, order_desc, order_id, receiver_card_number
        )
        body_data = {
            'request': {
                'order_id': order_id,
                'order_desc': order_desc,
                'currency': 'UAH',
                'amount': str(amount),
                'receiver_card_number': receiver_card_number,
                'signature': signature,
                'merchant_id': self.merchant_id,
            }
        }
        result = await self._post_request(url, body_data=body_data, headers=self.headers)
        result = result.get('response', dict())
        self._check_result(result, p2p=True)
        return True

    @staticmethod
    def _generate_signature(*values) -> str:
        string = '|'.join([str(m) for m in values])
        s = hashlib.sha1(bytes(string, 'utf-8'))
        return s.hexdigest()
