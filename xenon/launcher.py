import asyncio

from bot import Xenon
from utils import logger


async def prepare_bot(loop):
    logger.setup()
    return Xenon(loop=loop)


def run_bot():
    loop = asyncio.get_event_loop()
    bot = loop.run_until_complete(prepare_bot(loop))
    bot.run()


if __name__ == "__main__":
    run_bot()
