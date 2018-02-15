import factory

from .models import Daemon


class DaemonFactory(factory.DjangoModelFactory):

    class Meta:
        model = Daemon

    block_number = 0
