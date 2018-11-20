from discord.ext import commands as cmd
from discord_backups import copy_guild

from utils import checks
from cogs import backups


class Pro:
    def __init__(self, bot):
        self.bot = bot

    @cmd.command()
    async def pro(self, ctx):
        """Shows information about Xenon Pro"""
        await ctx.send(**ctx.em(
            "**Xenon Pro** is the **paid version** of xenon. It includes some **exclusive features**.\n"
            "You can buy it [here](https://donatebot.io/checkout/410488579140354049).\n\n"
            "All main features of the bot will remain completely free!",
            type="info"
        ))
        await ctx.invoke(self.bot.get_command("help"), "Pro")

    @cmd.command(aliases=["cp"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.is_pro()
    @checks.bot_has_managed_top_role()
    @cmd.cooldown(1, 5 * 60, cmd.BucketType.guild)
    async def copy(self, ctx, guild_id: int, chatlog: int = backups.max_chatlog):
        """
        Copy all channels and roles from one guild to another (this)


        guild_id ::     The id of the guild

        chatlog  ::     The count of messages to load per channel (max. 20) (default 20)
        """
        chatlog = chatlog if chatlog < backups.max_chatlog and chatlog >= 0 else backups.max_chatlog
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            raise cmd.CommandError(f"There is **no guild with the id** `{guild_id}`.")

        if guild.get_member(ctx.author.id) is None or not guild.get_member(ctx.author.id).guild_permissions.administrator:
            raise cmd.MissingPermissions([f"administrator` on the guild `{guild.name}"])

        warning = await ctx.send(**ctx.em("Are you sure you want to copy that guild? **All channels and roles will get replaced!**", type="warning"))
        await warning.add_reaction("✅")
        await warning.add_reaction("❌")
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == warning.id and u.id == ctx.author.id,
                timeout=60)
        except TimeoutError:
            raise cmd.CommandError(
                "Please make sure to **click the ✅ reaction** in order to load the backup.")
            await warning.delete()

        if str(reaction.emoji) != "✅":
            ctx.command.reset_cooldown(ctx)
            await warning.delete()
            return

        await copy_guild(guild, ctx.guild, chatlog)
        await ctx.guild.text_channels[0].send(**ctx.em("Successfully copied guild.", type="success"))


def setup(bot):
    bot.add_cog(Pro(bot))
