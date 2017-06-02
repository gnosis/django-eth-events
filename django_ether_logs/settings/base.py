# CELERY CONFIGURATION
# ------------------------------------------------------------------------------
# Additional apps
DJ_ADDITIONAL_APPS = ('taskapp.celery.CeleryConfig', 'kombu.transport.django', 'djcelery', 'solo',)
DJ_BROKER_URL = 'django://'
DJ_CELERY_ACCEPT_CONTENT = ['json']
DJ_CELERY_TASK_SERIALIZER = 'json'
DJ_CELERY_RESULT_SERIALIZER = 'json'
DJ_CELERY_IGNORE_RESULT = True
DJ_CELERY_RESULT_BACKEND = 'djcelery.backends.cache:CacheBackend'