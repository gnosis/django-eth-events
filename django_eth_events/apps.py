from __future__ import unicode_literals

from celery import Celery
from django.apps import AppConfig
from django.conf import settings
import sys

class EtherLogsConfig(AppConfig):
    name = 'django_eth_events'
    app = None

    def __init__(self, *args, **kwargs):
        super(EtherLogsConfig, self).__init__(*args, **kwargs)
        self.app = Celery(self.name)

    def ready(self):
        super(EtherLogsConfig, self).ready()
        self.app.config_from_object('django.conf:settings')
        self.app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, force=True)
