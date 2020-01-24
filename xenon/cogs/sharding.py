from discord.ext import commands as cmd
import traceback
import asyncio
from datetime import datetime


class Sharding(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.update_loop())

    async def update_database(self):
        latencies = self.bot.latencies
        if len(self.bot.shard_ids) == 0:
            return

        cluster_id = self.bot.shard_ids[0] % self.bot.config.per_cluster
        shards = {id: {
            "latency": latency,
            "guilds": 0,
            "users": 0,
            "seen": datetime.utcnow(),
            "cluster": cluster_id
        } for id, latency in latencies}
        for guild in self.bot.guilds:
            try:
                shards[guild.shard_id]["guilds"] += 1
                shards[guild.shard_id]["users"] += guild.member_count
            except:
                pass

        for id, shard in shards.items():
            await self.bot.db.shards.update_one({"_id": id}, {"$set": shard}, upsert=True)

    async def update_loop(self):
        while not self.bot.is_closed():
            try:
                await self.update_database()
            except Exception:
                traceback.print_exc()

            await asyncio.sleep(60)


def setup(bot):
    bot.add_cog(Sharding(bot))
