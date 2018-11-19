import asyncio

from utils import database
from bot import Xenon


async def prepare_bot(loop):
    await database.setup()
    bot = Xenon(loop=loop)

    return bot


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = loop.run_until_complete(prepare_bot(loop))
    bot.run()
