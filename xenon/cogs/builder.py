from discord.ext import commands as cmd
import asyncio
import discord

from utils import helpers, checks


def create_permissions(**kwargs):
    permissions = discord.Permissions.none()
    permissions.update(**kwargs)
    return permissions


class BuildMenu:
    def __init__(self, ctx):
        self.ctx = ctx
        self.msg = None
        self.page = 1
        self.pages = [
            {
                "name": "roles",
                "options": [
                    ["delete_old_roles", True],
                    ["staff_roles", True],
                    ["bot_role", True],
                    ["muted_role", True],
                    ["color_roles", False],
                    ["game_specific_roles", False]
                ]
            },
            {
                "name": "channels",
                "options": [
                    ["delete_old_channels", True],
                    ["info_channels", True],
                    ["staff_channels", True],
                    ["general_channels", True],
                    ["development_channels", False],
                    ["gaming_channels", False],
                    ["afk_channel", False],
                    ["log_channels", False]
                ]
            }
        ]

    async def update(self):
        await self.msg.edit(embed=self._create_embed())

    async def run(self):
        self.msg = await self.ctx.send(embed=self._create_embed())

        options = {
            **{f"{i + 1}\u20e3": self._switch_option(i) for i in range(9)},
            "◀": self._prev_page,
            "▶": self._next_page,
            "❎": self._cancel,
            "✅": self._finish,
        }

        for option in options:
            await self.msg.add_reaction(option)

        try:
            async for reaction, user in helpers.IterWaitFor(
                    self.ctx.bot,
                    event="reaction_add",
                    check=lambda r, u: u.id == self.ctx.author.id and
                                       r.message.id == self.msg.id and
                                       str(r.emoji) in options.keys(),
                    timeout=3 * 60
            ):
                self.ctx.bot.loop.create_task(self.msg.remove_reaction(reaction.emoji, user))

                if not await options[str(reaction.emoji)]():
                    try:
                        await self.msg.clear_reactions()
                    except Exception:
                        pass

                    return {name: value for page in self.pages for name, value in page["options"]}

                await self.update()
        except asyncio.TimeoutError:
            try:
                await self.msg.clear_reactions()
            except Exception:
                pass

            raise cmd.CommandError("**Canceled build process**, because you didn't do anything.")

    async def _next_page(self):
        if self.page < len(self.pages):
            self.page += 1

        return True

    async def _prev_page(self):
        if self.page > 1:
            self.page -= 1

        return True

    def _switch_option(self, option):
        async def predicate():
            try:
                self.pages[self.page - 1]["options"][option][1] = not self.pages[self.page - 1]["options"][option][1]
            except IndexError:
                pass

            return True

        return predicate

    async def _cancel(self):
        try:
            await self.msg.clear_reactions()
        except Exception:
            pass
        raise cmd.CommandError("You canceled the build process.")

    async def _finish(self):
        return False

    def _create_embed(self):
        page_options = self.pages[self.page - 1]
        embed = self.ctx.em("", title="Server Builder")["embed"]
        embed.title = page_options["name"].title()
        embed.set_footer(text="Enable / Disable options with the reactions and click ✅ when you are done.")
        for i, (name, value) in enumerate(page_options["options"]):
            embed.description += f"{i + 1}\u20e3 **{name.replace('_', ' ').title()}** -> {'✅' if value else '❌'}\n"

        return embed


