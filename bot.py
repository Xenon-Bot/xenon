import logging
import sys
import traceback

import dbl
import discord
import sentry_sdk
import aiohttp
from discord.ext import commands

import statics

description = ""

sentry_sdk.init(statics.sentry_key)

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def prefix(bot, msg):
    return statics.prefix


class Xenon(commands.AutoShardedBot):
    def __init__(self, token):
        activity = None
        if not statics.test_mode:
            activity = discord.Activity(type=discord.ActivityType.streaming, name="Starting Up ...", url="https://twitch.tv/merlintor")

        super().__init__(
            command_prefix=prefix,
            description=description,
            activity = activity
        )

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.dblpy = dbl.Client(self, statics.dbl_token, loop=self.loop)

        self.initial_extensions = (
            "cogs.help",
            "cogs.basics",
            "cogs.backups",
            "cogs.templates",
            "cogs.admin",
            "cogs.dynamic_cogs",
            "cogs.blacklist",
            "cogs.pro",
            "cogs.rollback",

            "cogs.command_error",
            "cogs.web",
            "cogs.special_events",
            "cogs.stats"
        )

        for cog in self.initial_extensions:
            try:
                self.load_extension(cog)
            except Exception as e:
                print(f'Failed to load cog {cog}.', file=sys.stderr)
                traceback.print_exc()

        self.run(statics.token)

    async def on_shard_ready(self, shard_id):
        print(f"Shard {shard_id} ready")

    async def on_ready(self):
        if not statics.test_mode:
            await self.change_presence(activity=discord.Activity(name=""))

        print(f"Connected to {str(self.user)} with {self.shard_count} shard(s).")
        print(f"Fetched {sum([len(guild.members) for guild in self.guilds])} members in {len(self.guilds)} guilds.")

    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_commands(msg)

    @property
    def shard_info(self):
        shards = {}
        for guild in self.guilds:
            shard = guild.shard_id
            if shards.get(shard) is None:
                shards[shard] = {"guilds": 1, "users": len(guild.members), "latency": None}

            else:
                shards[shard]["guilds"] += 1
                shards[shard]["users"] += len(guild.members)

        for shard, latency in self.latencies:
            shards[shard]["latency"] = latency

        return shards


bot = Xenon(statics.token)
