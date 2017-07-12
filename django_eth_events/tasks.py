from celery import shared_task
from django_eth_events.event_listener import EventListener
from celery.utils.log import get_task_logger
from celery.five import monotonic
from contextlib import contextmanager
from django.conf import settings
from django.core.cache import cache
from django.core.mail import mail_admins
from django_eth_events.models import Daemon

logger = get_task_logger(__name__)

oid = 'LOCK'

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


@shared_task
def event_listener():
    try:
        with cache_lock('eth_events', oid) as acquired:
            if acquired:
                bot = EventListener()
                bot.execute()
    except Exception as err:
        logger.error(str(err))
        # get last error block number from cache
        last_error_block_number = cache.get('last_error_block_number')
        # get current block number from database
        current_block_number = Daemon.block_number

        if last_error_block_number and last_error_block_number == current_block_number:
            pass
        else:
            # send email
            message = err.message
            mail_admins('[GnosisDB Celery Error] ', message)
            # save block number into cache
            cache.add('last_error_block_number', current_block_number)






