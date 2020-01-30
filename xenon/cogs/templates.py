from discord.ext import commands as cmd
import pymongo
from discord import Embed
import discord
from asyncio import TimeoutError

from utils import checks, helpers, types
from utils.backups import BackupInfo, BackupLoader


class Templates(cmd.Cog, name="Creating"):
    approval_options = None

    def __init__(self, bot):
        self.bot = bot
        self.approval_options = {
            "✅": self._approve,
            "⭐": self._feature,
            "⛔": self._delete,
            "❔": self._delete_because("Insufficient name and/or description, please fill them in and resubmit again."),
            "🙅": self._delete_because("Not a template, just a copy of your server, use a backup instead. "
                                      "Templates are for everyone, not specifically for you, they must be generic.")
        }

    @cmd.group(aliases=["temp"], invoke_without_command=True)
    async def template(self, ctx):
        """Create & load public templates"""
        await ctx.send_help(self.template)

    @template.command(aliases=["c"])
    @cmd.cooldown(1, 30, cmd.BucketType.user)
    async def create(self, ctx, backup_id=None, name=None, *, description=None):
        """
        Turn a private backup into a **PUBLIC** template.


        __Arguments__

        **backup_id**: The id of the backup that you want to turn into a template
        **name**: A name for the template
        **description**: A description for the template


        __Examples__

        ```{c.prefix}template create oj1xky11871fzrbu start-template A good start for new servers```
        """

        backup_id = backup_id or await helpers.ask_question(
            ctx,
            "Please respond with the **id of the backup** that you want to turn into a template."
        )
        name = name or await helpers.ask_question(ctx, "Please respond with your desired **name for template**.")
        description = description or await helpers.ask_question(
            ctx,
            "Please respond with a **meaningful description** for the template."
        )

        name = name.lower().replace(" ", "_")
        backup = await ctx.db.backups.find_one(backup_id)
        if backup is None or backup.get("creator") != ctx.author.id:
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        already_exists = (await ctx.db.templates.find_one(name)) is not None
        if already_exists:
            raise cmd.CommandError(
                f"There is **already a template with that name**, please choose another one."
            )

        if len(description) < 30:
            raise cmd.CommandError("The template description must be **at least 30 characters** long.")

        backup["backup"]["members"] = []
        backup["backup"]["bans"] = []

        warning = await ctx.send(**ctx.em(
            "Are you sure you want to turn this backup into a template?\n\n"
            "Templates must not be a copy of your server, they are for **public use** and must be generic. "
            "Use `x!backup load` if you just want to load or clone your server.",
            type="warning"
        ))
        await warning.add_reaction("✅")
        await warning.add_reaction("❌")
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == warning.id and u.id == ctx.author.id,
                timeout=60
            )
        except TimeoutError:
            await warning.delete()
            raise cmd.CommandError(
                "Please make sure to **click the ✅ reaction** in order to create a template."
            )

        if str(reaction.emoji) != "✅":
            await warning.delete()
            return

        template = {
            "_id": name,
            "creator": backup["creator"],
            "used": 0,
            "featured": False,
            "approved": False,
            "original": backup_id,
            "description": description,
            "template": backup["backup"]
        }

        try:
            channel = await self.bot.fetch_channel(ctx.config.template_approval)
            await channel.send(embed=self._template_info(template))
        except Exception as e:
            raise cmd.CommandError("Failed to access the template approval channel: **%s**" % str(e))

        await ctx.db.templates.insert_one(template)
        await ctx.send(**ctx.em("Successfully **created template**.\n"
                                f"The template **will not be available** until a moderator approves it.\n"
                                f"Please join the [support server](https://discord.club/discord) and enable direct "
                                f"messages to get updates about your template.",
                                type="success"))

    @template.command(hidden=True)
    @checks.has_role_on_support_guild("Staff")
    async def approve(self, ctx, *, template_name):
        """
        Approve a template


        __Arguments__

        **template_name**: The name of the template
        """
        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.templates.find_one(template_name)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")

        await ctx.send(**ctx.em(f"Successfully **approved template**.", type="success"))
        await self._approve(template)

    async def _approve(self, template, *args):
        await self.bot.db.templates.update_one({"_id": template["_id"]}, {"$set": {"approved": True}})
        try:
            channel = await self.bot.fetch_channel(self.bot.config.template_list)
            await channel.send(embed=self._template_info(template))
        except Exception as e:
            raise cmd.CommandError("Failed to access the template list channel: **%s**" % str(e))

        try:
            user = await self.bot.fetch_user(template["creator"])
            await user.send(**self.bot.em(f"Your **template `{template['_id']}` has been approved**.", type="info"))
        except:
            pass

    @template.command(aliases=["unfeature"], hidden=True)
    @checks.has_role_on_support_guild("Staff")
    async def feature(self, ctx, *, template_name):
        """
        Feature a template


        __Arguments__

        **template_name**: The name of the template
        """
        feature = True
        if ctx.invoked_with == "unfeature":
            feature = False

        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.templates.find_one(template_name)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")

        await ctx.send(**ctx.em(f"Successfully **{'un' if not feature else ''}featured template**.", type="success"))
        await self._feature(template, state=feature)

    async def _feature(self, template, *args, state=True):
        await self.bot.db.templates.update_one({"_id": template["_id"]},
                                               {"$set": {"featured": state, "approved": True}})
        try:
            channel = await self.bot.fetch_channel(self.bot.config.template_featured)
            await channel.send(embed=self._template_info(template))
        except Exception as e:
            raise cmd.CommandError("Failed to access the template featured channel: **%s**" % str(e))

        try:
            user = await self.bot.fetch_user(template["creator"])
            await user.send(**self.bot.em(f"Your **template `{template['_id']}` has been featured**!", type="info"))
        except:
            pass

    @template.command(aliases=["del", "rm", "remove", "deny"], hidden=True)
    @checks.has_role_on_support_guild("Staff")
    async def delete(self, ctx, *, template_name):
        """
        Delete a template


        __Arguments__

        **template_name**: The name of the template
        """
        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.templates.find_one(template_name)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")

        await self._delete(template, ctx.author, ctx.channel)
        await ctx.send(**ctx.em("Successfully **deleted/denied template**.", type="success"))

    async def _delete(self, template, user, channel):
        try:
            question = await channel.send(
                **self.bot.em(f"Why do you want to delete/deny the template `{template['_id']}`?", type="wait_for")
            )
            creator = await self.bot.fetch_user(template["creator"])
            reason = ""

            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: question.channel.id == m.channel.id and user.id == m.author.id,
                    timeout=120
                )
                reason = f"```{msg.content}```"
                await msg.delete()

            except TimeoutError:
                pass

            finally:
                await question.delete()
                await creator.send(
                    **self.bot.em(f"Your **template `{template['_id']}` got denied**.\n{reason}",
                                  type="info"))

        except:
            pass

        finally:
            await self.bot.db.templates.delete_one({"_id": template["_id"]})

    def _delete_because(self, reason):
        async def predicate(template, user, channel):
            try:
                creator = await self.bot.fetch_user(template["creator"])
                await creator.send(
                    **self.bot.em(f"Your **template `{template['_id']}` got denied**.```\n{reason}```",
                                  type="info"))
            except:
                pass

            finally:
                await self.bot.db.templates.delete_one({"_id": template["_id"]})

        return predicate

    @template.command(aliases=["l"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.bot_has_managed_top_role()
    @cmd.cooldown(1, 5 * 60, cmd.BucketType.guild)
    async def load(self, ctx, template_name, *options):
        """
        Load a template
        You can find templates in the #template-list and #featured-templates channels on the support discord.
        The template name is always the first line of the message (e.g. "starter"), you don't need the backup id!
        You can also use `{c.prefix}backup search <search-term>` to find templates.


        __Arguments__

        **template_name**: The name of the template


        __Examples__

        Default options ```{c.prefix}template load starter```
        Only roles ```{c.prefix}template load starter !* roles```
        """
        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.templates.find_one(template_name)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")

        warning = await ctx.send(
            **ctx.em("Are you sure you want to load this template? **All channels and roles will get replaced!**",
                     type="warning"))
        await warning.add_reaction("✅")
        await warning.add_reaction("❌")
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == warning.id and u.id == ctx.author.id,
                timeout=60)
        except TimeoutError:
            await warning.delete()
            raise cmd.CommandError(
                "Please make sure to **click the ✅ reaction** in order to load the template."
            )

        if str(reaction.emoji) != "✅":
            ctx.command.reset_cooldown(ctx)
            await warning.delete()
            return

        await ctx.db.templates.update_one({"_id": template_name}, {"$inc": {"used": 1}})
        handler = BackupLoader(self.bot, self.bot.session, template["template"])
        await handler.load(ctx.guild, ctx.author, types.BooleanArgs(
            ["channels", "roles"] + list(options)
        ))

    @template.command(aliases=["i", "inf"])
    @cmd.cooldown(1, 5, cmd.BucketType.user)
    async def info(self, ctx, *, template_name):
        """
        Get information about a template


        __Arguments__

        **template_name**: The name of the template


        __Examples__

        ```{c.prefix}template info starter```
        """
        template_name = template_name.lower().replace(" ", "_")
        template = await ctx.db.templates.find_one(template_name)
        if template is None:
            raise cmd.CommandError(f"There is **no template** with the name `{template_name}`.")

        embed = self._template_info(template)
        embed._fields.insert(1, {"name": "Uses", "value": str(template.get("used") or 0), "inline": True})
        await ctx.send(embed=embed)

    def _template_info(self, template):
        handler = BackupInfo(self.bot, template["template"])
        embed = Embed(color=0x36393e)
        embed.title = template["_id"]
        embed.description = template["description"]
        embed.add_field(name="Creator", value=f"<@{template['creator']}>")
        embed.add_field(name="Channels", value=handler.channels(), inline=True)
        embed.add_field(name="Roles", value=handler.roles(), inline=True)

        return embed

    @template.command(aliases=["ls", "search"])
    @cmd.cooldown(1, 10, cmd.BucketType.user)
    async def list(self, ctx, *, keywords=""):
        """
        Get a list of public templates


        __Arguments__

        **keywords**: Keywords to search for. Make sure to include non stop-words


        __Examples__

        List all backups: ```{c.prefix}template list```
        Search for a template: ```{c.prefix}template search basic```
        """
        # await ctx.db.templates.create_index([("description", pymongo.TEXT), ("_id", pymongo.TEXT)])
        args = {
            "limit": 10,
            "skip": 0,
            "sort": [("featured", pymongo.DESCENDING), ("used", pymongo.DESCENDING)],
            "filter": {
                "approved": True,
            }
        }
        if len(keywords) != 0:
            args["filter"]["$text"] = {
                "$search": keywords,
                "$caseSensitive": False
            }

        msg = await ctx.send(embed=await self.create_list(args))
        options = ["◀", "❎", "▶"]
        for option in options:
            await msg.add_reaction(option)

        try:
            async for reaction, user in helpers.IterWaitFor(
                    self.bot,
                    event="reaction_add",
                    check=lambda r, u: u.id == ctx.author.id and r.message.id == msg.id and str(r.emoji) in options,
                    timeout=60
            ):
                emoji = reaction.emoji
                if isinstance(ctx.channel, discord.TextChannel):
                    try:
                        await msg.remove_reaction(emoji, user)
                    except Exception:
                        pass

                if str(emoji) == options[0]:
                    if args["skip"] > 0:
                        args["skip"] -= args["limit"]
                        await msg.edit(embed=await self.create_list(args))

                elif str(emoji) == options[2]:
                    args["skip"] += args["limit"]
                    await msg.edit(embed=await self.create_list(args))

                else:
                    raise TimeoutError

        except TimeoutError:
            if isinstance(ctx.channel, discord.TextChannel):
                try:
                    await msg.clear_reactions()
                except Exception:
                    pass

    async def create_list(self, args):
        emb = Embed(
            title="Template List",
            description="For a detailed list look at the #template_list channel in the [support discord](https://discord.club/discord).\n​\n"
                        "__**Templates:**__",
            color=0x36393e
        )
        emb.set_footer(text=f"Page {args['skip'] // args['limit'] + 1}")

        templates = self.bot.db.templates.find(**args)
        async for template in templates:
            emb.add_field(name=template["_id"],
                          value=template["description"] if len(template["description"]) > 0 else "No description",
                          inline=False)

        if len(emb.fields) == 0:
            emb.description += "\nNo templates to display"

        return emb

    @cmd.Cog.listener()
    async def on_message(self, msg):
        if not isinstance(msg.channel, discord.TextChannel):
            return

        if len(msg.embeds) == 0 or not msg.embeds[0].title:
            return

        if msg.channel.id == self.bot.config.template_approval and msg.author.bot:
            for emoji in self.approval_options.keys():
                await msg.add_reaction(emoji)

    @cmd.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id != self.bot.config.template_approval:
            return

        channel = self.bot.get_channel(payload.channel_id)
        user = await self.bot.fetch_user(payload.user_id)

        if channel is None or user is None or user.bot:
            return

        message = await channel.fetch_message(payload.message_id)

        action = self.approval_options.get(str(payload.emoji))
        if action is not None:
            if len(message.embeds) == 0:
                return

            template = await self.bot.db.templates.find_one(message.embeds[0].title)
            if template is None:
                return

            await action(template, user, channel)
            await message.delete()


def setup(bot):
    bot.add_cog(Templates(bot))
