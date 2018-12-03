from discord.ext import commands as cmd
from discord_backups import BackupInfo, BackupLoader

from utils import checks


class Templates:
    def __init__(self, bot):
        self.bot = bot

    @cmd.group(aliases=["temp"], invoke_without_command=True)
    async def template(self, ctx):
        """Create & load public templates"""
        await ctx.invoke(self.bot.get_command("help"), "template")

    @template.command(aliases=["c"])
    @cmd.cooldown(1, 30, cmd.BucketType.user)
    async def create(self, ctx, backup_id, name, *, description):
        """
        Turn a private backup into a PUBLIC template.


        backup_id   ::      The id of the backup that you want to turn into a template

        name        ::      A name for the template

        description ::      A description for the template
        """
        name = name.lower().replace(" ", "_")
        backup = await ctx.db.table("backups").get(backup_id).run(ctx.db.con)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        already_exists = (await ctx.db.table("templates").get(name).run(ctx.db.con)) is not None
        if already_exists:
            raise cmd.CommandError(
                f"There is **already a template with that name**, please choose another one."
            )

        backup["backup"]["members"] = []

        warning = await ctx.send(**ctx.em("Are you sure you want to turn this backup into a template? **All templates are public!**", type="warning"))
        await warning.add_reaction("✅")
        await warning.add_reaction("❌")
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == warning.id and u.id == ctx.author.id,
                timeout=60
            )
        except TimeoutError:
            raise cmd.CommandError(
                "Please make sure to **click the ✅ reaction** in order to create a template."
            )
            await warning.delete()

        if str(reaction.emoji) != "✅":
            await warning.delete()
            return

        await ctx.db.table("templates").insert({
            "id": name,
            "creator": backup["creator"],
            "loaded": 0,
            "featured": False,
            "original": backup_id,
            "description": description,
            "template": backup["backup"]
        }).run(ctx.db.con)

        template = await ctx.db.table("templates").get(name).run(ctx.db.con)
        embed = self.template_info(ctx, name, template)
        await self.bot.get_channel(516345778327912448).send(embed=embed)

        await ctx.send(**ctx.em("Successfully **created template**.\n"
                                f"You can load the template with `{ctx.prefix}template load {name}`", type="success"))

    @template.command(aliases=["unfeature"])
    @checks.has_role_on_support_guild("Staff")
    async def feature(self, ctx, *, template_name):
        """
        Feature a template


        template_name ::    The name of the template
        """
        feature = True
        if ctx.invoked_with == "unfeature":
            feature = False

        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.table("templates").get(template_name).run(ctx.db.con)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")
        await ctx.db.table("templates").get(template_name).update({"featured": feature}).run(ctx.db.con)

        embed = self.template_info(ctx, template_name, template)
        await self.bot.get_channel(464837529267601408).send(embed=embed)

        await ctx.send(**ctx.em(f"Successfully **{'un' if not feature else ''}featured template**.", type="success"))

    @template.command(aliases=["del", "rm", "remove"])
    @checks.has_role_on_support_guild("Staff")
    async def delete(self, ctx, *, template_name):
        """
        Delete a template created by you


        template_name ::    The name of the template
        """
        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.table("templates").get(template_name).run(ctx.db.con)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")

        await ctx.db.table("templates").get(template_name).delete().run(ctx.db.con)
        await ctx.send(**ctx.em("Successfully **deleted template**.", type="success"))

    @template.command(aliases=["l"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.bot_has_managed_top_role()
    @cmd.cooldown(1, 5 * 60, cmd.BucketType.guild)
    async def load(self, ctx, *, template_name):
        """
        Load a template


        template_name ::    The name of the template
        """
        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.table("templates").get(template_name).run(ctx.db.con)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")

        warning = await ctx.send(**ctx.em("Are you sure you want to load this template? **All channels and roles will get replaced!**", type="warning"))
        await warning.add_reaction("✅")
        await warning.add_reaction("❌")
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == warning.id and u.id == ctx.author.id,
                timeout=60)
        except TimeoutError:
            raise cmd.CommandError(
                "Please make sure to **click the ✅ reaction** in order to load the template."
            )
            await warning.delete()

        if str(reaction.emoji) != "✅":
            ctx.command.reset_cooldown(ctx)
            await warning.delete()
            return

        await ctx.db.table("templates").get(template_name).update({"loaded": ctx.db.row["loaded"] + 1}).run(ctx.db.con)
        handler = BackupLoader(self.bot, self.bot.session, template["template"])
        await handler.load(ctx.guild, ctx.author, 0)

    @template.command(aliases=["i", "inf"])
    @cmd.cooldown(1, 5, cmd.BucketType.user)
    async def info(self, ctx, *, template_name):
        """
        Get information about a template


        template_name ::    The name of the template
        """
        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.table("templates").get(template_name).run(ctx.db.con)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")

        embed = self.template_info(ctx, template_name, template)
        await ctx.send(embed=embed)

    def template_info(self, ctx, name, template):
        handler = BackupInfo(ctx.bot, template["template"])
        embed = ctx.em("")["embed"]
        embed.title = name
        embed.description = template["description"]
        embed.add_field(name="Creator", value=f"<@{template['creator']}>")
        embed.add_field(name="Channels", value=handler.channels(), inline=True)
        embed.add_field(name="Roles", value=handler.roles(), inline=True)

        return embed

    @template.command(aliases=["ls"])
    async def list(self, ctx):
        await ctx.send(**ctx.em(
            "You can find a **list of templates** in <#516345778327912448> and <#464837529267601408> on the [support server](https://discord.club/discord).",
            type="info"
        ))


def setup(bot):
    bot.add_cog(Templates(bot))
