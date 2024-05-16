import asyncio
import logging
import random
from datetime import datetime

import httpx
from celery import shared_task
from django.conf import settings
from django.db.models import F, Q

from api.alaris.client import Client as SmsApiClient
from sms.models import Broadcast

logger = logging.getLogger('app')


@shared_task()
def broadcast_task():
    logger.debug('run task')
    client = httpx.AsyncClient(base_url=settings.ALARIS_SMS_BASE_URL)
    broadcasts = Broadcast.objects.prefetch_related('text').prefetch_related('sender').filter(
        ~Q(sent_sms=F('total_sms_count')), is_active=True, end_date__gt=datetime.now()
    )
    if not broadcasts:
        logger.warning('no broadcasts for run found')
        return

    api_client = SmsApiClient(client=client)
    sms_tasks = []
    for broadcast in broadcasts:
        sms_to_send = broadcast.calculate_sms_count_to_send()
        logger.info(f'broadcast: {broadcast.name}; sms to send - {sms_to_send};')
        for _ in range(sms_to_send):
            text = random.choice(broadcast.text.all())
            sender = random.choice(broadcast.sender.all())
            phone_number = broadcast.generate_phone_number()
            sms_tasks.append(
                api_client.send_sms(
                    channel_login=broadcast.channel_login,
                    channel_password=broadcast.channel_password,
                    phone_number=phone_number,
                    sender=sender,
                    text=text,
                ))

        broadcast.run_count += 1
        broadcast.sent_sms += sms_to_send
        broadcast.save()

    logger.info(f'total sms to send in task - {len(sms_tasks)}')
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(handle_broadcast(sms_tasks))


async def handle_broadcast(sms_tasks):
    results = await asyncio.gather(*[asyncio.create_task(task) for task in sms_tasks], return_exceptions=True)
