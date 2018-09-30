from discord.ext import commands
import discord


def has_support_role(id: int):
    async def predicate(ctx):
        role = discord.utils.get(ctx.get_guild(ctx.bot.support_guild).roles, id=id)
        if role in ctx.author.roles:
            return True

        raise commands.BadArgument("You are **missing a required role** on the support server to use this command")

    return commands.check(predicate)