from django.core.management.base import BaseCommand

from ...models import Block, Daemon


class Command(BaseCommand):
    help = 'Force daemon to sync deleting blocks and restoring status'

    def handle(self, *args, **options):
        Block.objects.all().delete()
        Daemon.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Forcing daemon sync'))
