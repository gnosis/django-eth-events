# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.test import TestCase
from django_eth_events.tasks import deadlock_checker
from django_eth_events.factories import DaemonFactory
from django_eth_events.models import Daemon
from time import sleep


class TestCelery(TestCase):

    def test_deadlock_checker(self):
        daemon = DaemonFactory(listener_lock=True)
        # sleep process to simulate old Daemon instance
        sleep(2)
        deadlock_checker(2000) # 2 seconds
        daemon_test = Daemon.get_solo()
        # Test deadlock detection
        self.assertEquals(daemon_test.listener_lock, False)

        daemon.listener_lock = True
        daemon.save()
        deadlock_checker()
        daemon_test = Daemon.get_solo()
        self.assertEquals(daemon_test.listener_lock, True)


