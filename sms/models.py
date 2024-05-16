import logging
import random
from datetime import datetime, time, timedelta

from django.db import models

logger = logging.getLogger('app')


class Sender(models.Model):
    sender = models.CharField(unique=True, max_length=10)

    def __str__(self):
        return self.sender


class Text(models.Model):
    text = models.CharField(max_length=60, unique=True)

    def __str__(self):
        return self.text


class Broadcast(models.Model):
    name = models.CharField(unique=False, max_length=120)
    comment = models.CharField(unique=False, max_length=200)
    is_active = models.BooleanField()
    prefix = models.IntegerField(unique=False)
    phone_number_length = models.IntegerField()
    total_sms_count = models.IntegerField(unique=False)
    start_date = models.DateField()
    end_date = models.DateField()
    channel_login = models.CharField(max_length=10)
    channel_password = models.CharField(max_length=10)
    run_count = models.IntegerField(default=0)
    sent_sms = models.IntegerField(default=0)

    sender = models.ManyToManyField(to=Sender, related_name='senders')
    text = models.ManyToManyField(to=Text, related_name='texts')

    def __str__(self):
        return self.name

    def calculate_sms_count_to_send(self) -> int:
        end_of_broadcast = datetime.combine(self.end_date - timedelta(days=1), time=time(23, 59, 59))
        remain_run_count = int((end_of_broadcast - datetime.now()).total_seconds() / 60)
        if self.run_count == 0:
            calculated_sms_count = self.total_sms_count // remain_run_count
        else:
            calculated_sms_count = (self.total_sms_count - self.sent_sms) // remain_run_count

        return calculated_sms_count if calculated_sms_count > 0 else 1

    def generate_phone_number(self) -> int:
        part_length = self.phone_number_length - len(str(self.prefix))
        random_part = int(''.join(random.choices('0123456789', k=part_length)))

        return int(f'{self.prefix}{random_part}')