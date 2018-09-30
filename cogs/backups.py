from discord.ext.commands import *
from discord import *
from aiohttp import web
import random

from cogs.utils.backup_handler import Backup


class BackupConv(Converter):
    async def convert(self, ctx, argument):
        backup =  await ctx.bot.database.save_backup(argument.lower())
        if backup is None:
            raise BadArgument("Cant find a backup with that id.")

        return backup


class WebServer:
    routes = web.RouteTableDef()
    def __init__(self):
        self.app = web.Application()

    async def authorization(self, request):
        return web.Response(text="Authorization")

    async def setup(self):
        self.app.add_routes([web.get('/', self.authorization)])

        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 4321)
        await site.start()


class Backups:
    def __init__(self, bot):
        self.bot = bot
        self.webserver = WebServer()

    async def on_ready(self):
        await self.webserver.setup()

    @group(invoke_without_command=True, aliases=["bu"])
    async def backup(self, ctx):
        """Create or load personal server backups"""
        await ctx.invoke(self.bot.get_command("help"), "backup")

    @backup.command(aliases=["c"])
    @guild_only()
    @has_permissions(administrator=True)
    @bot_has_permissions(administrator=True)
    @cooldown(1, 1 * 60, BucketType.guild)
    async def create(self, ctx):
        "Create a backup of your server"
        status_message = await ctx.send("Creating backup, thais could take a while.")

        handler = await Backup.from_guild(self.bot, ctx.guild, ctx.author)
        print("Finished")
        await handler.load()

        try:
            await ctx.author.send()
        except Exception as e:
            await status_message.edit(content="I was **unable to send you the backup-id**. Please enable private messages on this server!")
            return

        await status_message.edit(content="Successfully **created backup**. Please **check your dm's** to see the backup-id.")

    @backup.command(aliases=["l"])
    @guild_only()
    @has_permissions(administrator=True)
    @bot_has_permissions(administrator=True)
    @cooldown(1, 5 * 60, BucketType.guild)
    async def load(self, ctx, backup: BackupConv):
        if str(ctx.author.id) != str(backup["creator"]):
            pass


def setup(bot):
    bot.add_cog(Backups(bot))