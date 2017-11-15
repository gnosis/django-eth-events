# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin
from solo.admin import SingletonModelAdmin
from . import models


admin.site.register(models.Daemon, SingletonModelAdmin)
