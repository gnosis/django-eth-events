[![Build Status](https://travis-ci.org/gnosis/django-eth-events.svg?branch=master)](https://travis-ci.org/gnosis/django-eth-events)
[![Coverage Status](https://coveralls.io/repos/github/gnosis/django-eth-events/badge.svg?branch=master)](https://coveralls.io/github/gnosis/django-eth-events?branch=master)
![Python 3.6](https://img.shields.io/badge/Python-3.6-blue.svg)
![Django 2](https://img.shields.io/badge/Django-2-blue.svg)
[![PyPI version](https://badge.fury.io/py/django-eth-events.svg)](https://badge.fury.io/py/django-eth-events)

# django_eth_events
A standalone Django app for decoding Ethereum events compatible with Python 2.7 and 3.x

# Setup
If you want to install the latest stable release from PyPi:

`$ pip install django-eth-events`

If you want to install the latest development version from GitHub:

`$ pip install -e git+https://github.com/gnosis/django-eth-events.git#egg=Package`

Add django_eth_events to your INSTALLED_APPS:

```
INSTALLED_APPS = (
    ...
    'django_eth_events',
    ...
)
```

# Settings
Provide an Ethereum _host_, _port_ and _SSL (0, 1)_. Use _SSL = 1_ only if your Ethereum host supports HTTPS/SSL.
Communication with node will use **RPC through HTTP/S**

```
ETHEREUM_NODE_HOST = os.environ['ETHEREUM_NODE_HOST']
ETHEREUM_NODE_PORT = os.environ['ETHEREUM_NODE_PORT']
ETHEREUM_NODE_SSL = bool(int(os.environ['ETHEREUM_NODE_SSL']))
```

You can also provide an **IPC path** to a node running locally, which will be faster.
You can use the environment variable  _ETHEREUM_IPC_PATH_.
If set, it will override _ETHEREUM_NODE_HOST_ and _ETHEREUM_NODE_PORT_, so **IPC will
be used instead of RPC**:

```
ETHEREUM_IPC_PATH = os.environ['ETHEREUM_IPC_PATH']
```

Number of concurrent threads connected to the ethereum node can be configured:

```
ETHEREUM_MAX_WORKERS = os.environ['ETHEREUM_MAX_WORKERS']
```

Provide an IPFS host and port:

```
IPFS_HOST = os.environ['IPFS_HOST']
IPFS_PORT = os.environ['IPFS_PORT']
```

Create a new array variable in your settings file and call it ETH_EVENTS as follows:

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

Take a look at GnosisDB repository and check out the full documentation: [link](https://github.com/gnosis/gnosisdb).

# Tests
You can launch tests using `python run_tests.py`. No additional services are required.

Django tests can also be used
```
export DJANGO_SETTINGS_MODULE=settings.test
export PYTHONPATH="/folder/to/project/django-eth-events"
python django_eth_events/manage.py test
```

Coverage can be run using _coverage_ tool:
```
pip install coverage
coverage run --source=django_eth_events django_eth_events/manage.py test
```
