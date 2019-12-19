from aiohttp import ClientSession
from discord.ext import commands as cmd
import discord
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
import asyncio
import logging

from utils import formatter, helpers
from utils.extended import Context

log = logging.getLogger(__name__)


class Xenon(cmd.AutoShardedBot):
    session = None
    db = None

    def __init__(self, *args, **kwargs):
        super().__init__(
            command_prefix=self._prefix_callable,
            shard_count=self.config.shard_count,
            fetch_offline_members=False,
            guild_subscriptions=False,
            shard_ids=[
                i for i in range(
                    self.config.pod_id * self.config.shards_per_pod,
                    (self.config.pod_id + 1) * self.config.shards_per_pod
                )
            ],
            owner_id=self.config.owner_id,
            disabled_events=[
                "VOICE_STATE_UPDATE",
                "PRESENCE_UPDATE",
                "TYPING_START",
                "GUILD_EMOJIS_UPDATE"
            ],
            *args, **kwargs
        )

        log.info("Running shards: " + ", ".join([str(shard_id) for shard_id in self.shard_ids]))

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

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_commands(message)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)
        if ctx.command and self.config.private_bot and self.config.owner_id != message.author.id:
            await ctx.send(**ctx.em(
                f"**Private mode is enabled**. This bot can only be used by {ctx.author.mention}.",
                type="error"
            ))
            return

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
    def config(self):
        return __import__("config")

    @property
    def em(self):
        return formatter.embed_message

    def run(self):
        return super().run(self.config.token)

    async def close(self):
        await super().close()
        await self.session.close()