class Builder(cmd.Cog, name="Creating"):
    def __init__(self, bot):
        self.bot = bot

    @cmd.command(aliases=["builder", "bld", "bd"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.bot_has_managed_top_role()
    @cmd.cooldown(1, 5 * 60, cmd.BucketType.guild)
    async def build(self, ctx):
        """
        Choose between different options and build your discord server in less than a minute
        Enable and disable options by clicking the associated number and change the page
        by clicking the arrows. Click on the check to start the build process.


        __Examples__

        ```{c.prefix}build```
        """
        menu = BuildMenu(ctx)
        reason = f"Built by {ctx.author}"
        options = await menu.run()

        if options["delete_old_channels"] or options["delete_old_roles"]:
            warning = await ctx.send(
                **ctx.em("Are you sure you want to start the build process?\n"
                         "Channels and roles might get deleted and reconstructed from the build options!",
                         type="warning"))
            await warning.add_reaction("✅")
            await warning.add_reaction("❌")
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda r, u: r.message.id == warning.id and u.id == ctx.author.id,
                    timeout=60)
            except asyncio.TimeoutError:
                await warning.delete()
                raise cmd.CommandError(
                    "Please make sure to **click the ✅ reaction** in order to continue.")

            if str(reaction.emoji) != "✅":
                ctx.command.reset_cooldown(ctx)
                await warning.delete()
                return

        roles = {"staff": [], "muted": [], "bot": []}

        if options["delete_old_channels"]:
            for channel in ctx.guild.channels:
                await channel.delete(reason=reason)

        if options["delete_old_roles"]:
            for role in filter(lambda r: not r.managed and not r.is_default(), ctx.guild.roles):
                await role.delete(reason=reason)

        if options["staff_roles"]:
            staff_roles = [
                {
                    "name": "─────────────"
                },
                {
                    "name": "Owner",
                    "color": discord.Color.dark_red(),
                    "permissions": discord.Permissions.all()
                },
                {
                    "name": "Admin",
                    "color": discord.Color.red(),
                    "permissions": discord.Permissions.all()
                },
                {
                    "name": "Moderator",
                    "color": discord.Color.teal(),
                    "permissions": create_permissions(
                        kick_members=True,
                        ban_members=True,
                        view_audit_log=True,
                        priority_speaker=True,
                        mute_members=True,
                        deafen_members=True,
                        move_members=True,
                        manage_nicknames=True
                    )
                }
            ]

            for kwargs in staff_roles:
                roles["staff"].append(await ctx.guild.create_role(**kwargs, reason=reason))

        if options["bot_role"]:
            roles["bot"].append(await ctx.guild.create_role(
                name="Bot",
                color=discord.Color.blurple(),
                permissions=create_permissions(
                    kick_members=True,
                    ban_members=True,
                    view_audit_log=True,
                    priority_speaker=True,
                    mute_members=True,
                    deafen_members=True,
                    move_members=True,
                    manage_nicknames=True
                ),
                reason=reason
            ))

        if options["muted_role"]:
            roles["muted"].append(await ctx.guild.create_role(
                name="Muted",
                color=discord.Color.dark_grey(),
                permissions=create_permissions(
                    send_messages=False,
                    add_reactions=False,
                    connect=False
                ),
                reason=reason
            ))

        if options["color_roles"]:
            color_roles = [
                {
                    "name": "──── Colors ────"
                },
                {
                    "name": "Black",
                    "color": discord.Color(0)
                },
                {
                    "name": "Blue",
                    "color": discord.Color(0x4363D8)
                },
                {
                    "name": "Brown",
                    "color": discord.Color(0x9A6324)
                },
                {
                    "name": "Cyan",
                    "color": discord.Color(0x42D4F4)
                },
                {
                    "name": "Green",
                    "color": discord.Color(0x3CB44B)
                },
                {
                    "name": "Grey",
                    "color": discord.Color(0xA9A994)
                },
                {
                    "name": "Lavender",
                    "color": discord.Color(0xE6BEFF)
                },
                {
                    "name": "Lime",
                    "color": discord.Color(0xBFE743)
                },
                {
                    "name": "Magenta",
                    "color": discord.Color(0xF032E6)
                },
                {
                    "name": "Maroon",
                    "color": discord.Color(0x800014)
                },
                {
                    "name": "Mint",
                    "color": discord.Color(0xAAFFC3)
                },
                {
                    "name": "Navy",
                    "color": discord.Color(0x000075)
                },
                {
                    "name": "Olive",
                    "color": discord.Color(0x808012)
                },
                {
                    "name": "Orange",
                    "color": discord.Color(0xF58231)
                },
                {
                    "name": "Pink",
                    "color": discord.Color(0xF4BCBE)
                },
                {
                    "name": "Purple",
                    "color": discord.Color(0x911EB4)
                },
                {
                    "name": "Red",
                    "color": discord.Color(0xE62345)
                },
                {
                    "name": "Teal",
                    "color": discord.Color(0x469990)
                },
                {
                    "name": "White",
                    "color": discord.Color(0xFFFFFF)
                },
                {
                    "name": "Yellow",
                    "color": discord.Color(0xFFE119)
                },
            ]

            for kwargs in color_roles:
                await ctx.guild.create_role(**kwargs, reason=reason)

        if options["game_specific_roles"]:
            game_roles = ["──── Games ────", "minecraft", "fortnite", "apex", "pubg", "roblox", "destiny", "rainbow 6"]
            for name in game_roles:
                await ctx.guild.create_role(name=name, reason=reason)

        if options["info_channels"]:
            info_category = await ctx.guild.create_category(
                name="Info",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(
                        send_messages=False
                    ),
                    **{role: discord.PermissionOverwrite(
                        send_messages=True
                    ) for role in roles["staff"]}
                },
                reason=reason
            )

            channels = ["announcements", "faq", "rules"]
            for name in channels:
                await info_category.create_text_channel(name=name, reason=reason)

        if options["staff_channels"]:
            staff_category = await ctx.guild.create_category(
                name="Staff",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(
                        read_messages=False,
                        send_messages=False,
                        connect=False
                    ),
                    **{role: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        connect=True
                    ) for role in roles["staff"]},
                    **{role: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        connect=True
                    ) for role in roles["bot"]}
                },
                reason=reason
            )

            text_channels = ["staff general", "staff commands"]
            for name in text_channels:
                await staff_category.create_text_channel(name=name, reason=reason)

            await staff_category.create_voice_channel(name="Staff Voice")

        if options["general_channels"]:
            general_category = await ctx.guild.create_category(
                name="General",
                overwrites={role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                    connect=False
                ) for role in roles["muted"]},
                reason=reason
            )

            text_channels = ["general", "shitpost", "commands"]
            for name in text_channels:
                await general_category.create_text_channel(name=name)

            await general_category.create_voice_channel(name="General")

        if options["development_channels"]:
            dev_category = await ctx.guild.create_category(
                name="Development",
                overwrites={role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                    connect=False
                ) for role in roles["muted"]},
                reason=reason
            )

            text_channels = ["python", "javascript", "java", "kotlin", "c", "go", "ruby"]
            for name in text_channels:
                await dev_category.create_text_channel(name=name)

        if options["gaming_channels"]:
            game_category = await ctx.guild.create_category(
                name="Gaming",
                overwrites={role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                    connect=False
                ) for role in roles["muted"]},
                reason=reason
            )

            text_channels = ["gaming general", "team finding"]
            for name in text_channels:
                await game_category.create_text_channel(name=name, reason=reason)

            voice_channels = [
                {
                    "name": "Free 1"
                },
                {
                    "name": "Free 2"
                },
                {
                    "name": "Duo 1",
                    "user_limit": 2
                },
                {
                    "name": "Duo 2",
                    "user_limit": 2
                },
                {
                    "name": "Trio 1",
                    "user_limit": 3
                },
                {
                    "name": "Trio 2",
                    "user_limit": 3
                },
                {
                    "name": "Squad 1",
                    "user_limit": 4
                },
                {
                    "name": "Squad 2",
                    "user_limit": 4
                }
            ]
            for kwargs in voice_channels:
                await game_category.create_voice_channel(**kwargs, reason=reason)

        if options["afk_channel"]:
            afk_category = await ctx.guild.create_category(
                name="AFK",
                overwrites={role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                    connect=False
                ) for role in roles["muted"]},
                reason=reason
            )

            afk_channel = await afk_category.create_voice_channel(name="Afk")
            await ctx.guild.edit(afk_channel=afk_channel)

        if options["log_channels"]:
            log_category = await ctx.guild.create_category(
                name="Logs",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(
                        read_messages=False,
                        send_messages=False,
                        connect=False
                    ),
                    **{role: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=False,
                        connect=True
                    ) for role in roles["staff"]},
                    **{role: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        connect=True
                    ) for role in roles["bot"]}
                },
                reason=reason
            )

            await log_category.create_text_channel(name="bot logs")
            member_logs = await log_category.create_text_channel(name="members")
            await ctx.guild.edit(
                system_channel=member_logs,
                system_channel_flags=discord.SystemChannelFlags(join_notifications=True),
                reason=reason
            )


def setup(bot):
    bot.add_cog(Builder(bot))
