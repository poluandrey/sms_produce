from typing import Coroutine
from pydantic import BaseModel, ConfigDict


class BroadcastTask(BaseModel):
    id: int
    sms_pack: list[Coroutine]

    model_config = ConfigDict(arbitrary_types_allowed=True)
