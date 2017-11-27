from __future__ import unicode_literals
from django.apps import AppConfig
from django.conf import settings
from celery import Celery


app = Celery('django_eth_events')


class EtherLogsConfig(AppConfig):
    name = 'django_eth_events'

    def ready(self):
        super(EtherLogsConfig, self).ready()
        app.config_from_object('django.conf:settings')
        app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, force=True)