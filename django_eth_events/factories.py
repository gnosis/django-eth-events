import factory
from django_eth_events import models


class DaemonFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.Daemon

    block_number = 0
