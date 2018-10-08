import asyncio

from discord.ext import commands

import statics
from cogs.utils import checks, backups, formatter, file_system

em = formatter.embed_message


class Templates:
    def __init__(self, bot):
        self.bot = bot
        self.handler = backups.BackupHandler(self.bot)

    @commands.command()
    async def templates(self, ctx):
        """List all templates"""
        await ctx.invoke(self.bot.get_command("template list"))

    @commands.group(invoke_without_command=True, aliases=["temp", "tp"])
    async def template(self, ctx):
        """Main template command"""
        await ctx.invoke(self.bot.get_command("help"), "template")

    @template.command(aliases=["c"])
    @commands.cooldown(1, 15 * 60, commands.BucketType.user)
    async def create(self, ctx, backup_id):
        """
        Create a template

        **backup_id**: the id of the backup you want to convert to a template
        """
        data = file_system.get_json_file(f"backups/{backup_id}")
        if data is None:
            ctx.command.reset_cooldown(ctx)
            raise commands.BadArgument(f"Sorry, I was **unable to find** this **backup**.")

        if int(data["creator"]) != ctx.author.id:
            raise commands.BadArgument("You need to be **the creator** of this backup.")

        await ctx.send(
            **em(f"Please give the **template** a **name** that fits the best. (min. 5 characters)", type="wait_for"))
        try:
            name_msg = await self.bot.wait_for("message",
                                               check=lambda
                                                   m: m.channel == ctx.channel and m.author.id == ctx.author.id and len(
                                                   m.content) >= 5,
                                               timeout=30)
            name = name_msg.content.lower().replace(" ", "")
        except asyncio.TimeoutError:
            ctx.command.reset_cooldown(ctx)
            raise checks.InputTimeout

        if file_system.get_json_file(f"templates/{name}") is not None:
            raise commands.BadArgument("There is **already a template** with that name!")

        if name.lower().startswith(statics.prefix):
            raise commands.BadArgument(
                "Looks like **you did not understand** how to use this command. Please read again. [Support](https://discord.club/discord)")

        await ctx.send(
            **em(f"Please give the **template** a **description** that describes it the best. (min. 10 characters)",
                 type="wait_for"))
        try:
            description_msg = await self.bot.wait_for("message",
                                                      check=lambda
                                                          m: m.channel == ctx.channel and m.author.id == ctx.author.id and len(
                                                          m.content) >= 10,
                                                      timeout=120)
            description = description_msg.content
        except asyncio.TimeoutError:
            ctx.command.reset_cooldown(ctx)
            raise checks.InputTimeout

        data["description"] = description
        data["name"] = name
        data["members"] = []

        file_system.save_json_file(f"templates/{name}", data)

        list_channel = self.bot.get_channel(464837510632046593)

        await list_channel.send(embed=self.handler.get_backup_info(data))

        await ctx.send(**em(
            f"Successfully **created template**! You can find a list of templates on the [support discord]({statics.support_invite})!",
            type="success"))

    @template.command(aliases=["l"])
    @commands.guild_only()
    @commands.check(checks.has_top_role)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(administrator=True)
    @commands.cooldown(1, 5 * 60, commands.BucketType.guild)
    async def load(self, ctx, template_name, *options_input):
        """
        Load a template

        **template_name**: the name of the template
        **options**: info (on), settings (on), roles (on), channels (on), bans (on), delete (on)
        <option> turn an option on; !<option> turn an option off
        """
        data = file_system.get_json_file(f"templates/{template_name.lower()}")
        if data is None:
            ctx.command.reset_cooldown(ctx)
            raise commands.BadArgument(f"Sorry, I was **unable to find** this **template**.")

        await self.handler.load_command(ctx, data, options_input, 9999)

    @template.command()
    async def list(self, ctx):
        """List all templates"""
        await ctx.send(**em(f"You can find a list of templates on the [support discord]({statics.support_invite})!"))

    @template.command(aliases=["i"])
    async def info(self, ctx, template_name):
        """
        Get information about a template

        **template_name**: the name of the template
        """
        data = file_system.get_json_file(f"templates/{template_name.lower()}")
        if data is None:
            raise commands.BadArgument(f"Sorry, I was **unable to find** this **backup**.")

        await ctx.send(embed=self.handler.get_backup_info(data))

    @template.command(aliases=["f"])
    @commands.check(checks.is_bot_admin)
    async def feature(self, ctx, template_name):
        """
        Add a template to the featured list

        **template_name**: The template to add to the list
        """
        data = file_system.get_json_file(f"templates/{template_name.lower()}")
        if data is None:
            raise commands.BadArgument(f"Sorry, I was **unable to find** this **template**.")

        channel = self.bot.get_channel(464837529267601408)
        await channel.send(embed=self.handler.get_backup_info(data))

        await ctx.send(embed=self.bot.embeds.success(f"Successfully **featured the template** `{template_name}`!"))


def setup(bot):
    bot.add_cog(Templates(bot))
