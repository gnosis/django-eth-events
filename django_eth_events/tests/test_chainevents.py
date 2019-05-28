from django.test import TestCase
from ..chainevents import AbstractEventReceiver, AbstractAddressesGetter


class EventReceiverImpl(AbstractEventReceiver):
    pass


class AddressGetterImpl(AbstractAddressesGetter):
    pass


class TestAbstractClasses(TestCase):

    def test_abstract_class_detected(self):
        # Make sure abstract classes gets detected as abstracts. This to prevent
        # not desired behaviour when updating Python version.
        with self.assertRaises(TypeError):
            EventReceiverImpl()

        with self.assertRaises(TypeError):
            AddressGetterImpl()
