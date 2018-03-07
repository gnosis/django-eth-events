import errno
import traceback
from datetime import datetime, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import mail_admins
from django.db import transaction
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError, LocationValueError, PoolError

from .event_listener import EventListener
from .exceptions import (UnknownBlock, UnknownBlockReorgException,
                         UnknownTransaction, Web3ConnectionException)
from .models import Daemon

logger = get_task_logger(__name__)


def send_email(message):
    logger.info('Sending email with text: {}'.format(message))
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
            logger.error('Unknown Transaction hash, might be a reorg')
        except UnknownBlock:
            logger.error('Unknown Block hash, might be a reorg')
        except UnknownBlockReorgException:
            logger.error('Unknown Block hash, might be a reorg')
        except Web3ConnectionException:
            logger.error('Web3 cannot connect to providers')
        except Exception as err:
            # Not halting system for connection error cases
            if hasattr(err, 'errno') and (err.errno == errno.ECONNABORTED
                                          or err.errno == errno.ECONNRESET
                                          or err.errno == errno.ECONNREFUSED):
                logger.error("An error has occurred, errno: {}, trace: {}".format(err.errno, str(err)))
            elif (isinstance(err, HTTPError)
                  or isinstance(err, PoolError)
                  or isinstance(err, LocationValueError)
                  or isinstance(err, RequestException)):
                logger.error("An error has occurred, errno: {}, trace: {}".format(err.errno, str(err)))
            else:
                logger.error("Halting system due to error {}".format(str(err)))
                daemon = Daemon.get_solo()
                daemon.set_halted()
                daemon.save()
                # get last error block number database
                last_error_block_number = daemon.last_error_block_number
                # get current block number from database
                current_block_number = daemon.block_number
                logger.info("Current block number: {}, Last error block number: {}".format(
                    current_block_number, last_error_block_number
                ))
                if last_error_block_number < current_block_number:
                    # save block number into cache
                    daemon.last_error_block_number = current_block_number
                    daemon.save()
                    send_email(traceback.format_exc())
        finally:
            logger.info('Releasing LOCK')
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
        valid_interval = datetime.now() - timedelta(milliseconds=lock_interval)
        if daemon.modified < valid_interval and daemon.listener_lock is True:
            # daemon is deadlocked
            logger.info('Found deadlocked Daemon task, block number %d' % daemon.block_number)
            with transaction.atomic():
                daemon.listener_lock = False
                daemon.save()
    except Exception as err:
        logger.error(str(err))
        send_email(traceback.format_exc())
