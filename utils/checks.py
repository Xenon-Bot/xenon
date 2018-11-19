from discord.ext import commands as cmd


def bot_has_managed_top_role():
    async def predicate(ctx):
        if ctx.guild.roles[-1].managed and ctx.guild.roles[-1] in ctx.guild.me.roles:
            return True

        else:
            raise cmd.CommandError(
                f"The role called **{ctx.bot.user.name}** needs to be **at the top** of the role hierarchy")

    return cmd.check(predicate)
