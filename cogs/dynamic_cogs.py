from discord.ext import commands

from cogs.utils import checks, formatter


em = formatter.embed_message
fake_token = "mfa.VkO_2G4Qv3T--YOU--lWetW_tjND--TRIED--QFTm6YGtzq9PH--4U--tG0"


class Admin:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def __local_check(self, ctx):
        return checks.is_bot_admin(ctx)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        await ctx.send("Restarting ...")
        exit()

    @commands.group(invoke_without_command=True, aliases=["ext"], hidden=True)
    async def extension(self, ctx):
        """load/unload/reload extensions dynamically"""
        await ctx.invoke(self.bot.get_command("help"), "extension")

    @extension.command(aliases=["rl"])
    async def reload(self, ctx, extension):
        """
        Reload an extension

        **extension**: The extension to reload
        """
        if extension.lower() == "all":
            for extension in self.bot.initial_extensions:
                self.bot.unload_extension(extension)
                self.bot.load_extension(extension)

            await ctx.send(**em("Successfully **reloaded all extensions**!", type="success"))
            return

        self.bot.unload_extension("cogs." + extension.lower())
        self.bot.load_extension("cogs." + extension.lower())

        await ctx.send(**em(f"Successfully **reloaded** the extension **{extension}**!", type="success"))

    @extension.command(aliases=["ul"])
    async def unload(self, ctx, extension):
        """
        Unload an extension

        **extension**: The extension to unload
        """
        self.bot.unload_extension("cogs." + extension.lower())

        await ctx.send(**em(f"Successfully **unloaded** the extension **{extension}**!", type="success"))

    @extension.command(aliases=["l"])
    async def load(self, ctx, extension):
        """
        Load an extension

        **extension**: The extension to load
        """
        self.bot.load_extension("cogs." + extension.lower())

        await ctx.send(**em(f"Successfully **loaded** the extension **{extension}**!", type="success"))


def setup(bot):
    bot.add_cog(Admin(bot))