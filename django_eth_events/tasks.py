from celery import shared_task
from django_eth_events.event_listener import EventListener, UnknownBlock, UnknownTransaction
from celery.utils.log import get_task_logger
from django.db import transaction
from contextlib import contextmanager
from django.conf import settings
from django.core.cache import cache
from django.core.mail import mail_admins
from django_eth_events.models import Daemon
from functools import wraps
import traceback

logger = get_task_logger(__name__)

def send_email(message):
    logger.info('Sending email with text: {}'.format(message))
    # send email
    mail_admins('[ETH Events Error] ', message)


@shared_task
def event_listener():
    with transaction.atomic():
        daemon = Daemon.get_solo()
        locked = daemon.listener_lock
        if locked:
            logger.debug(
                'LOCK already being imported by another worker')
        else:
            daemon.listener_lock = True
            daemon.save()
            bot = EventListener()
            try:
                bot.execute()
            except UnknownTransaction:
                logger.error('Unknown Transaction hash, might be a reorg')
            except UnknownBlock:
                logger.error('Unknown Block hash, might be a reorg')
            except Exception as err:
                logger.error(str(err))
                daemon = Daemon.get_solo()
                daemon.status = 'HALTED'
                daemon.save()
                # get last error block number database
                last_error_block_number = daemon.last_error_block_number
                # get current block number from database
                current_block_number = daemon.block_number
                logger.info("Current block number: {}, Last error block number: {}".format(
                    current_block_number, last_error_block_number
                ))
                if last_error_block_number < current_block_number:
                    send_email(traceback.format_exc())
                    # save block number into cache
                    daemon.last_error_block_number = current_block_number
                    daemon.save()
            finally:
                logger.info('Releasing LOCK')
                daemon.listener_lock = False
                daemon.save()




