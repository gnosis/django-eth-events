# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.test import TestCase
from eth.mail_batch import MailBatch
from django.core import mail


class TestMail(TestCase):

    def setUp(self):
        self.batch = MailBatch()
        self.test_logs = [
            {
                u'address': u'0xa6d9c5f7d4de3cef51ad3b7235d79ccc95114de5',
                u'name': u'ContractInstantiation',
                u'params': [
                    {
                        u'name': u'sender',
                        u'value': u'0x65039084cc6f4773291a6ed7dcf5bc3a2e894ff3'
                    },
                    {
                        u'name': u'instantiation',
                        u'value': u'0x17e054b16ca658789c927c854976450adbda7df0'
                    }
                ]
            }
        ]

    def test_add_mail(self):
        self.assertEqual(len(self.batch.users), 0)
        self.batch.add_mail("test@test.com", {})
        self.assertEqual(len(self.batch.users), 0)
        self.batch.add_mail("test@test.com", {'multisig': self.test_logs})
        self.assertEqual(len(self.batch.users), 1)

    def test_send_mail(self):
        self.batch.add_mail("test@test.com", {'multisig': self.test_logs})
        self.assertEqual(len(self.batch.users), 1)
        self.batch.send_mail()
        self.assertEqual(len(self.batch.users), 0)
        self.assertEqual(len(mail.outbox), 1)