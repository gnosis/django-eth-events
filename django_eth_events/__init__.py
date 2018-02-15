from .apps import app as celery_app
default_app_config = 'django_eth_events.apps.EtherLogsConfig'
__all__ = ['celery_app']