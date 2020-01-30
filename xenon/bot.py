from aiohttp import ClientSession
from discord.ext import commands as cmd
import aioredis
import json
import uuid
import asyncio
import traceback
import inspect
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import discord
from datetime import datetime
import time
import threading
import io

from utils import formatter, helpers
from utils.context import Context
from utils.lock import RedisLock

log = logging.getLogger(__name__)
last_commands = []


def block_check(loop):
    while True:
        try:
            time.sleep(1)
            future = asyncio.run_coroutine_threadsafe(asyncio.sleep(0), loop)
            blocked_for = 0
            while True:
                try:
                    future.result(1)
                    break
                except asyncio.TimeoutError:
                    blocked_for += 1
                    task = asyncio.current_task(loop)
                    buffer = io.StringIO()
                    task.print_stack(file=buffer)
                    buffer.seek(0)
                    log.warning("Event loop blocked for longer than %d seconds (%s)\n%s\n%s" % (
                        blocked_for,
                        str(task),
                        str(last_commands),
                        buffer.read()
                    ))
        except Exception:
            pass


class Xenon(cmd.AutoShardedBot):
    session = None
    db = None
    redis = None

    def __init__(self, *args, **kwargs):
        super().__init__(
            command_prefix=self._prefix_callable,
            shard_count=self.config.shard_count,
            fetch_offline_members=False,
            guild_subscriptions=False,
            shard_ids=[],
            owner_id=self.config.owner_id,
            max_messages=10**4,
            disabled_events=[
                "VOICE_STATE_UPDATE",
                "PRESENCE_UPDATE",
                "TYPING_START",
                "GUILD_EMOJIS_UPDATE"
            ],
            *args, **kwargs
        )

        self.session = ClientSession(loop=self.loop)
        db_connection = AsyncIOMotorClient(
            host=self.config.db_host,
            username=self.config.db_user,
            password=self.config.db_password
        )
        self.db = getattr(db_connection, self.config.identifier)
        for ext in self.config.extensions:
            self.load_extension("cogs." + ext)

        log.info(f"Loaded {len(self.cogs)} cogs")

    async def on_ready(self):
        log.info(f"Cached {len(self.users)} users from {len(self.guilds)} guilds")

    async def on_command(self, ctx):
        last_commands.append(ctx.message.content)
        if len(last_commands) > 10:
            last_commands.pop(0)

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
        channel, = await self.redis.subscribe("shards")
        async for msg in channel.iter(decoder=json.loads):
            try:
                _type, author, data = msg["t"], msg["a"], msg["d"]
                if _type == "b":
                    self.dispatch("broadcast", author, data)

                elif _type == "q":
                    to_eval = data["e"].replace("await ", "")
                    try:
                        result = eval(to_eval)
                        if inspect.isawaitable(result):
                            result = await result

                    except Exception as e:
                        result = type(e).__name__ + ": " + str(e)

                    await self.redis.publish_json("shards", {
                        "t": "r",
                        "a": self.cluster_id,
                        "d": {"n": data["n"], "r": result}
                    })

                elif _type == "r":
                    self.dispatch("query_response", author, data)

            except Exception:
                traceback.print_exc()

        self.loop.create_task(self._shards_reader())  # Restart

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
                    event="query_response",
                    check=lambda a, d: d["n"] == nonce,
                    timeout=timeout
            ):
                responses.append((author, data["r"]))

        except asyncio.TimeoutError:
            pass

        return responses

    async def _keep_shard_lock(self, lock):
        last_renew = datetime.utcnow()
        while not self.is_closed():
            await asyncio.sleep(2)
            difference_last = datetime.utcnow() - last_renew
            before_renew = datetime.utcnow()
            if not await lock.is_owner():
                difference_renew = datetime.utcnow() - before_renew
                log.info("Lost the SHARD lock (lost ownership, %ds, %ds). Restarting ..." %
                         (difference_last.seconds, difference_renew.seconds))
                await self.close()
                self.loop.stop()
                exit(0)

            if not await lock.renew():
                difference_renew = datetime.utcnow() - before_renew
                log.info("Lost the SHARD lock (unable to renew, %ds %ds). Restarting ..." %
                         (difference_last.seconds, difference_renew.seconds))
                await self.close()
                self.loop.stop()
                exit(0)

            last_renew = datetime.utcnow()

    async def launch_shards(self):
        log.info("Waiting to acquire a SHARD lock.")
        while not self.is_closed():
            tried = []
            for i in range(0, self.config.shard_count, self.config.per_cluster):
                lock = RedisLock(
                    self.redis,
                    key="%s_%d" % (self.config.identifier, i),
                    timeout=10,
                    wait_timeout=0
                )
                if await lock.acquire():
                    log.info("Acquired the SHARD lock %d" % i)
                    self.shard_ids = list(range(i, i + self.config.per_cluster))
                    self.loop.create_task(self._keep_shard_lock(lock))
                    log.info("Running shards: " + ", ".join([str(shard_id) for shard_id in self.shard_ids]))
                    return await super().launch_shards()

                else:
                    tried.append(i)

                await asyncio.sleep(0)  # Suspend

            log.info("Tried SHARD Locks (%s) with no success." % ", ".join([str(j) for j in tried]))

            await asyncio.sleep(10)

    async def launch_shard(self, gateway, shard_id):
        log.info("Waiting to acquire the IDENTIFY lock.")
        async with RedisLock(
                self.redis,
                key="%s_identify" % self.config.identifier,
                timeout=200,  # More than the connect timeout
                wait_timeout=None
        ):
            log.info("Shard ID %s has acquired the IDENTIFY lock." % shard_id)
            return await super().launch_shard(gateway, shard_id)

    @property
    def invite(self):
        invite = self.config.invite_url
        if not invite:
            invite = discord.utils.oauth_url(
                client_id=self.user.id,
                permissions=discord.Permissions(8)
            )

        return invite

    @property
    def cluster_id(self):
        return self.shard_ids[0]

    @property
    def config(self):
        return __import__("config")

    @property
    def em(self):
        return formatter.embed_message

    async def start(self, *args, **kwargs):
        t = threading.Thread(target=block_check, args=(self.loop,))
        t.setDaemon(True)
        t.start()
        self.redis = aioredis.Redis(await aioredis.create_pool("redis://" + self.config.redis_host))
        # self.loop.create_task(self._shards_reader())

        return await super().start(*args, **kwargs)

    def run(self):
        return super().run(self.config.token)

    async def close(self):
        await super().close()
        await self.session.close()
