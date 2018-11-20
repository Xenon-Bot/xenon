from discord.ext import commands as cmd


def bot_has_managed_top_role():
    async def predicate(ctx):
        if ctx.guild.roles[-1].managed and ctx.guild.roles[-1] in ctx.guild.me.roles:
            return True

        else:
            raise cmd.CommandError(
                f"The role called **{ctx.bot.user.name}** needs to be **at the top** of the role hierarchy")

    return cmd.check(predicate)


def check_role_on_support_guild(role_name):
    async def predicate(ctx):
        support_guild = ctx.bot.get_guild(ctx.config.support_guild)
        if support_guild is None:
            ctx.log.warning("Support Guild is unavailable")
            raise cmd.CommandError(
                "The support guild is currently unavailable. Please try again later."
            )

        member = support_guild.get_member(ctx.author.id)
        if member is None:
            raise cmd.CommandError("You need to be on the support guild to use this command.")

        roles = filter(lambda r: r.name == role_name, member.roles)
        if len(list(roles)) == 0:
            raise cmd.CommandError(
                f"You are **missing** the `{role_name}` **role** on the support guild."
            )

        return True

    return predicate


def has_role_on_support_guild(role_name):
    pred = check_role_on_support_guild(role_name)
    return cmd.check(pred)


def is_pro():
    async def predicate(ctx):
        try:
            await check_role_on_support_guild("Xenon Pro")(ctx)
        except cmd.CommandError:
            raise cmd.CommandError(
                f"This command is only for **Xenon Pro** users. Use `{ctx.config.prefix}pro` for more information."
            )

        return True

    return cmd.check(predicate)
