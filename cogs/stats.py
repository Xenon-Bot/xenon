from discord.ext import commands
import discord
import asyncio
import traceback

import statics


class Stats:
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self._loop())

    async def _loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                await self.bot.change_presence(activity=discord.Activity(name=f"{len(self.bot.guilds)} Servers | x!help", type=3))
                await self.bot.dblpy.post_server_count(shard_count=self.bot.shard_count)
            except:
                traceback.print_exc()

            await asyncio.sleep(1*60)


def setup(bot):
    bot.add_cog(Stats(bot))