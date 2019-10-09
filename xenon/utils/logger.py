import logging
from logging.handlers import TimedRotatingFileHandler
import sys


def setup():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fh = TimedRotatingFileHandler(f"logs/bot.log", when="midnight", interval=1)
    fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s > %(message)s'))

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

    logger.addHandler(fh)
    logger.addHandler(ch)
