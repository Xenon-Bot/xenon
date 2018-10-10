import inspect
import io
import textwrap
import traceback
from contextlib import redirect_stdout
import discord
from discord.ext import commands

import statics
from cogs.utils import checks, file_system, formatter


em = formatter.embed_message


class Blacklist:
    def __init__(self, bot):
        self.bot = bot

        @bot.check
        async def not_blacklisted(ctx):
            blacklist = await file_system.get_json_file("blacklist")
            if blacklist is None:
                return True
            if ctx.author.id not in blacklist:
                return True

            raise checks.Blacklisted

    async def __local_check(self, ctx):
        return checks.is_bot_admin(ctx)


    @commands.group(invoke_without_command=True, hidden=True, aliases=["bl"])
    async def blacklist(self, ctx):
        """Prevent people from using this bot"""
        await ctx.invoke(self.bot.get_command("help"), "blacklist")

    @blacklist.command(aliases=["a"])
    async def add(self, ctx, user: discord.User):
        """
        Add someone to the blacklist

        **user**: The user to add to the blacklist
        """
        blacklist = await file_system.get_json_file("blacklist")
        if blacklist is None:
            blacklist = []

        if user.id in blacklist:
            raise commands.BadArgument("This user is **already blacklisted**!")

        blacklist.append(user.id)
        await file_system.save_json_file("blacklist", blacklist)
        await ctx.send(**em(f"Successfully **added {str(user)}** to the blacklist!", type="success"))

    @blacklist.command(aliases=["delete", "del", "rm"])
    async def remove(self, ctx, user: discord.User):
        """
        Remove someone from the blacklist

        **user**: The user to remove from the blacklist
        """
        blacklist = await file_system.get_json_file("blacklist")
        if blacklist is None:
            blacklist = []

        if user.id not in blacklist:
            raise commands.BadArgument("This user **isn't blacklisted**!")

        blacklist.remove(user.id)
        await file_system.save_json_file("blacklist", blacklist)
        await ctx.send(**em(f"Successfully **removed {str(user)}** from the blacklist!", type="success"))

    @blacklist.command(aliases=["info", "i", "l"])
    async def list(self, ctx):
        """Show the list of blacklisted users"""
        blacklist = await file_system.get_json_file("blacklist")
        if blacklist is None or len(blacklist) == 0:
            await ctx.send(**em("The **blacklist** is currently **empty**!", type="info"))
            return

        users = ""
        for user_id in blacklist:
            users += f"<@{user_id}> "

        embed = discord.Embed(color=statics.embed_color, description=users)
        embed.set_author(name="Blacklist")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Blacklist(bot))