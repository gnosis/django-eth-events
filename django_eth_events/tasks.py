from celery import shared_task
from django_eth_events.event_listener import EventListener
from celery.utils.log import get_task_logger
from celery.five import monotonic
from contextlib import contextmanager
from django.conf import settings
from django.core.cache import cache
from django.core.mail import mail_admins
from django_eth_events.models import Daemon
from functools import wraps

logger = get_task_logger(__name__)

oid = 'LOCK'


def error_email(func):

    @wraps(func)
    def inner(*args, **kwargs):

        def send_email(message):
            # send email
            mail_admins('[ETH Events Error] ', message)

        try:
            func(*args, **kwargs)
        except Exception as err:
            logger.error(str(err))
            # get last error block number from cache
            last_error_block_number = cache.get_or_set('last_error_block_number', 0)
            # get current block number from database
            current_block_number = Daemon.get_solo().block_number

            if last_error_block_number < current_block_number:
                send_email(err.message)
                # save block number into cache
                cache.set('last_error_block_number', current_block_number)
            elif not last_error_block_number:
                # send email
                send_email(err.message)
                # save block number into cache
                cache.set('last_error_block_number', current_block_number)

    return inner


@contextmanager
def cache_lock(lock_id, oid):
    timeout_at = monotonic() + settings.CELERY_LOCK_EXPIRE
    # cache.add fails if the key already exists
    status = cache.add(lock_id, oid, settings.CELERY_LOCK_EXPIRE)
    try:
        yield status
    finally:
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        if monotonic() < timeout_at:
            # don't release the lock if we exceeded the timeout
            # to lessen the chance of releasing an expired lock
            # owned by someone else.
            cache.delete(lock_id)


@error_email
@shared_task
def event_listener():
    with cache_lock('eth_events', oid) as acquired:
        if acquired:
            bot = EventListener()
            bot.execute()




