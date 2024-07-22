import asyncio
import logging
import random
from datetime import datetime, time
from time import sleep
from typing import Coroutine, Optional

import httpx
from celery import shared_task
from celery.signals import task_postrun
from django.conf import settings
from django.db.models import F, Q
from django.core.cache import cache

from api.alaris.client import Client as SmsApiClient
from sms.schema import BroadcastTask, SmsParams
from sms.models import Broadcast

logger = logging.getLogger('app')


@shared_task()
def broadcast_task_handler():
    logger.info('start')
    try:
        broadcasts = Broadcast.objects.prefetch_related('text').prefetch_related('sender').filter(
            ~Q(sent_sms=F('total_sms_count')), is_active=True,
            end_date__gt=datetime.now().replace(second=0, microsecond=0)
        )
        if not broadcasts:
            logger.warning('no broadcasts for run found')
            return
        sms_tasks = []
        total_sms_sms_to_send = 0
        for broadcast in broadcasts:
            prefixes = [obj.prefix for obj in broadcast.prefix.all()]
            exists_phone_numbers = []
            sms_pack: list[dict] = []
            calculated_sms_count_in_br = broadcast.calculate_sms_count_to_send()
            total_sms_sms_to_send += calculated_sms_count_in_br
            for _ in range(calculated_sms_count_in_br):
                sms_params = generate_sms_param(prefixes=prefixes, broadcast=broadcast,
                                                exists_phone_numbers=exists_phone_numbers)
                if sms_params:
                    exists_phone_numbers.append(sms_params.phone_number)
                    cache_time_out = (datetime.combine(broadcast.end_date, time(00, 00, 00)) - datetime.now()).seconds
                    cache.set(f'{broadcast.id}:{sms_params.phone_number}', sms_params.phone_number, timeout=cache_time_out)
                    sms_pack.append(sms_params.dict())

            sms_tasks.append(BroadcastTask(id=broadcast.id, sms_pack=sms_pack))
            broadcast.run_count += 1
            broadcast.save()

        logger.info(f'total sms to send in task - {total_sms_sms_to_send}')

        if sms_tasks:
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            sent_result = event_loop.run_until_complete(send_sms_pack(sms_tasks))
            handle_sent_result(broadcasts, sent_result)
    except Exception as err:
        logger.error(err)


def generate_sms_param(prefixes: list[int], broadcast: Broadcast, exists_phone_numbers: list[int]) -> Optional[SmsParams]:
    prefix = random.choice(prefixes)
    text = random.choice(broadcast.text.all())
    sender = random.choice(broadcast.sender.all())
    phone_number = broadcast.generate_phone_number(prefix)
    generation_cnt = 0
    while phone_number in exists_phone_numbers or is_phone_already_used(broadcast.id, phone_number):
        phone_number = broadcast.generate_phone_number(prefix)
        prefix = random.choice(prefixes)
        generation_cnt += 1
        if generation_cnt == 10:
            logger.warning('stuck in loop')
            return

    logger.debug(f'broadcast {broadcast.id}: generated phone number {phone_number}')
    return SmsParams(
        channel_login=broadcast.channel_login,
        channel_password=broadcast.channel_password,
        phone_number=phone_number,
        sender=sender.sender,
        text=text.text,
        broadcast_id=broadcast.id
    )


async def send_sms_pack(sms_tasks: list[BroadcastTask]) -> dict[int, list[int]]:
    try:
        async with httpx.AsyncClient(base_url=settings.ALARIS_SMS_BASE_URL,
                                     limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
                                     timeout=httpx.Timeout(10.0)) as client:
            api_client = SmsApiClient(client=client)
            result = {}
            tasks: list[Coroutine] = []
            for broadcast_task in sms_tasks:
                tasks.extend([api_client.send_sms(**params) for params in broadcast_task.sms_pack])
            pending_tasks = []
            responses = []
            batch_size = 200
            while tasks or pending_tasks:
                logger.debug(f'Remain {len(tasks)} requests')

                # Create new tasks from the remaining coroutines
                current_batch = [asyncio.create_task(tasks.pop(0)) for _ in
                                 range(min(batch_size - len(pending_tasks), len(tasks)))]

                # Combine current batch with any pending tasks
                proceed_tasks = current_batch + pending_tasks
                logger.debug(f'Count of proceed_tasks: {len(proceed_tasks)}')

                done, pending = await asyncio.wait(proceed_tasks, timeout=1)
                logger.debug(f'Done: {len(done)}')
                logger.debug(f'Pending: {len(pending)}')

                responses.extend([task.result() for task in done if not task.exception()])
                pending_tasks = list(pending)

        for resp in responses:
            broadcast_id, http_status_code = resp
            if broadcast_id not in result:
                result[broadcast_id] = [http_status_code]
            else:
                result[broadcast_id].append(http_status_code)
    except Exception as err:
        logger.error(err)
    return result


def handle_sent_result(broadcasts, sms_sent_results: dict[int, list[int]]):
    for broadcast_id, results in sms_sent_results.items():
        broadcast = broadcasts.get(id=broadcast_id)
        accepted_sms_count = len([result for result in results if result == 200])
        logger.info(
            f'broadcast_id - {broadcast_id}; accepted_sms_count - {accepted_sms_count}; '
            f'rejected_sms_count - {len(results) - accepted_sms_count}'
        )
        broadcast.sent_sms += accepted_sms_count
        broadcast.save()


def is_phone_already_used(broadcast_id: int, phone_number: int) -> bool:
    if cache.get(f'{broadcast_id}:{phone_number}'):
        logger.debug(f'{broadcast_id}:{phone_number} find in cache!')
        return True

    return False


@task_postrun.connect(sender=broadcast_task_handler)
def broadcast_after_run(**kwargs):
    logger.debug('start execute post run signal')
    broadcasts = Broadcast.objects.filter(
        (Q(sent_sms=F('total_sms_count')) | Q(end_date__lte=datetime.now())),
        is_active=True
    ).all()

    for broadcast in broadcasts:
        broadcast.is_active = False
        broadcast.save()
        logger.info(f'set broadcast: {broadcast.id} inactive')
    logger.debug('finished execute post  run signal')
