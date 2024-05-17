import httpx


class Client:

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def send_sms(
            self,
            channel_login: str,
            channel_password: str,
            sender: str,
            phone_number: int,
            text: str
    ) -> int:
        payload = {
            'username': channel_login,
            'password': channel_password,
            'command': 'submit',
            'ani': sender,
            'dnis': phone_number,
            'message': text
        }
        resp = await self.client.post(url='', data=payload)

        resp.raise_for_status()
        return resp.status_code
