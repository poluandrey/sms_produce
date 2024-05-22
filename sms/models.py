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

    def calculate_remain_run_count(self, start_date: datetime) -> int:
        business_hours = 0
        business_minutes = 0
        current_date = start_date
        if current_date.minute != 0:
            business_minutes = 60 - current_date.minute
            current_date += timedelta(hours=1)
            current_date = current_date.replace(minute=0)
        while current_date < datetime.combine(self.end_date, time(23, 59, 59)):
            if 8 <= current_date.hour < 20:
                business_hours += 1
            current_date += timedelta(hours=1)
        return int(business_hours * 60 + business_minutes)

    def calculate_sms_count_to_send(self) -> int:
        # end_of_broadcast = datetime.combine(self.end_date - timedelta(days=1), time=time(23, 59, 59))
        start_date = datetime.now()
        remain_run_count = self.calculate_remain_run_count(start_date=start_date)
        logger.info(f'broadcast {self.id}: from {start_date} to {self.end_date} remain {remain_run_count} runs')
        if self.run_count == 0:
            calculated_sms_count = self.total_sms_count // remain_run_count
        else:
            calculated_sms_count = (self.total_sms_count - self.sent_sms) // remain_run_count
        sms_to_send = round(calculated_sms_count * random.triangular(0, 2)) if calculated_sms_count > 0 else 1
        # because of using multiple to random in sms_to_send calculation sms_to_send + self.sent_sms
        # can be more than self.total_sms
        if self.total_sms_count < self.sent_sms + sms_to_send:
            sms_to_send = self.total_sms_count - self.sent_sms
        logger.info(f'broadcast {self.id}: calculated number of sms to send: {sms_to_send}')
        return sms_to_send

    def generate_phone_number(self) -> int:
        part_length = self.phone_number_length - len(str(self.prefix))
        random_part = int(''.join(random.choices('0123456789', k=part_length)))

        return int(f'{self.prefix}{random_part}')
