import asyncio
import typing
from datetime import timedelta, datetime
from prettytable import PrettyTable

import discord
from discord.ext import commands

import statics
from cogs.utils import converters, formatter, time

em = formatter.embed_message


class Basics:
    def __init__(self, bot):
        self.bot = bot
        self.uptime = 0

        self.bot.loop.create_task(self._uptime_loop())

    @commands.command()
    async def ping(self, ctx):
        """Shows the latency of the bot"""
        ms = self.bot.latency * 1000
        embed = em(f"I have a **latency of {round(ms, 1)}ms**!")["embed"]
        embed.set_author(name="Pong")

        await ctx.send(embed=embed)

    @commands.command()
    async def shards(self, ctx):
        shards = self.bot.shard_info
        table = PrettyTable()
        table.field_names = ["Shard-Id", "Guilds", "Users", "Latency"]
        for shard, info in shards.items():
            guilds, users, latency = info.values()
            table.add_row([shard, guilds, users, f"{round(latency * 100, 1)} ms"])

        pages = formatter.paginate(str(table), limit=1500)
        for page in pages:
            try:
                await ctx.send(f"```diff\n{page}```")
            except:
                print("asd")

    @commands.command()
    async def invite(self, ctx):
        """Shows the invite of the bot"""
        await ctx.invoke(self.bot.get_command("info bot"))

    @commands.group(aliases=["i"], invoke_without_command=True)
    async def info(self, ctx,
                   something: typing.Union[discord.Member, discord.User, discord.Role, discord.TextChannel] = None):
        """
        Shows info about a discord object

        **something**: A member, channel, role, user (id / mention / name)

        **Examples**: `info channel #general`, `info user Xenon`
        """
        if something is None:
            await ctx.invoke(self.bot.get_command("info bot"))
            return

        destinations = {
            discord.Member: "info user",
            discord.User: "info user",
            discord.Role: "info role",
            discord.TextChannel: "info channel"
        }

        if type(something) not in destinations:
            raise commands.BadArgument(f"Sorry, I was **unable to find 'whatever you searched for'**.")

        await ctx.invoke(self.bot.get_command(destinations[type(something)]), something)

    @info.command(name="bot")
    async def bot_cmd(self, ctx):
        bot_info = await self.bot.dblpy.get_bot_info(self.bot.user.id)

        embed = discord.Embed(title="Bot Info", color=statics.embed_color, description=bot_info["shortdesc"])
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Invite", value=f"[Click Here]({bot_info['invite']})")
        embed.add_field(name="Support", value=f"[Click Here]({statics.support_invite})")
        embed.add_field(name="Prefix", value=statics.prefix)

        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)))
        embed.add_field(name="Shards", value=str(self.bot.shard_count))
        user_count = sum(len(guild.members) for guild in self.bot.guilds)
        embed.add_field(name="Users", value=str(user_count))

        embed.add_field(name="Uptime", value=time.format_timedelta(timedelta(minutes=self.uptime)))
        last_restart = time.format_datetime(datetime.utcnow() - timedelta(minutes=self.uptime))
        embed.add_field(name="Last Restart", value=last_restart)

        await ctx.send(embed=embed)

    @info.command(aliases=["member"])
    async def user(self, ctx, user: converters.MemberUserConvert):
        embed = discord.Embed(title="User Info", color=statics.embed_color)
        if not isinstance(user, discord.Member):
            for guild in ctx.bot.guilds:
                member = guild.get_member(user.id)
                if member is not None:
                    user = member
                    embed.add_field(name="Guild", value=member.guild.name)

        embed.set_footer(text=f"Unique Id: {user.id}")
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="Name", value=f"{str(user)} {user.mention}")
        if isinstance(user, discord.Member):
            embed.add_field(name="Status", value=str(user.status).title())
            if user.activity is not None:
                if isinstance(user.activity, discord.Game):
                    embed.add_field(name="Playing", value=user.activity.name)
                elif isinstance(user.activity, discord.Streaming):
                    embed.add_field(name="Streaming",
                                    value=f"{user.activity.name} [:arrow_heading_up:]({user.activity.url})")
                else:
                    embed.add_field(name="Activity", value=user.activity.name)

            embed.add_field(name="Joined At", value=time.format_datetime(user.joined_at))
            roles = "```"
            for role in user.roles:
                if len(roles) + len(role.name) >= 1000:
                    roles += "\n..."
                    break
                roles += role.name + "\n"
            roles += "```"

            embed.add_field(name=f"Roles ({len(user.roles)})", value=roles)

        await ctx.send(embed=embed)

    @info.command()
    async def role(self, ctx, role: discord.Role):
        embed = discord.Embed(title="Role Info", color=statics.embed_color)
        embed.set_footer(text=f"Unique Id: {role.id}")
        embed.add_field(name="Name", value=role.name)
        embed.add_field(name="Created At", value=time.format_datetime(role.created_at, short=True))
        embed.add_field(name="Members", value=str(len(role.members)))
        roles = "```md\n"
        for role_l in role.guild.role_hierarchy:
            if len(roles) + len(role_l.name) >= 1000:
                roles += "\n..."
                break
            roles += f"{'# ' if role_l == role else ''}{role_l.name}\n"
        roles += "```"

        embed.add_field(name=f"Position ({role.position})", value=roles)
        permissions = "```"
        for permission, allowed in dict(role.permissions).items():
            if not allowed:
                continue

            if len(permissions) + len(permission) >= 1000:
                permissions += "\n..."
                break

            permissions += permission.replace("_", " ").title() + "\n"
        permissions += "```"

        embed.add_field(name=f"Permissions ({role.permissions.value})", value=permissions)

        await ctx.send(embed=embed)

    @info.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        embed = discord.Embed(title="Channel Info", color=statics.embed_color, description=channel.topic)
        embed.set_footer(text=f"Unique Id: {channel.id}")
        embed.add_field(name="Name", value=channel.name)
        embed.add_field(name="Category", value=channel.category.name)
        embed.add_field(name="Members", value=str(len(channel.members)))
        channels = "```md\n"
        for category in channel.guild.categories:
            if len(channels) + len(category.name) >= 1000:
                channels += "\n..."
                break
            channels += category.name + "\n"
            for channel_l in category.channels:
                if len(channels) + len(channel_l.name) >= 1000:
                    channels += "\n..."
                    break
                channels += f"{'#  ' if channel_l == channel else '   '} {channel_l.name}\n"
        channels += "```"

        embed.add_field(name=f"Position ({channel.position})", value=channels)
        roles = "```"
        for role in channel.changed_roles:
            if len(roles) + len(role.name) >= 1000:
                roles += "\n..."
                break
            roles += role.name + "\n"
        roles += "```"

        embed.add_field(name="Overrides", value=roles)

        await ctx.send(embed=embed)

    @info.command(aliases=["server"])
    async def guild(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title="Guild Info", color=statics.embed_color)
        embed.set_thumbnail(url=guild.icon_url)
        embed.set_footer(text=f"Unique Id: {guild.id}")
        embed.add_field(name="Name", value=guild.name)
        embed.add_field(name="Owner", value=f"<@{guild.owner.id}>")
        embed.add_field(name="Created At", value=time.format_datetime(guild.created_at, short=True))
        embed.add_field(name=f"Members ({len(guild.members)})",
                        value=f"**{sum(1 for member in guild.members if str(member.status) != 'offline')}** online"
                              f"\n**{sum(1 for member in guild.members if member.bot)}** bots")
        channels = "```"
        for category in guild.categories:
            if len(channels) + len(category.name) >= 1000:
                channels += "\n..."
                break
            channels += category.name + "\n"
            for channel in category.channels:
                if len(channels) + len(channel.name) >= 1000:
                    channels += "\n..."
                    break
                channels += f"   {'#' if type(channel) == discord.TextChannel else '~'} {channel.name}\n"
        channels += "```"

        embed.add_field(name=f"Channels ({len(guild.channels)})", value=channels)
        roles = "```"
        for role in guild.role_hierarchy:
            if len(roles) + len(role.name) >= 1000:
                roles += "\n..."
                break
            roles += role.name + "\n"
        roles += "```"

        embed.add_field(name=f"Roles ({len(guild.roles)})", value=roles)
        emojis = ""
        for emoji in guild.emojis:
            emoji_formatted = f"<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>"
            if len(emojis) + len(emoji_formatted) >= 1000:
                emojis += " ..."
                break
            emojis += emoji_formatted

        if len(emojis) > 0:
            embed.add_field(name=f"Emojis ({len(guild.emojis)})", value=emojis)

        await ctx.send(embed=embed)

    async def _uptime_loop(self):
        while True:
            await asyncio.sleep(1 * 60)
            self.uptime += 1


def setup(bot):
    bot.add_cog(Basics(bot))
