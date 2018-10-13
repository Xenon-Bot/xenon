from discord.ext import commands
import asyncio
from discord_backups import copy_guild

from cogs.utils import formatter, checks


em = formatter.embed_message


class Pro:
    def __init__(self, bot):
        self.bot = bot
        self.syncs = {}

    @commands.command()
    @commands.guild_only()
    @commands.check(checks.has_top_role)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(administrator=True)
    @commands.check(checks.is_pro)
    @commands.cooldown(1, 5 * 60, commands.BucketType.guild)
    async def copy(self, ctx, guild_id: int, chatlog: int = 20):
        """
        Copy a guild
        Be careful with this, it does not have any confirm warnings yet

        **guild_id** The id of the guild you want to copy
        """
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            raise commands.BadArgument(f"I was **unable to find that guild**.")

        if not guild.me.guild_permissions.administrator:
            raise commands.BadArgument(f"I need to have **administrator permissions** on the guild you want to copy.")

        if guild.get_member(ctx.author.id) is None or not guild.get_member(ctx.author.id).guild_permissions.administrator:
            raise commands.BadArgument(f"You need to be **administrator** on the guild you want to copy.")

        warning = await ctx.send(**em("Are you sure you want to copy  that guild?\n**All channels will get replaced.**", type="warning"))
        await warning.add_reaction("✅")
        await warning.add_reaction("❌")
        try:
            reaction, user = await self.bot.wait_for(
                event="reaction_add",
                timeout=60,
                check=lambda r, u: u.id == ctx.author.id and
                                   r.message.id == warning.id and r.message.channel.id == warning.channel.id and
                                   (str(r.emoji) == "✅" or str(r.emoji) == "❌")
            )
        except asyncio.TimeoutError:
            raise commands.BadArgument("**Canceled copy process.**")

        if str(reaction.emoji) == "✅":
            await copy_guild(guild, ctx.guild, chatlog)

        else:
            raise commands.BadArgument("**Canceled copy process.**")


def setup(bot):
    bot.add_cog(Pro(bot))