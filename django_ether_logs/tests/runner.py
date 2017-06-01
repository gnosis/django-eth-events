import os, sys
import django
from django.conf import settings

SECRET_KEY = 'testtest'
DEBUG = True

INSTALLED_APPS=(
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django_ether_logs',
    'django_ether_logs.tests',
)

LOGGING={
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/var/www/mysite/sqlite.db',
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

ROOT_URLCONF = 'urls'


def runtests(*test_args):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_ether_logs.tests.runner')
    django.setup()

    DIRNAME = os.path.dirname(__file__)

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    if django.VERSION < (1, 8):
        from django.test.simple import DjangoTestSuiteRunner
        failures = DjangoTestSuiteRunner(
            top_level=os.getcwd(),
            verbosity=1,
            interactive=True,
            failfast=False
        ).run_tests(['tests'])

        if failures:
            sys.exit(failures)

    else:
        from django.test.runner import DiscoverRunner
        failures = DiscoverRunner(
            top_level=os.getcwd(),
            verbosity=1,
            interactive=True,
            failfast=False
        ).run_tests(test_args)

        if failures:
            sys.exit(failures)


runtests()