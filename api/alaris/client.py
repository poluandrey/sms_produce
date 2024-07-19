import httpx
from httpx import HTTPStatusError

import logging

logger = logging.getLogger('app')


class Client:

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def send_sms(
            self,
            channel_login: str,
            channel_password: str,
            sender: str,
            phone_number: int,
            text: str,
            broadcast_id: int
    ) -> tuple[int, int]:
        payload = {
            'username': channel_login,
            'password': channel_password,
            'command': 'submit',
            'ani': sender,
            'dnis': phone_number,
            'message': text
        }
        resp = await self.client.post(url='', data=payload)
        # logger.debug(f'br_id: {broadcast_id}, phone_number: {phone_number}, resp: {resp}')
        try:
            resp.raise_for_status()
        except HTTPStatusError as e:
            return broadcast_id, resp.status_code

        return broadcast_id, resp.status_code
