# -*- coding: utf-8 -*-
from django.contrib import admin
from solo.admin import SingletonModelAdmin

from . import models

admin.site.register(models.Daemon, SingletonModelAdmin)
admin.site.register(models.Block)
