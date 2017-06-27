from celery import shared_task
from django_eth_events.event_listener import EventListener
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task
def event_listener():
    try:
        bot = EventListener()
        bot.execute()
    except Exception as err:
        logger.error(str(err))
