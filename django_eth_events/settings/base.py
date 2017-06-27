# CELERY CONFIGURATION
# ------------------------------------------------------------------------------
# Additional apps
ETHER_LOGS_ADDITIONAL_APPS = ('django_ether_logs.apps.EtherLogsConfig', 'kombu.transport.django', 'djcelery', 'solo',)

RABBIT_HOSTNAME = 'rabbit'
RABBIT_USER = 'gnosisdb'
RABBIT_PASSWORD = 'gnosisdb'
RABBIT_PORT = '5672'
ETHER_LOGS_BROKER_URL = 'amqp://{user}:{password}@{hostname}:{port}'.format(
    user=RABBIT_USER,
    password=RABBIT_PASSWORD,
    hostname=RABBIT_HOSTNAME,
    port=RABBIT_PORT
)

ETHER_LOGS_BROKER_POOL_LIMIT = 1
ETHER_LOGS_BROKER_CONNECTION_TIMEOUT = 10
# Celery configuration
ETHER_LOGS_CELERY_RESULT_SERIALIZER = 'json'
ETHER_LOGS_CELERY_RESULT_BACKEND = 'djcelery.backends.cache:CacheBackend'
# configure queues, currently we have only one
ETHER_LOGS_CELERY_DEFAULT_QUEUE = 'default'
# Sensible settings for celery
ETHER_LOGS_CELERY_ALWAYS_EAGER = False
ETHER_LOGS_CELERY_ACKS_LATE = True
ETHER_LOGS_CELERY_TASK_PUBLISH_RETRY = True
ETHER_LOGS_CELERY_DISABLE_RATE_LIMITS = False
# By default we will ignore result
# If you want to see results and try out tasks interactively, change it to False
# Or change this setting on tasks level
ETHER_LOGS_CELERY_IGNORE_RESULT = False
ETHER_LOGS_CELERY_SEND_TASK_ERROR_EMAILS = False
ETHER_LOGS_CELERY_TASK_RESULT_EXPIRES = 600
# Don't use pickle as serializer, json is much safer
ETHER_LOGS_CELERY_TASK_SERIALIZER = "json"
ETHER_LOGS_CELERY_ACCEPT_CONTENT = ['application/json']
ETHER_LOGS_CELERYD_HIJACK_ROOT_LOGGER = False
ETHER_LOGS_CELERYD_PREFETCH_MULTIPLIER = 1
ETHER_LOGS_CELERYD_MAX_TASKS_PER_CHILD = 1000
