from aiohttp import ClientSession
from discord.ext import commands as cmd
from motor.motor_asyncio import AsyncIOMotorClient
import aioredis

from utils import formatter, logger
from utils.extended import Context


class Xenon(cmd.AutoShardedBot):
    session = None
    db = None
    redis = None

    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix=self._prefix_callable,
                         shard_count=self.config.shard_count,
                         fetch_offline_members=False,
                         shard_ids=[
                             i for i in range(
                                 self.config.pod_id * self.config.shards_per_pod,
                                 (self.config.pod_id + 1) * self.config.shards_per_pod
                             )
                         ],
                         owner_id=self.config.owner_id,
                         *args, **kwargs)

        self.log.info("Running shards: " + ", ".join([str(shard_id) for shard_id in self.shard_ids]))

        self.session = ClientSession(loop=self.loop)
        self.db = AsyncIOMotorClient(
            host=self.config.db_host,
            username=self.config.db_user,
            password=self.config.db_password
        ).xenon
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

    async def get_shards(self):
        return [{"id": shard.pop("_id"), **shard} for shard in await self.db.shards.find().to_list(self.shard_count or 1)]

    async def get_guild_count(self):
        shards = await self.get_shards()
        return sum([shard["guilds"] for shard in shards])

    async def get_user_count(self):
        shards = await self.get_shards()
        return sum([shard["users"] for shard in shards])

    @property
    def em(self):
        return formatter.embed_message

    @property
    def log(self):
        return logger.logger

    @property
    def config(self):
        return __import__("config")

    async def start(self, *args, **kwargs):
        self.redis = aioredis.Redis(await aioredis.create_pool("redis://" + self.config.redis_host))
        return await super().start(*args, **kwargs)

    def run(self):
        return super().run(self.config.token)

    async def close(self):
        await super().close()
        await self.session.close()
