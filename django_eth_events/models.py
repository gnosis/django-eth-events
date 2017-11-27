from __future__ import unicode_literals

from django.db import models
from model_utils.models import TimeStampedModel
from solo.models import SingletonModel


class Daemon(TimeStampedModel, SingletonModel):
    block_number = models.IntegerField(default=0)
    last_error_block_number = models.IntegerField(default=0)


class Block(TimeStampedModel):
    block_number = models.IntegerField()
    block_hash = models.CharField(primary_key=True, max_length=64)
    decoded_logs = models.TextField(default="{}")