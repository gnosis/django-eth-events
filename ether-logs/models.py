from __future__ import unicode_literals

from django.db import models
from model_utils.models import TimeStampedModel
from solo.models import SingletonModel


class Daemon(TimeStampedModel, SingletonModel):
    block_number = models.IntegerField(default=0)