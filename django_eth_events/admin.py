# -*- coding: utf-8 -*-
from django.contrib import admin
from solo.admin import SingletonModelAdmin

from . import models


class DaemonAdmin(SingletonModelAdmin):
    readonly_fields = ('created', 'modified')


class BlockAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')


admin.site.register(models.Daemon, DaemonAdmin)
admin.site.register(models.Block, BlockAdmin)
