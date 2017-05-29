from celery import shared_task
from bot import Bot
from celery.contrib import rdb
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task
def run_bot():
    try:
        bot = Bot()
        bot.execute()
    except Exception as err:
        logger.error(str(err))
