import logging
from logging.handlers import TimedRotatingFileHandler

fh = TimedRotatingFileHandler(f"logs/bot.log", when="midnight", interval=1)
fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s'))
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s : %(message)s'))

# Internal
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.addHandler(ch)

# Discord
discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.INFO)
discord_logger.addHandler(fh)