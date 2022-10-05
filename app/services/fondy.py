import hashlib
import logging
from datetime import datetime

import aiohttp
import ujson

from app.models import User

log = logging.getLogger(__name__)


class FondyAPIWrapper:

    def __init__(self, merchant_id: str, secret_key: str):
        self.merchant_id = merchant_id
        self.secret_key = secret_key
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
    def _check_result(result: dict):
        if result.get('response_status', None) == 'failure':
            log.exception(result)
            return False
        elif result['response_status'] == 'success':
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

    @staticmethod
    def _generate_signature(*values) -> str:
        string = '|'.join([str(m) for m in values])
        s = hashlib.sha1(bytes(string, 'utf-8'))
        return s.hexdigest()
