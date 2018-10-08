import sys
import traceback

from discord.ext import commands

from cogs.utils import checks, formatter

em = formatter.embed_message


class CommandError():
    def __init__(self, bot):
        self.bot = bot

    async def on_command_error(self, ctx, error):
        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandOnCooldown):
            def format_time(seconds):
                seconds = int(round(seconds, 0))
                if seconds >= 60:
                    min = seconds // 60
                    rest = seconds % 60
                    if min < 10:
                        min = int("0" + str(min))

                    if rest < 10:
                        rest = int("0" + str(rest))

                    return str(min) + ((':' + str(rest)) if rest > 0 else "") + " minute(s)"
                else:
                    return str(seconds) + " seconds"

            await ctx.send(**em(
                f"This command is currently **on cooldown** for {format_time(error.cooldown.per)}.Please **try again in {format_time(error.retry_after)}**.",
                type="error"))
            return

        try:
            ctx.command.reset_cooldown(ctx)
        except:
            pass

        if isinstance(error, commands.CommandNotFound):
            pass

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(**em(f"Please **define** the required **argument** `{error.param.name}`.", type="error"))
        elif isinstance(error, checks.Blacklisted):
            await ctx.send(**em(f"You are not allowed to use this bot anymore. [Support](https://discord.club/discord)", type="error"))
        elif isinstance(error, checks.NotGuildOwner):
            await ctx.send(**em("You need to be the **owner of this guild** to perform this command", type="error"))
        elif isinstance(error, checks.HasNotTopRole):
            await ctx.send(**em(
                "The role called `Xenon` needs to be **on the top of the role hierarchy**.", type="error"))
        elif isinstance(error, checks.InputTimeout):
            await ctx.send(**em("**Canceled** input, because you did **not respond** in the right way.", type="error"))

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(
                **em(f"You are **missing** the following **permissions**: `{str(*error.missing_perms).upper()}`",
                     type="error"))
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(**em(f"I'm **missing** the following **permissions**: `{str(*error.missing_perms).upper()}`",
                                type="error"))
        elif isinstance(error, commands.NotOwner):
            await ctx.send(**em(f"You need to be the **owner of this bot** to perform this command!", type="error"))
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(**em(f"This command **can't be used** in **Private Messages**!", type="error"))
        elif isinstance(error, commands.BadUnionArgument):
            await ctx.send(**em(f"I was not able to find a **{'** / **'.join([str(conv.__name__) for conv in error.converters])}** for the argument `{error.param.name}`", type="error"))
        elif isinstance(error, commands.BadArgument):
            await ctx.send(**em(str(error), type="error"))

        else:
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            error_message = traceback.format_exception(type(error), error, error.__traceback__)
            try:
                await ctx.send(**em(error_message, type="unex_error"))
            except:
                print("Unable to report this error!")


def setup(bot):
    bot.add_cog(CommandError(bot))
