# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-07 07:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_eth_events', '0006_block_timestamp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='block',
            name='decoded_logs',
            field=models.TextField(default='[]'),
        ),
    ]
