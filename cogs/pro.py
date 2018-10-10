from discord.ext import commands

from cogs.utils import formatter, backups, checks


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
    async def copy(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            raise commands.BadArgument(f"I was **unable to find that guild**.")

        if not guild.me.guild_permissions.administrator:
            raise commands.BadArgument(f"I need to have **administrator permissions** on the guild you want to copy.")

        if guild.get_member(ctx.author.id) is None or not guild.get_member(ctx.author.id).guild_permissions.administrator:
            raise commands.BadArgument(f"You need to be **administrator** on the guild you want to copy.")

        await backups.copy_guild(guild, ctx.guild)


def setup(bot):
    bot.add_cog(Pro(bot))