from discord.ext import commands as cmd
import discord
import asyncio
import traceback
import logging

log = logging.getLogger(__name__)


class Botlist(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.update_loop())

    async def update_discordbots_org(self):
        guilds = await self.bot.get_guild_count()
        async with self.bot.session.post(
            url=f"https://discordbots.org/api/bots/{self.bot.user.id}/stats",
            headers={
                "Authorization": self.bot.config.dbl_token
            },
            json={
                "server_count": guilds,
                "shard_count": self.bot.shard_count
            }
        ) as resp:
            if resp.status != 200:
                log.error("Error posting stats to botlist: %s" % resp.status)

    async def update_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self.bot.change_presence(activity=discord.Activity(
                    name=f"{self.bot.config.prefix}help",
                    type=discord.ActivityType.watching
                ), afk=False)

                if self.bot.config.dbl_token is not None and self.bot.is_primary_shard():
                    await self.update_discordbots_org()

            except:
                traceback.print_exc()

            finally:
                await asyncio.sleep(10 * 60)


def setup(bot):
    bot.add_cog(Botlist(bot))
