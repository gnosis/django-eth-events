import factory
from . import models


class DaemonFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.Daemon

    block_number = 0