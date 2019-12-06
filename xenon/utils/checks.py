from discord.ext import commands as cmd
import asyncio
import logging
import discord

log = logging.getLogger(__name__)


def bot_has_managed_top_role():
    async def predicate(ctx):
        if ctx.guild.roles[-1].managed and ctx.guild.roles[-1] in ctx.guild.me.roles:
            return True

        else:
            sended = await ctx.send(**ctx.em(
                f"The role called **{ctx.bot.user.name}** is currently not at the top of the role hierarchy.\n\n"
                "Continuing could cause bugs. Do you want to continue?", type="warning"))

            await sended.add_reaction("✅")
            await sended.add_reaction("❌")

            try:
                reaction, user = await ctx.bot.wait_for(
                    "reaction_add",
                    check=lambda r, u: r.message.id == sended.id and u.id == ctx.author.id,
                    timeout=60)
            except asyncio.TimeoutError:
                try:
                    ctx.command.reset_cooldown(ctx)
                except:
                    pass

                await sended.delete()
                raise cmd.CommandError(
                    "Please make sure to **click the ✅ reaction** in order to continue.")

            if str(reaction.emoji) != "✅":
                try:
                    ctx.command.reset_cooldown(ctx)
                except:
                    pass

                await sended.delete()
                raise cmd.CommandError(
                    "Please make sure to **click the ✅ reaction** in order to continue.")

            await sended.delete()
            return True

    return cmd.check(predicate)


def check_role_on_support_guild(role_name):
    async def predicate(ctx):
        support_guild = ctx.bot.get_guild(ctx.config.support_guild)
        if support_guild is None:
            log.warning("Support Guild is unavailable")
            raise cmd.CommandError(
                "The support guild is currently unavailable. Please try again later."
            )

        try:
            member = await support_guild.fetch_member(ctx.author.id)
        except discord.NotFound:
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
