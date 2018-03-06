from django.db import models
from model_utils.models import TimeStampedModel
from solo.models import SingletonModel


class DaemonStatus:
    EXECUTING = 'EXECUTING'
    HALTED = 'HALTED'


STATUS_CHOICES = (
    (DaemonStatus.EXECUTING, 'Normal execution'),
    (DaemonStatus.HALTED, 'System halted, there was an error'),
)


class Daemon(TimeStampedModel, SingletonModel):
    block_number = models.IntegerField(default=0)
    last_error_block_number = models.IntegerField(default=0)
    status = models.CharField(max_length=9,
                              choices=STATUS_CHOICES,
                              default=DaemonStatus.EXECUTING)
    listener_lock = models.BooleanField(default=False)

    def __str__(self):
        return "Daemon at block {} {}".format(self.block_number, self.status)

    def is_executing(self):
        return self.status == DaemonStatus.EXECUTING

    def is_halted(self):
        return self.status == DaemonStatus.HALTED

    def set_executing(self):
        self.status = DaemonStatus.EXECUTING

    def set_halted(self):
        self.status = DaemonStatus.HALTED


class Block(TimeStampedModel):
    block_number = models.IntegerField()
    block_hash = models.CharField(primary_key=True, max_length=64)
    decoded_logs = models.TextField(default="[]")
    timestamp = models.IntegerField()

    def __str__(self):
        with_logs = " with decoded logs" if len(self.decoded_logs) > 2 else ""
        return 'Block {}{}'.format(self.block_number, with_logs)
