# CELERY CONFIGURATION
# ------------------------------------------------------------------------------
# Additional apps
ETHER_LOGS_ADDITIONAL_APPS = ('django_ether_logs.apps.EtherLogsConfig', 'kombu.transport.django', 'djcelery', 'solo',)
ETHER_LOGS_BROKER_URL = 'django://'
ETHER_LOGS_CELERY_ACCEPT_CONTENT = ['json']
ETHER_LOGS_CELERY_TASK_SERIALIZER = 'json'
ETHER_LOGS_CELERY_RESULT_SERIALIZER = 'json'
ETHER_LOGS_CELERY_IGNORE_RESULT = True
ETHER_LOGS_CELERY_RESULT_BACKEND = 'djcelery.backends.cache:CacheBackend'