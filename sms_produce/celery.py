import os

from celery import Celery, signals

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_produce.settings')
app = Celery('sms_produce', include=['sms.task'])
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.worker_hijack_root_logger = False  # Celery 4/5

@signals.setup_logging.connect
def setup_celery_logging(**kwargs):
    # Ничего не делаем – оставляем логирование как настроено Django через fileConfig
    return
