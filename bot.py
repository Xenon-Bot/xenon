from aiohttp import ClientSession
from discord.ext import commands as cmd

from utils import formatter, logger, database
from utils.extended import Context


class Xenon(cmd.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix=self._prefix_callable,
                         shard_count=self.config.shard_count,
                         shard_ids=self.config.shard_ids)

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
        if message.author.bot:
            return

        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    def _prefix_callable(self, bot, msg):
        valid = [f"<@{self.user.id}> ",
                 f"<@!{self.user.id}> ",
                 f"<@{self.user.id}>",
                 f"<@!{self.user.id}>",
                 self.config.prefix]

        return valid

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
