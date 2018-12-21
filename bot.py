from aiohttp import ClientSession
from discord.ext import commands as cmd

from utils import formatter, logger, database
from utils.extended import Context


class Xenon(cmd.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix=self._prefix_callable,
                         shard_count=kwargs.get("shard_count") or self.config.shard_count,
                         shard_ids=kwargs.get("shard_ids") or self.config.shard_ids)

        self.session = ClientSession(loop=self.loop)
        for ext in self.config.extensions:
            self.load_extension(ext)

        self.log.info(f"Loaded {len(self.cogs)} cogs")

    async def on_shard_ready(self, shard_id):
        self.log.info(f"Shard {shard_id} ready")

    async def on_ready(self):
        self.log.info(
            f"Fetched {sum([g.member_count for g in self.guilds])} members on {len(self.guilds)} guilds")

    async def on_resumed(self):
        self.log.debug(f"Bot resumed")

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_commands(message)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    def _prefix_callable(self, bot, msg):
        valid = [f"<@{self.user.id}> ",
                 f"<@!{self.user.id}> ",
                 f"<@{self.user.id}>",
                 f"<@!{self.user.id}>",
                 self.config.prefix]

        return valid

    def is_primary_shard(self):
        return self.get_guild(self.config.support_guild) is not None

    def is_splitted(self):
        return (self.shard_count or 1) != len(self.shard_ids or [0])

    async def get_shard_stats(self):
        if self.is_splitted():
            stats = await self.db.table("shards").get("stats").run(self.db.con)
            return stats["shards"]

        else:
            latencies = self.latencies
            stats = {str(id): {"latency": latency, "guilds": 0, "users": 0}
                     for id, latency in latencies}
            for guild in self.guilds:
                try:
                    stats[str(guild.shard_id)]["guilds"] += 1
                    stats[str(guild.shard_id)]["users"] += guild.member_count
                except:
                    pass

            return stats

    async def get_guild_count(self):
        stats = await self.get_shard_stats()
        return sum([values["guilds"] for i, values in stats.items()])

    async def get_user_count(self):
        stats = await self.get_shard_stats()
        return sum([values["users"] for i, values in stats.items()])

    @property
    def em(self):
        return formatter.embed_message

    @property
    def log(self):
        return logger.logger

    @property
    def config(self):
        return __import__("config")

    @property
    def db(self):
        return database.rdb

    def run(self):
        super().run(self.config.token)

    async def close(self):
        await super().close()
        await self.session.close()
