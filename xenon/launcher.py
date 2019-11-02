import asyncio

from bot import Xenon
from utils import logger


async def prepare_bot(_loop):
    logger.setup()
    return Xenon(loop=_loop)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = loop.run_until_complete(prepare_bot(loop))
    bot.run()
