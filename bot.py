from discord.ext import commands
import traceback
import sys
import dbl
import logging

import statics


description = ""

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def prefix(bot, msg):
    return statics.prefix


class Xenon(commands.AutoShardedBot):
    def __init__(self, token):
        super().__init__(command_prefix=prefix, description=description)
        self.dblpy = dbl.Client(self, statics.dbl_token, loop=self.loop)

        self.initial_extensions = (
            "cogs.help",
            "cogs.basics",
            "cogs.backups",
            "cogs.templates",
            "cogs.admin",
            "cogs.dynamic_cogs",
            "cogs.blacklist",

            "cogs.command_error",
            "cogs.web",
            #"cogs.stats"
        )

        for cog in self.initial_extensions:
            try:
                self.load_extension(cog)
            except Exception as e:
                print(f'Failed to load cog {cog}.', file=sys.stderr)
                traceback.print_exc()

        self.run(statics.token)

    async def on_ready(self):
        print(f"Connected to {str(self.user)} on {len(self.guilds)} guild(s) with {self.shard_count} shard(s).")

    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_commands(msg)

bot = Xenon(statics.token)