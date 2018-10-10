from discord.ext import commands

import statics
from cogs.utils import file_system


class InputTimeout(commands.CommandError):
    pass


class NotGuildOwner(commands.CheckFailure):
    pass

def is_guild_owner(ctx):
    if ctx.guild.owner.id != ctx.author.id:
        raise NotGuildOwner
    return True


class HasNotTopRole(commands.CheckFailure):
    pass

def has_top_role(ctx):
    if ctx.guild.roles[-1].id not in [role.id for role in ctx.guild.me.roles]:
        raise HasNotTopRole
    return True


class NotBotAdmin(commands.MissingPermissions):
    def __init__(self):
        self.missing_perms = ["BotAdmin"]

def is_bot_admin(ctx):
    guild = ctx.bot.get_guild(statics.support_guild)
    if guild is None:
        raise NotBotAdmin

    member = guild.get_member(ctx.author.id)
    if member is None:
        raise  NotBotAdmin

    if not statics.admin_role in [role.id for role in member.roles]:
        raise NotBotAdmin

    return True

class NotPro(commands.MissingPermissions):
    def __init__(self):
        self.missing_perms = ["ProUser"]

def is_pro(ctx):
    guild = ctx.bot.get_guild(statics.support_guild)
    if guild is None:
        raise NotPro

    member = guild.get_member(ctx.author.id)
    if member is None:
        raise NotPro

    if not statics.pro_role in [role.id for role in member.roles]:
        raise NotPro

    return True


class Blacklisted(commands.CommandError):
    pass