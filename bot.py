from discord.ext import commands
import traceback

from cogs.utils import database


class Xenon(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__dict__.update(kwargs)

        self.db = database.Database()

        cogs = [
            "cogs.backups",
            "cogs.templates"
        ]
        for cog in cogs:
            try:
                self.load_extension(cog)
            except Exception as e:
                traceback.print_exc()

    async def on_ready(self):
        print(f"Successfully connected to {str(self.user)} on {len(self.guilds)} guilds with {self.shard_count} shards.")

    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_commands(msg)