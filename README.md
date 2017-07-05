# django_eth_events
A standalone Django app for decoding Ethereum events.

# Setup
If you want to install the latest stable release from PyPi:

```$ pip install django-eth-events```

If you want to install the latest development version from GitHub:

```$ pip install -e git+https://github.com/gnosis/django-eth-events.git#egg=Package```

Add django_eth_events to your INSTALLED_APPS:

```
INSTALLED_APPS = (
    ...
    'django_eth_events',
    ...
)
```

# Settings
Create a new array variable in your settings file and call it ETH_EVENTS as follows:

```
ETH_EVENTS = [
    {
        'ADDRESSES': ['254dffcd3277c0b1660f6d42efbb754edababc2b'],
        'ADDRESSES_GETTER': '',
        'EVENT_ABI': '... ABI ...',
        'EVENT_DATA_RECEIVER': 'yourmodule.event_receivers.YourReceiverClass',
        'NAME': 'Your Contract Name',
        'PUBLISH': True,
    },
    {
        'ADDRESSES': [],
        'ADDRESSES_GETTER': 'yourmodule.address_getters.YouCustomAddressGetter',
        'EVENT_ABI': '... ABI ...',
        'EVENT_DATA_RECEIVER': 'chainevents.event_receivers.MarketInstanceReceiver',
        'NAME': 'Standard Markets Buy/Sell/Short Receiver'
    }
]
```

Take a look at GnosisDB repository and check out the full documentation: [link](https://github.com/gnosis/gnosisdb/blob/master/README.md).
