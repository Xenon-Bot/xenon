import asyncio
import os
import random
import traceback
from datetime import timedelta, datetime

import discord
from discord.ext import commands

import statics
from cogs.utils import checks, backups, formatter, file_system, converters

em = formatter.embed_message


class Backups:
    def __init__(self, bot):
        self.bot = bot
        self.interval_task = None
        self.run_task = None
        self.to_backup = []

    @commands.group(invoke_without_command=True, aliases=["bu"])
    async def backup(self, ctx):
        """Main backup command"""
        await ctx.invoke(self.bot.get_command("help"), "backup")

    @backup.command()
    async def rejoin(self, ctx):
        """Authorize this bot to add your members back."""
        await ctx.send(
            **em(
                "By clicking the link below you **authorize Xenon** to **add you back** to backed up guilds you were in.\n"
                "https://xenon.discord.club/rejoin", type="info"))

    @backup.command(aliases=["c"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(administrator=True)
    @commands.cooldown(1, 1 * 60, commands.BucketType.guild)
    async def create(self, ctx, chatlog: int = statics.max_chatlog):
        """
        Create a backup

        **chatlog**: the count of messages that get saved in a channel
        """
        if chatlog < 0 or chatlog > statics.max_chatlog:
            ctx.command.reset_cooldown(ctx)
            raise commands.BadArgument(
                f"Please **specify how many messages** you want to be backed up between **0** and **{statics.max_chatlog}**.")

        id = ""
        for i in range(16):
            id += str(random.choice(statics.alphabet))

        status = await ctx.send(**em("Creating backup, this could take a while.", type="working"))

        handler = backups.BackupHandler(self.bot)
        data = await handler.save(ctx.guild, ctx.author, chatlog)
        await file_system.save_json_file(f"backups/{id}", data)

        try:
            if ctx.author.dm_channel is None:
                await ctx.author.create_dm()
            dm_channel = ctx.author.dm_channel

            embed = em(f"Created backup of **{ctx.guild.name}** with the Backup id `{id}`.", type="info")["embed"]
            embed.add_field(name="Usage", value=f"```{statics.prefix}backup load {id}```\n"
                                                f"```{statics.prefix}backup info {id}```")
            embed.set_footer(text="Click the phone below to get a mobile friendly version")
            info = await dm_channel.send(embed=embed)
            await info.add_reaction("📱")
        except discord.Forbidden:
            await status.edit(
                **em("I was **unable to send you the backup-id**. Please enable private messages on this server!",
                     type="error"))

        await status.edit(
            **em("Successfully **created backup**. Please **check your dm's** to see the backup-id.", type="success"))

    async def on_reaction_add(self, reaction, user):
        if user.bot or reaction.emoji != "📱" or len(reaction.message.embeds) == 0 \
                or reaction.message.author.id != self.bot.user.id:
            return

        embed = reaction.message.embeds[0]
        if embed.author.name != "Info" or len(embed.fields) == 0:
            return

        field = embed.fields[0]
        if field.name != "Usage":
            return

        await reaction.message.edit(content=field.value, embed=None)

    @backup.command(aliases=["del"])
    async def delete(self, ctx, backup_id):
        data = await file_system.get_json_file(f"backups/{backup_id}")
        if data is None:
            raise commands.BadArgument(f"Sorry, I was **unable to find** that **backup**.")

        if str(ctx.author.id) != str(data["creator"]):
            raise commands.BadArgument(f"Only **the creator** can **delete** this backup.")

        await file_system.delete(f"backups/{backup_id}")
        await ctx.send(**em(f"Successfully **deleted the backup**.", type="success"))

    @backup.command(aliases=["l"])
    @commands.guild_only()
    @commands.check(checks.has_top_role)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(administrator=True)
    @commands.cooldown(1, 5 * 60, commands.BucketType.guild)
    async def load(self, ctx, backup_id: converters.JsonFileContent("backups/"), *options_input):
        """
        Load a backup

        **backup_id**: the id of the backup
        **options**: info (on), settings (on), roles (on), channels (on), bans (on), delete (on), rejoin (off)
        <option> turn an option on; !<option> turn an option off
        """
        if backup_id is None:
            raise commands.BadArgument("I was **unable to find** that backup.")

        data = backup_id
        if str(data["creator"]) == str(self.bot.user.id):
            guild = self.bot.get_guild(int(data["guild_id"]))
            if guild is None:
                raise commands.BadArgument(
                    f"Sorry, **you can't load this backup** because you are **not the creator** of it. After a discussion with discord this was the only way **to protect this bot** against abusers. [More details](https://cdn.discordapp.com/attachments/442447986052562956/480486412446072857/unknown.png)")

            owner = guild.owner
            if owner.id != ctx.author.id:
                raise commands.BadArgument(
                    f"Sorry, **you can't load this backup** because you are **not the creator** of it. After a discussion with discord this was the only way **to protect this bot** against abusers. [More details](https://cdn.discordapp.com/attachments/442447986052562956/480486412446072857/unknown.png)")

        elif str(ctx.author.id) != str(data["creator"]):
            raise commands.BadArgument(
                f"Sorry, **you can't load this backup** because you are **not the creator** of it. After a discussion with discord this was the only way **to protect this bot** against abusers. [More details](https://cdn.discordapp.com/attachments/442447986052562956/480486412446072857/unknown.png)")

        handler = backups.BackupHandler(self.bot)
        await handler.load_command(ctx, data, options_input)

    @backup.command(aliases=["i"])
    async def info(self, ctx, backup_id):
        """
        Get information about a backup

        **backup_id**: the id of the backup
        """
        data = await file_system.get_json_file(f"backups/{backup_id}")
        if data is None:
            raise commands.BadArgument(f"Sorry, I was **unable to find** this **backup**.")

        handler = backups.BackupHandler(self.bot)
        await ctx.send(embed=handler.get_backup_info(data))

    @backup.command(aliases=["iv"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(administrator=True)
    async def interval(self, ctx, *interval):
        """
        Let the bot create a backup in a certain interval

        **interval**: the interval e.g. '1d 8h 15m'
        """
        if len(interval) == 0:
            intervals = await file_system.get_json_file("intervals")
            if intervals is None:
                await ctx.invoke(self.bot.get_command("help"), "backup", "interval")
                return

            interval = intervals.get(str(ctx.guild.id))
            if interval is None:
                await ctx.invoke(self.bot.get_command("help"), "backup", "interval")
                return

            embed = discord.Embed(color=statics.embed_color)
            embed.set_author(name="Current Interval",
                             icon_url="http://icons.iconarchive.com/icons/graphicloads/colorful-long-shadow/256/Clock-icon.png")
            embed.add_field(name="Interval", value=self.bot.time.format_timedelta(timedelta(minutes=interval[0])))
            embed.add_field(name="Time Remaining", value=self.bot.time.format_timedelta(timedelta(minutes=interval[1])))
            embed.add_field(name="Next Backup",
                            value=self.bot.time.format_datetime(datetime.utcnow() + timedelta(minutes=interval[1])))
            await ctx.send(embed=embed)
            return

        if interval[0] == "off":
            intervals = await file_system.get_json_file("intervals")
            if intervals is None:
                intervals = {}
            else:
                intervals.pop(str(ctx.guild.id), None)

            await file_system.save_json_file("intervals", intervals)
            await ctx.send(**em(f"Successfully **turned backup interval off**", type="success"))
            return

        try:
            interval_sum = sum(
                [int(interval_part[:-1]) * statics.time_units[interval_part[-1]] for interval_part in interval])
        except:
            raise commands.BadArgument(f"Please specify a valid **interval between 1h and 2w**, e.g. `8h 15m`.")

        if interval_sum < 60 or interval_sum > 60 * 24 * 7 * 2:
            raise commands.BadArgument(f"Please specify a valid **interval between 1h and 2w**, e.g. `8h 15m`.")

        intervals = await file_system.get_json_file("intervals")
        if intervals is None:
            intervals = {}

        intervals[str(ctx.guild.id)] = [interval_sum, interval_sum]
        await file_system.save_json_file("intervals", intervals)

        await ctx.send(**em(
            f"Successfully **set backup interval** to `{self.bot.time.format_timedelta(timedelta(minutes=interval_sum))}`"),
                       type="success")

    async def _run_backups(self):
        while True:
            await asyncio.sleep(30)

            for guild in self.to_backup:
                try:
                    id = ""
                    for i in range(16):
                        id += str(random.choice(statics.alphabet))

                    handler = backups.BackupHandler(self.bot)
                    data = await handler.save(guild, guild.owner)
                    await file_system.save_json_file(f"backups/{id}", data)

                    if guild.owner.dm_channel is None:
                        await guild.owner.create_dm()
                    dm_channel = guild.owner.dm_channel

                    embed = em(f"Created backup of **{guild.name}** with the Backup id `{id}`.", type="info")
                    embed.add_field(name="Usage", value=f"```{statics.prefix}backup load {id}```\n"
                                                        f"```{statics.prefix}backup info {id}```")
                    await dm_channel.send(embed=embed)
                except Exception as e:
                    print(f"Error executing interval for {guild.id}: {type(e).__name__} {str(e)}")

            self.to_backup = []

    async def _interval_loop(self):
        while True:
            await asyncio.sleep(1 * 60)

            try:
                intervals = await file_system.get_json_file("intervals")
                if intervals is None:
                    continue

                for guild_id, interval in intervals.copy().items():
                    interval[1] -= 1
                    if interval[1] < 0:
                        interval[1] = interval[0]

                        guild = self.bot.get_guild(int(guild_id))
                        if guild is None:
                            intervals.pop(guild_id, None)
                            continue
                        self.to_backup.append(guild)

                    intervals[guild_id] = interval

                await file_system.save_json_file("intervals", intervals)

            except:
                traceback.print_exc()

    async def on_ready(self):
        if self.interval_task is None:
            self.interval_task = self.bot.loop.create_task(self._interval_loop())

        if self.run_task is None:
            self.run_task = self.bot.loop.create_task(self._run_backups())


def setup(bot):
    bot.add_cog(Backups(bot))
