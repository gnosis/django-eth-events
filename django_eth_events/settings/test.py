from .base import *

SECRET_KEY = 'testtest'
DEBUG = True

INSTALLED_APPS = (
    'solo',
    'django_eth_events',
)

ETHEREUM_NODE_HOST = 'localhost'
ETHEREUM_NODE_PORT = 8545
ETHEREUM_NODE_SSL = 0

RABBIT_HOSTNAME = 'rabbit'
RABBIT_USER = 'gnosisdb'
RABBIT_PASSWORD = 'gnosisdb'
RABBIT_PORT = '5672'
BROKER_URL = 'amqp://{user}:{password}@{hostname}:{port}'.format(
    user=RABBIT_USER,
    password=RABBIT_PASSWORD,
    hostname=RABBIT_HOSTNAME,
    port=RABBIT_PORT
)

# IPFS
IPFS_HOST = 'http://ipfs'  # 'ipfs'
IPFS_PORT = 5001


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
    }
}
