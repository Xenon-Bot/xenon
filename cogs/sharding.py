import traceback
import asyncio


class Sharding:
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.update_loop())

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
                if self.bot.is_splitted():
                    await self.update_database()

            except:
                traceback.print_exc()

            await asyncio.sleep(60)


def setup(bot):
    bot.add_cog(Sharding(bot))
