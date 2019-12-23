from discord.ext import commands as cmd
import traceback
import sys
from datetime import timedelta

from utils import formatter


em = formatter.embed_message


basic_formatter = {
    cmd.MissingRequiredArgument: "You forgot to define the argument **{error.param.name}**. "
                                 "Use `{ctx.config.prefix}help {ctx.command.qualified_name}` for more information.",
    cmd.NoPrivateMessage: "This command **can't be used** in **private** messages.",
    cmd.DisabledCommand: "This command is currently **disabled**.",
    cmd.NotOwner: "This command can **only** be used by **the owner** of this bot."
}

ignore = [cmd.CommandNotFound, cmd.TooManyArguments]
catch_all = [cmd.CommandError]


class Errors(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cmd.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, 'original', error)
        catch_all = True

        if not isinstance(error, cmd.CommandOnCooldown):
            try:
                ctx.command.reset_cooldown(ctx)
            except AttributeError:
                pass

        for error_cls in ignore:
            if isinstance(error, error_cls):
                return

        for error_cls, format in basic_formatter.items():
            if isinstance(error, error_cls):
                await ctx.send(**em(format.format(error=error, ctx=ctx), type="error"))
                return

        if isinstance(error, cmd.BotMissingPermissions):
            await ctx.send(**em(f"The bot is **missing** the following **permissions** `{', '.join(error.missing_perms)}`.", type="error"))
            return

        if isinstance(error, cmd.MissingPermissions):
            await ctx.send(**em(f"You are **missing** the following **permissions** `{', '.join(error.missing_perms)}`.", type="error"))
            return

        if isinstance(error, cmd.CommandOnCooldown):
            await ctx.send(**ctx.em(
                f"This command is currently **on cooldown** for `{str(timedelta(seconds=error.cooldown.per)).split('.')[0]}`.\n"
                f"Please **try again in** `{str(timedelta(seconds=error.retry_after)).split('.')[0]}`.",
                type="error")
            )
            return

        if isinstance(error, cmd.BadUnionArgument):
            # cba
            pass

        if isinstance(error, cmd.BadArgument):
            if 'Converting to "' in str(error):
                converters = {
                    "int": "number"
                }
                conv = str(error).split('"')[1]
                parameter = str(error).split('"')[3]
                await ctx.send(**em(
                    f"The value you passed to **{parameter}** is not a valid **{converters.get(conv, conv)}**.",
                    type="error"
                ))
                return

            if '" not found' in str(error):
                conv = str(error).split(" ")[0]
                value = str(error).split('"')[1]
                await ctx.send(**em(
                    f"**No {conv} found** that fits the value `{value}`.",
                    type="error"
                ))
                return

        if catch_all:
            if isinstance(error, cmd.CommandError):
                await ctx.send(**em(str(error), type="error"))

            else:
                traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
                error_message = traceback.format_exception(type(error), error, error.__traceback__)
                try:
                    await ctx.send(**em(error_message[:1900], type="unex_error"))

                except:
                    pass


def setup(bot):
    bot.add_cog(Errors(bot))
