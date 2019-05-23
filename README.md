[![Build Status](https://travis-ci.org/gnosis/django-eth-events.svg?branch=master)](https://travis-ci.org/gnosis/django-eth-events)
[![Coverage Status](https://coveralls.io/repos/github/gnosis/django-eth-events/badge.svg?branch=master)](https://coveralls.io/github/gnosis/django-eth-events?branch=master)
![Python 3.6](https://img.shields.io/badge/Python-3.6-blue.svg)
![Django 2](https://img.shields.io/badge/Django-2-blue.svg)
[![PyPI version](https://badge.fury.io/py/django-eth-events.svg)](https://badge.fury.io/py/django-eth-events)

# django_eth_events
A standalone Django app for decoding Ethereum events compatible with Python 3.x. This app provides methods 
and [Celery tasks](http://www.celeryproject.org/) to continuously decode events from ethereum blockchain and
index then in a relational database. Too see an example of using this you can
check [Gnosis TradingDB repository](https://github.com/gnosis/pm-trading-db) and
[readthedocs documentation](https://gnosis-apollo.readthedocs.io/en/latest/pm-trading-db.html)

# Setup
If you want to install the latest stable release from PyPi:

`$ pip install django-eth-events`

If you want to install the latest development version from GitHub:

`$ pip install -e git+https://github.com/gnosis/django-eth-events.git#egg=Package`

Add django_eth_events to your INSTALLED_APPS:

```python
INSTALLED_APPS = (
    ...
    'django_eth_events',
    ...
)
```

# Settings
Provide an Ethereum _node url_. Provider will be detected depending on the protocol of the url. _http/s_, _ipc_ and
_ws(websocket)_ providers are available. **Recommended protocol is HTTPS.**
For example, using _https://localhost:8545_ communication with node will use **RPC through HTTPS**

```python
ETHEREUM_NODE_URL = os.environ['ETHEREUM_NODE_URL']
```

You can also provide an **IPC path** to a node running locally, which will be faster, using _ipc://PATH_TO_IPC_SOCKET_

Number of concurrent threads connected to the ethereum node can be configured:

```python
ETHEREUM_MAX_WORKERS = os.environ['ETHEREUM_MAX_WORKERS']
```

# IPFS
Provide an IPFS host and port:

```python
IPFS_HOST = os.environ['IPFS_HOST']
IPFS_PORT = os.environ['IPFS_PORT']
```

# Listening to Events
Create a new array `ETH_EVENTS` in your settings file and as follows:

```
ETH_EVENTS = [
    {
        'ADDRESSES': ['0x254dffcd3277C0b1660F6d42EFbB754edaBAbC2B'],
        'EVENT_ABI': '... ABI ...',
        'EVENT_DATA_RECEIVER': 'yourmodule.event_receivers.YourReceiverClass',
        'NAME': 'Your Contract Name',
        'PUBLISH': True,
    },
    {
        'ADDRESSES_GETTER': 'yourmodule.address_getters.YouCustomAddressGetter',
        'EVENT_ABI': '... ABI ...',
        'EVENT_DATA_RECEIVER': 'chainevents.event_receivers.MarketInstanceReceiver',
        'NAME': 'Standard Markets Buy/Sell/Short Receiver'
    }
]
```

Take a look at [Gnosis TradingDB repository](https://github.com/gnosis/pm-trading-db) and check out the full documentation.


# Django-eth-events development
The easiest way to start development on django-eth-events is to install dependencies using pip and a virtualenv, python3.6 is
required:

```
virtualenv -p python3.6 venv
source venv/bin/activate
pip install -r requirements
```

## Tests
You can launch tests using `python run_tests.py`. No additional services are required.

Django tests can also be used
```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
```

Coverage can be run using _coverage_ tool:
```bash
pip install coverage
DJANGO_SETTINGS_MODULE=config.settings.test coverage run --source=django_eth_events manage.py test
```

### Run specific test cases

```DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test django_eth_events.tests.test_file```

More information at [https://docs.djangoproject.com/en/2.2/topics/testing/overview/#running-tests](https://docs.djangoproject.com/en/2.2/topics/testing/overview/#running-tests).
