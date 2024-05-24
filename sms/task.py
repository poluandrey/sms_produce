import asyncio
import logging
import random
from datetime import datetime, timedelta, time
from typing import Union, Any

import httpx
from celery import shared_task
from django.conf import settings
from django.db.models import F, Q
from httpx import HTTPStatusError

from api.alaris.client import Client as SmsApiClient
from sms.schema import BroadcastTask
from sms.models import Broadcast


logger = logging.getLogger('app')


@shared_task()
def broadcast_task_handler():
    client = httpx.AsyncClient(base_url=settings.ALARIS_SMS_BASE_URL)
    broadcasts = Broadcast.objects.prefetch_related('text').prefetch_related('sender').filter(
        ~Q(sent_sms=F('total_sms_count')), is_active=True, end_date__gt=datetime.now()
    )
    if not broadcasts:
        logger.warning('no broadcasts for run found')
        return

    api_client = SmsApiClient(client=client)
    sms_tasks = []
    total_sms_sms_to_send = 0
    for broadcast in broadcasts:
        sms_pack = []
        sms_to_send = broadcast.calculate_sms_count_to_send()
        # logger.info(f'broadcast: {broadcast.name}; sms to send - {sms_to_send};')
        total_sms_sms_to_send += sms_to_send
        for _ in range(sms_to_send):
            text = random.choice(broadcast.text.all())
            sender = random.choice(broadcast.sender.all())
            phone_number = broadcast.generate_phone_number()
            sms_pack.append(
                api_client.send_sms(
                    channel_login=broadcast.channel_login,
                    channel_password=broadcast.channel_password,
                    phone_number=phone_number,
                    sender=sender,
                    text=text,
                ))

        sms_tasks.append(BroadcastTask(id=broadcast.id, sms_pack=sms_pack))

        broadcast.run_count += 1
        broadcast.save()

    logger.info(f'total sms to send in task - {total_sms_sms_to_send}')
    event_loop = asyncio.get_event_loop()
    sent_result = event_loop.run_until_complete(asyncio.gather(*[send_sms_pack(task) for task in sms_tasks]))
    handle_sent_result(broadcasts, sent_result)


async def send_sms_pack(sms_tasks: BroadcastTask) -> tuple[int, Union[HTTPStatusError, Any]]:
    results = await asyncio.gather(*[asyncio.create_task(task) for task in sms_tasks.sms_pack], return_exceptions=True)
    logger.debug(f'broadcast id - {sms_tasks.id}; result - {results}')
    return sms_tasks.id, results


def handle_sent_result(broadcasts, sms_sent_results):
    for task in sms_sent_results:
        broadcast_id, results = task
        broadcast = broadcasts.get(id=broadcast_id)
        accepted_sms_count = len([result for result in results if result == 200])
        logger.info(f'broadcast_id - {broadcast_id}; accepted_sms_count - {accepted_sms_count}')
        broadcast.sent_sms += accepted_sms_count
        broadcast.save()

        if (broadcast.sent_sms >= broadcast.total_sms_count or
            datetime.combine(broadcast.end_date - timedelta(days=1),
                             time(23, 59, 59)) < datetime.now()):
            broadcast.is_active = False
            broadcast.save()
