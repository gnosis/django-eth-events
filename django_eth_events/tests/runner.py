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
    'django_ether_logs'
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
    DIRNAME = os.path.dirname(__file__)
    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)
    # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_ether_logs.settings.base')
    settings.configure(
        DEBUG=True,
        DATABASES=DATABASES,
        INSTALLED_APPS=INSTALLED_APPS
    )

    # django.setup()

    """from django.test.runner import DiscoverRunner
    failures = DiscoverRunner(
        top_level=os.getcwd(),
        verbosity=1,
        interactive=True,
        failfast=False
    ).run_tests(test_args)

    if failures:
        sys.exit(failures)"""

    from django.test import run_tests

    failures = run_tests(['django_ether_logs',], verbosity=1)
    if failures:
        sys.exit(failures)


runtests()
