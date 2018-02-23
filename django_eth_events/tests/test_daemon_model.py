# -*- coding: utf-8 -*-
from django.test import TestCase

from ..factories import DaemonFactory
from ..models import Daemon


class TestDaemonModel(TestCase):
    def test_default_value(self):
        daemon = DaemonFactory()
        self.assertIsNotNone(daemon.pk)
        self.assertEqual(daemon.block_number, 0)

    def test_singleton(self):
        self.assertEqual(0, Daemon.objects.all().count())
        DaemonFactory()
        d1 = Daemon.get_solo()
        self.assertEqual(1, Daemon.objects.all().count())
        d2 = Daemon.get_solo()
        self.assertEqual(1, Daemon.objects.all().count())
        self.assertEqual(d1.pk, d2.pk)
