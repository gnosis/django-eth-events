import errno
import traceback
from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import mail_admins
from django.db import transaction
from django.utils import timezone
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError, LocationValueError, PoolError

from .event_listener import EventListener
from .exceptions import (UnknownBlock, UnknownBlockReorgException,
                         UnknownTransaction, Web3ConnectionException)
from .models import Daemon

logger = get_task_logger(__name__)


def send_email(message):
    logger.info('Sending email with text: %s', message)
    # send email
    mail_admins('[ETH Events Error] ', message)


@shared_task
def event_listener(provider=None):
    with transaction.atomic():
        daemon = Daemon.objects.select_for_update().first()
        if not daemon:
            logger.debug('Daemon singleton row was not created, creating')
            daemon = Daemon.get_solo()
        locked = daemon.listener_lock
        if not locked:
            logger.debug('LOCK acquired')
            daemon.listener_lock = True
            daemon.save()
    if locked:
        logger.debug('LOCK already being imported by another worker')
    else:
        try:
            el = EventListener(provider=provider)
            el.execute()
        except UnknownTransaction:
            logger.warning('Unknown Transaction hash, might be a reorg', exc_info=True)
        except UnknownBlock:
            logger.warning('Cannot get block by number/hash, might be a reorg', exc_info=True)
        except UnknownBlockReorgException:
            logger.warning('Unknown Block hash, might be a reorg', exc_info=True)
        except Web3ConnectionException:
            logger.warning('Web3 cannot connect to provider/s', exc_info=True)
        except Exception as err:
            logger.error('An error occurred', exc_info=True)
            daemon = Daemon.get_solo()

            # get last error block number database
            last_error_block_number = daemon.last_error_block_number
            # get current block number from database
            current_block_number = daemon.block_number
            logger.error('Daemon block number: %d, Last error block number: %d',
                         current_block_number, last_error_block_number)

            if last_error_block_number < current_block_number:
                # save block number into cache
                daemon.last_error_block_number = current_block_number
                daemon.last_error_date_time = timezone.now()

            daemon.save()
        finally:
            logger.debug('Releasing LOCK')
            with transaction.atomic():
                daemon = Daemon.objects.select_for_update().first()
                daemon.listener_lock = False
                daemon.save()


@shared_task
def deadlock_checker(lock_interval=60000):
    """
    Verifies whether celery tasks over the Daemon table are deadlocked.
    :param lock_interval: milliseconds
    """
    try:
        logger.info("Deadlock checker, lock_interval %d" % lock_interval)
        daemon = Daemon.get_solo()
        valid_interval = timezone.now() - timedelta(milliseconds=lock_interval)
        if daemon.modified < valid_interval and daemon.listener_lock is True:
            # daemon is deadlocked
            logger.info('Found deadlocked Daemon task, block number %d' % daemon.block_number)
            daemon.listener_lock = False
            daemon.save()
    except Exception:
        logger.exception("Problem found using deadlock checker")
        send_email(traceback.format_exc())
