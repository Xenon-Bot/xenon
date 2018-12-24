import asyncio
import sys
import getopt

from utils import database
from bot import Xenon


async def prepare_bot(loop):
    opts, args = getopt.getopt(sys.argv[1:], "", ["shard_count=", "shard_ids="])

    arguments = {}
    for opt, arg in opts:
        opt = opt.strip("-")
        if opt == "shard_count":
            arg = int(arg)

        if opt == "shard_ids":
            arg = [int(id) for id in arg.split(",")]

        arguments[opt] = arg

    await database.setup()
    bot = Xenon(loop=loop, **arguments)

    return bot


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = loop.run_until_complete(prepare_bot(loop))
    bot.run()
