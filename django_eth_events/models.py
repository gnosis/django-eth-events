from __future__ import unicode_literals

from django.db import models
from model_utils.models import TimeStampedModel
from solo.models import SingletonModel


STATUS_CHOICES = (
    ('EXECUTING', 'Normal execution'),
    ('HALTED', 'System halted, there was an error'),
)


class Daemon(TimeStampedModel, SingletonModel):
    block_number = models.IntegerField(default=0)
    last_error_block_number = models.IntegerField(default=0)
    status = models.CharField(max_length=9, choices=STATUS_CHOICES, default='EXECUTING')


class Block(TimeStampedModel):
    block_number = models.IntegerField()
    block_hash = models.CharField(primary_key=True, max_length=64)
    decoded_logs = models.TextField(default="{}")
    timestamp = models.IntegerField()