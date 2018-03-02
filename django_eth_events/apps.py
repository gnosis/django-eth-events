from celery import Celery
from django.apps import AppConfig
from django.conf import settings

app = Celery('django_eth_events')


class DjangoEthEventsConfig(AppConfig):
    name = 'django_eth_events'

    def ready(self):
        super(DjangoEthEventsConfig, self).ready()
        app.config_from_object('django.conf:settings')
        app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, force=True)
