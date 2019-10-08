from aiohttp import ClientSession
from discord.ext import commands as cmd
from motor.motor_asyncio import AsyncIOMotorClient
import aioredis
import json
import uuid
import asyncio
import traceback

from utils import formatter, logger, helpers
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

    async def on_ready(self):
        self.log.info(f"Fetched {sum([g.member_count for g in self.guilds])} members on {len(self.guilds)} guilds")

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
        return [{"id": shard.pop("_id"), **shard} for shard in
                await self.db.shards.find().to_list(self.shard_count or 1)]

    async def get_guild_count(self):
        shards = await self.get_shards()
        return sum([shard["guilds"] for shard in shards])

    async def get_user_count(self):
        shards = await self.get_shards()
        return sum([shard["users"] for shard in shards])

    async def _shards_reader(self):
        eval_channel, = await self.redis.subscribe("shards")
        async for msg in eval_channel.iter(decoder=json.loads):
            try:
                _type, author, data = msg["t"], msg["a"], msg["d"]
                if _type == "b":
                    self.dispatch("broadcast", author, data)

                elif _type == "q":
                    result = eval(data["e"])
                    await self.redis.publish_json("shards", {
                        "t": "r",
                        "a": self.shard_ids,
                        "d": {"n": data["n"], "r": result}
                    })

                elif _type == "r":
                    self.dispatch("shard_response", author, data)

            except Exception:
                traceback.print_exc()

    async def broadcast(self, data):
        return await self.redis.publish_json("shards", {
            "t": "b",
            "a": self.shard_ids,
            "d": data
        })

    async def query(self, expression, timeout=0.5):
        nonce = str(uuid.uuid4())
        await self.redis.publish_json("shards", {
            "t": "q",
            "a": self.shard_ids,
            "d": {"n": nonce, "e": expression}
        })

        responses = []
        try:
            async for author, data in helpers.IterWaitFor(
                    self,
                    event="shard_response",
                    check=lambda a, d: d["n"] == nonce,
                    timeout=timeout
            ):
                responses.append((author, data["r"]))

        except asyncio.TimeoutError:
            pass

        return responses

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
        self.loop.create_task(self._shards_reader())

        return await super().start(*args, **kwargs)

    def run(self):
        return super().run(self.config.token)

    async def close(self):
        await super().close()
        await self.session.close()
