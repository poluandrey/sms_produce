from typing import Coroutine, Dict
from pydantic import BaseModel, ConfigDict


class BroadcastTask(BaseModel):
    id: int
    sms_pack: list[Dict]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SmsParams(BaseModel):
    channel_login: str
    channel_password: str
    sender: str
    phone_number: int
    text: str
    broadcast_id: int
