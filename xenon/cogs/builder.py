from discord.ext import commands as cmd
import asyncio
import discord

from utils import helpers


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
                    ["staff_role", False],
                    ["muted_role", False],
                    ["color_roles", False],
                    ["game_specific_roles", False]
                ]
            },
            {
                "name": "channels",
                "options": [
                    ["delete_old_channels", True],
                    ["announcement_channel", False],
                    ["rules_channel", False],
                    ["staff_channels", False],
                    ["game_specific_channels", False]
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
                try:
                    await self.msg.remove_reaction(reaction.emoji, user)
                except Exception:
                    pass

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

            raise cmd.CommandError("timeout")

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
        raise cmd.CommandError("canceled")

    async def _finish(self):
        return False

    def _create_embed(self):
        page_options = self.pages[self.page - 1]
        embed = self.ctx.em("", title="Server Builder")["embed"]
        embed.title = page_options["name"].title()
        for i, (name, value) in enumerate(page_options["options"]):
            embed.description += f"{i + 1}\u20e3 **{name.replace('_', ' ').title()}** -> {'✅' if value else '❌'}\n"

        return embed


class Builder(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cmd.command(aliases=["builder", "bld", "bd"])
    async def build(self, ctx):
        menu = BuildMenu(ctx)
        options = await menu.run()

        roles = {"staff": [], "muted": []}

        if options.get("delete_old_channels"):
            for channel in ctx.guild.channels:
                await channel.delete()

        if options.get("delete_old_roles"):
            for role in filter(lambda r: not r.managed and not r.is_default(), ctx.guild.roles):
                await role.delete()

        if options.get("staff_roles"):
            staff_roles = [
                {
                    "name": "Admin"
                },
                {
                    "name": "Moderator"
                }
            ]

            for kwargs in staff_roles:
                roles["staff"].append(await ctx.guild.create_role(**kwargs))

        if options.get("color_roles"):
            color_roles = [
                {
                    "name": "Red"
                },
                {
                    "name": "Green"
                },
                {
                    "name": "Yellow"
                }
            ]

            for kwargs in color_roles:
                await ctx.guild.create_role(**kwargs)

        if options.get("muted_role"):
            roles["muted"].append(await ctx.guild.create_role(name="Muted"))


def setup(bot):
    bot.add_cog(Builder(bot))
