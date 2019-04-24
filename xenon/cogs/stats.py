from discord.ext import commands as cmd
from aioinflux import InfluxDBClient
import traceback
import asyncio


class Botlist(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats = {}

        self.build_scheme()

        if getattr(bot, "stats_loop", None) is None:
            bot.stats_loop = bot.loop.create_task(self.update_loop())

    def build_scheme(self):
        self.stats = {shard: {
            "messagesPerMinute": 0,
            "commandsPerMinute": 0,
            "guildsTotal": 0,
            "guildsPerMinute": 0,
            "guildsLeavePerMinute": 0,
            "guildsJoinPerMinute": 0,
            "membersTotal": 0
        } for shard in self.bot.shard_ids or [0]}

    @cmd.Cog.listener()
    async def on_message(self, msg):
        shard_id = msg.channel.guild.shard_id
        self.stats[shard_id]["messagesPerMinute"] += 1

    @cmd.Cog.listener()
    async def on_command(self, ctx):
        shard_id = ctx.guild.shard_id
        self.stats[shard_id]["commandsPerMinute"] += 1

    @cmd.Cog.listener()
    async def on_guild_join(self, guild):
        shard_id = guild.shard_id
        self.stats[shard_id]["guildsPerMinute"] += 1
        self.stats[shard_id]["guildsJoinPerMinute"] += 1

    @cmd.Cog.listener()
    async def on_guild_remove(self, guild):
        shard_id = guild.shard_id
        self.stats[shard_id]["guildsPerMinute"] -= 1
        self.stats[shard_id]["guildsLeavePerMinute"] += 1

    async def calculate_total_values(self):
        for guild in self.bot.guilds:
            self.stats[guild.shard_id]["guildsTotal"] += 1
            self.stats[guild.shard_id]["membersTotal"] += len(guild.members)

    async def update_loop(self):
        await self.bot.wait_until_ready()
        async with InfluxDBClient(db='xenon') as client:
            await client.create_database(db='xenon')
            while True:
                await asyncio.sleep(60)
                await self.calculate_total_values()
                try:
                    for shard_id, stats in self.stats.items():
                        await client.write([{
                            "measurement": measurement,
                            "tags": {"shard": str(shard_id)},
                            "fields": {"value": value}
                        } for measurement, value in stats.items()])

                    self.build_scheme()
                except:
                    traceback.print_exc()


def setup(bot):
    bot.add_cog(Botlist(bot))
