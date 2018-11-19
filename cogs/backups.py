from discord.ext import commands as cmd
import discord
from discord_backups import BackupSaver, BackupLoader, BackupInfo
import string
import random
import traceback
from asyncio import TimeoutError, sleep
from datetime import datetime, timedelta
import pytz

from utils import checks, helpers


max_chatlog = 20


class Backups:
    def __init__(self, bot):
        self.bot = bot
        self.to_backup = []

        if getattr(bot, "backup_interval", None) is None:
            bot.backup_interval = bot.loop.create_task(self.interval_loop())
            bot.loop.create_task(self.backup_loop())

    @cmd.group(aliases=["bu"], invoke_without_command=True)
    async def backup(self, ctx):
        """Create & load backups of your servers"""
        await ctx.invoke(self.bot.get_command("help"), "backup")

    def random_id(self):
        return "".join([random.choice(string.digits + string.ascii_lowercase) for i in range(16)])

    @backup.command(aliases=["c"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @cmd.cooldown(1, 1 * 60, cmd.BucketType.guild)
    async def create(self, ctx, chatlog: int = 20):
        """
        Create a backup


        chatlog ::      The count of messages to save per channel (max. 20) (default 20)
        """
        chatlog = chatlog if chatlog < max_chatlog and chatlog > 0 else max_chatlog
        status = await ctx.send(**ctx.em("**Creating backup** ... Please wait", type="working"))
        handler = BackupSaver(self.bot, self.bot.session, ctx.guild)
        backup = await handler.save(chatlog)
        id = self.random_id()
        await ctx.db.rdb.table("backups").insert({
            "id": id,
            "creator": str(ctx.author.id),
            "timestamp": datetime.now(pytz.utc),
            "backup": backup
        }).run(ctx.db.con)

        await status.edit(**ctx.em("Successfully **created backup**.", type="success"))
        try:
            embed = ctx.em(
                f"Created backup of **{ctx.guild.name}** with the Backup id `{id}`\n", type="info")["embed"]
            embed.add_field(name="Usage",
                            value=f"```{ctx.prefix}backup load {id}```\n```{ctx.prefix}backup info {id}```")
            result_msg = await ctx.author.send(embed=embed)
            await result_msg.add_reaction("📱")
        except:
            traceback.print_exc()
            await status.edit(**ctx.em("I was **unable to send you the backup-id**. Please make sure you have dm's enabled.", type="error"))

    async def on_reaction_add(self, reaction, user):
        msg = reaction.message
        if not isinstance(msg.channel, discord.DMChannel) or user.bot:
            return

        if str(reaction.emoji) != "📱" or len(msg.embeds) == 0:
            return

        embed = msg.embeds[0]
        for field in embed.fields:
            if field.name == "Usage":
                await msg.edit(content=field.value, embed=None)
                break

    @backup.command(aliases=["l"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.bot_has_managed_top_role()
    @cmd.cooldown(1, 5 * 60, cmd.BucketType.guild)
    async def load(self, ctx, backup_id, chatlog: int = 20, *load_options):
        """
        Load a backup


        backup_id ::    The id of the backup

        chatlog   ::    The count of messages to load per channel (max. 20) (default 20)
        """
        chatlog = chatlog if chatlog < max_chatlog and chatlog >= 0 else max_chatlog
        backup = await ctx.db.rdb.table("backups").get(backup_id).run(ctx.db.con)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        warning = await ctx.send(**ctx.em("Are you sure you want to load this backup? **All channels and roles will get replaced!**", type="warning"))
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

        if len(load_options) == 0:
            options = {
                "channels": True,
                "roles": True,
                "bans": True
            }

        else:
            options = {}
            for opt in load_options:
                options[opt.lower()] = True

        handler = BackupLoader(self.bot, self.bot.session, backup["backup"])
        await handler.load(ctx.guild, ctx.author, chatlog, **options)
        await ctx.guild.text_channels[0].send(**ctx.em("Successfully loaded backup.", type="success"))

    @backup.command(aliases=["del", "remove", "rm"])
    @cmd.cooldown(1, 5, cmd.BucketType.user)
    async def delete(self, ctx, backup_id):
        """
        Delete a backup


        backup_id ::    The id of the backup
        """
        backup = await ctx.db.rdb.table("backups").get(backup_id).run(ctx.db.con)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        await ctx.db.rdb.table("backups").get(backup_id).delete().run(ctx.db.con)
        await ctx.send(**ctx.em("Successfully **deleted backup**.", type="success"))

    @backup.command(aliases=["i", "inf"])
    @cmd.cooldown(1, 5, cmd.BucketType.user)
    async def info(self, ctx, backup_id):
        """
        Get information about a backup

        backup_id ::    The id of the backup
        """
        backup = await ctx.db.rdb.table("backups").get(backup_id).run(ctx.db.con)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        handler = BackupInfo(self.bot, backup["backup"])
        embed = ctx.em("")["embed"]
        embed.title = handler.name
        embed.add_field(name="Creator", value=f"<@{backup['creator']}>")
        embed.add_field(name="Members", value=handler.member_count, inline=True)
        embed.add_field(name="Created At", value=helpers.datetime_to_string(
            backup["timestamp"]), inline=False
        )
        embed.add_field(name="Channels", value=handler.channels(), inline=True)
        embed.add_field(name="Roles", value=handler.roles(), inline=True)
        await ctx.send(embed=embed)

    @backup.command(aliases=["iv", "auto"])
    @cmd.cooldown(1, 30, cmd.BucketType.guild)
    async def interval(self, ctx, *interval):
        """
        Setup automated backups


        interval ::     The time between every backup.
                        Supported units: minutes (m), hours (h), days (d), weeks (w), month (m)
                        Example: 1d 12h
        """
        if len(interval) == 0:
            interval = await ctx.db.rdb.table("intervals").get(str(ctx.guild.id)).run(ctx.db.con)
            if interval is None:
                await ctx.send(**ctx.em("The backup interval **is currently turned off** for this guild.", type="info"))
                return

            embed = ctx.em("", type="info")["embed"]
            embed.add_field(
                name="Interval",
                value=str(timedelta(minutes=interval["interval"])).split(".")[0]
            )
            embed.add_field(
                name="Remaining",
                value=str(timedelta(minutes=interval["remaining"])).split(".")[0]
            )
            embed.add_field(
                name="Next Backup",
                value=helpers.datetime_to_string(
                    (datetime.utcnow() + timedelta(minutes=interval["interval"]))
                )
            )
            await ctx.send(embed=embed)
            return

        delta_types = {"m": 1, "h": 60, "d": 60 * 24, "w": 60 * 24 * 7}
        minutes = 0
        for part in interval:
            type = delta_types.get(part[-1], 1)
            try:
                minutes += int(part[:-1]) * type
            except ValueError:
                continue

        minutes = minutes if minutes >= 60 else 60
        await ctx.db.rdb.table("intervals").insert({
            "id": str(ctx.guild.id),
            "interval": minutes,
            "remaining": minutes
        }, conflict="replace").run(ctx.db.con)
        embed = ctx.em("Successfully updated the backup interval", type="success")["embed"]
        embed.add_field(name="Interval", value=str(timedelta(minutes=minutes)).split(".")[0])
        embed.add_field(
            name="Next Backup",
            value=helpers.datetime_to_string(datetime.utcnow() + timedelta(minutes=minutes))
        )
        await ctx.send(embed=embed)

    async def backup_loop(self):
        db = self.bot.db
        while True:
            try:
                await sleep(60)

                to_backup = self.to_backup.copy()
                self.to_backup = []
                for guild_id in to_backup:
                    guild = self.bot.get_guild(guild_id)
                    if guild is None:
                        await db.rdb.table("intervals").get(str(guild_id)).delete().run(db.con)

                    handler = BackupSaver(self.bot, self.bot.session, guild)
                    backup = await handler.save(max_chatlog)
                    id = self.random_id()
                    await db.rdb.table("backups").insert({
                        "id": id,
                        "creator": str(guild.owner.id),
                        "timestamp": datetime.now(pytz.utc),
                        "backup": backup
                    }).run(db.con)

                    embed = self.bot.em(
                        f"Created **automated** backup of **{guild.name}** with the Backup id `{id}`\n",
                        type="info"
                    )["embed"]
                    embed.add_field(
                        name="Usage",
                        value=f"```{self.bot.config.prefix}backup load {id}```\n```{self.bot.config.prefix}backup info {id}```"
                    )
                    result_msg = await guild.owner.send(embed=embed)
                    await result_msg.add_reaction("📱")
            except:
                traceback.print_exc()

    async def interval_loop(self):
        db = self.bot.db
        while True:
            try:
                await sleep(60)

                await db.rdb.table("intervals").update({"remaining": db.rdb.row["remaining"] - 1}).run(db.con)
                filter = db.rdb.table("intervals").filter(
                    lambda interval: (interval["remaining"] <= 0)
                )
                to_backup = await filter.run(db.con)
                await filter.update({"remaining": db.rdb.row["interval"]}).run(db.con)
                self.to_backup += [int(iv["id"]) for iv in await helpers.async_cursor_to_list(to_backup)]
            except:
                traceback.print_exc()


def setup(bot):
    bot.add_cog(Backups(bot))
