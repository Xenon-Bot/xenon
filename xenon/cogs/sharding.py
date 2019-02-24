from discord.ext import commands as cmd
import traceback
import asyncio

from utils import pubsub


class Sharding(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

        if self.bot.is_splitted():
            self.bot.loop.create_task(self.update_loop())
            self.bot.loop.create_task(self.subscribe_to_events())

    async def update_database(self):
        latencies = self.bot.latencies
        stats = {str(id): {"latency": latency, "guilds": 0, "users": 0}
                 for id, latency in latencies}
        for guild in self.bot.guilds:
            try:
                stats[str(guild.shard_id)]["guilds"] += 1
                stats[str(guild.shard_id)]["users"] += guild.member_count
            except:
                pass

        await self.bot.db.table("shards").insert({
            "id": "stats",
            "shards": stats
        }, conflict="update").run(self.bot.db.con)

    async def update_loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                await self.update_database()
            except:
                traceback.print_exc()
            await asyncio.sleep(60)

    @cmd.Cog.listener()
    async def on_shard_ready(self, shard_id):
        if not self.bot.is_primary_shard():
            await pubsub.publish("events", event="on_shard_ready", shard_id=shard_id)

        else:
            await self.bot.get_channel(self.bot.config.update_channel).send(**self.bot.em(f"Shard **{shard_id}** ready"))

    async def subscribe_to_events(self):
        async def distribute_events(event, **kwargs):
            if getattr(self, event, None) is not None:
                await getattr(self, event)(**kwargs)

        await self.bot.wait_until_ready()
        if self.bot.is_primary_shard():
            await pubsub.subscribe("events", distribute_events)


def setup(bot):
    bot.add_cog(Sharding(bot))
