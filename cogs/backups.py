from discord.ext import commands as cmd
from discord_backups import BackupSaver, BackupLoader, BackupInfo
import string
import random
import traceback
from asyncio import TimeoutError, sleep
from datetime import datetime, timedelta
import pytz

from utils import checks, helpers


max_reinvite = 100
min_interval = 60 * 24


class Backups:
    def __init__(self, bot):
        self.bot = bot
        self.to_backup = []

        if getattr(bot, "backup_interval", None) is None:
            bot.backup_interval = bot.loop.create_task(self.interval_loop())

    async def _get_backup(self, id):
        return await self.bot.db.table("backups").get(id).run(self.bot.db.con)

    async def _create_backup(self, creator_id, data, id=None):
        id = id or self.random_id()
        await self.bot.db.table("backups").insert({
            "id": id,
            "creator": str(creator_id),
            "timestamp": datetime.now(pytz.utc),
            "backup": data
        }, conflict="replace").run(self.bot.db.con)
        return id

    async def _delete_backup(self, id):
        backup = await self._get_backup(id)
        if backup is None:
            return False

        await self.bot.db.table("backups").get(id).delete().run(self.bot.db.con)
        return True

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
    async def create(self, ctx):
        """
        Create a backup
        """

        status = await ctx.send(**ctx.em("**Creating backup** ... Please wait", type="working"))
        handler = BackupSaver(self.bot, self.bot.session, ctx.guild)
        backup = await handler.save(chatlog=0)
        id = await self._create_backup(ctx.author.id, backup)

        await status.edit(**ctx.em("Successfully **created backup**.", type="success"))
        try:
            if ctx.author.is_on_mobile():
                await ctx.author.send(f"{ctx.prefix}backup load {id}")

            else:
                embed = ctx.em(
                    f"Created backup of **{ctx.guild.name}** with the Backup id `{id}`\n", type="info")["embed"]
                embed.add_field(name="Usage",
                                value=f"```{ctx.prefix}backup load {id}```\n```{ctx.prefix}backup info {id}```")
                await ctx.author.send(embed=embed)

        except:
            traceback.print_exc()
            await status.edit(
                **ctx.em("I was **unable to send you the backup-id**. Please make sure you have dm's enabled.",
                         type="error"))

    @backup.command(aliases=["l"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.bot_has_managed_top_role()
    @cmd.cooldown(1, 5 * 60, cmd.BucketType.guild)
    async def load(self, ctx, backup_id, *load_options):
        """
        Load a backup


        backup_id ::    The id of the backup or "interval" for the latest automated backup
        """
        backup_id = str(ctx.guild.id) if backup_id.lower() == "interval" else backup_id
        backup = await self._get_backup(backup_id)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        warning = await ctx.send(
            **ctx.em("Are you sure you want to load this backup? **All channels and roles will get replaced!**",
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
                "Please make sure to **click the ✅ reaction** in order to load the backup.")

        if str(reaction.emoji) != "✅":
            ctx.command.reset_cooldown(ctx)
            await warning.delete()
            return

        if len(load_options) == 0:
            options = {
                "channels": True,
                "roles": True,
                "bans": True,
                "members": True,
                "settings": True
            }

        else:
            options = {}
            for opt in load_options:
                options[opt.lower()] = True

        handler = BackupLoader(self.bot, self.bot.session, backup["backup"])
        await handler.load(ctx.guild, ctx.author, chatlog=0, **options)
        await ctx.guild.text_channels[0].send(**ctx.em("Successfully loaded backup.", type="success"))

    @backup.command(aliases=["del", "remove", "rm"])
    @cmd.cooldown(1, 5, cmd.BucketType.user)
    async def delete(self, ctx, backup_id):
        """
        Delete a backup

        backup_id::    The id of the backup
        """
        backup = await self._get_backup(backup_id)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        await self._delete_backup(backup_id)
        await ctx.send(**ctx.em("Successfully **deleted backup**.", type="success"))

    @backup.command(aliases=["i", "inf"])
    @cmd.cooldown(1, 5, cmd.BucketType.user)
    async def info(self, ctx, backup_id):
        """
        Get information about a backup

        backup_id::    The id of the backup or "interval" for the latest automated backup
        """
        backup_id = str(ctx.guild.id) if backup_id.lower() == "interval" else backup_id
        backup = await self._get_backup(backup_id)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        handler = BackupInfo(self.bot, backup["backup"])
        embed = ctx.em("")["embed"]
        embed.title = handler.name
        embed.set_thumbnail(url=handler.icon_url)
        embed.add_field(name="Creator", value=f"<@{backup['creator']}>")
        embed.add_field(name="Members", value=handler.member_count, inline=True)
        embed.add_field(name="Created At", value=helpers.datetime_to_string(
            backup["timestamp"]), inline=False
                        )
        embed.add_field(name="Channels", value=handler.channels(), inline=True)
        embed.add_field(name="Roles", value=handler.roles(), inline=True)

        await ctx.send(embed=embed)

    @backup.command(aliases=["iv", "auto"])
    @cmd.cooldown(1, 1, cmd.BucketType.guild)
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    async def interval(self, ctx, *interval):
        """
        Setup automated backups

        interval ::     The time between every backup or "off".
                        Supported units: minutes(m), hours(h), days(d), weeks(w), month(m)
                        Example: 1d 12h
        """
        if len(interval) == 0:
            interval = await ctx.db.table("intervals").get(str(ctx.guild.id)).run(ctx.db.con)
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
                value=str(interval["next"] - datetime.now(pytz.utc)).split(".")[0]
            )
            embed.add_field(
                name="Latest Backup",
                value=helpers.datetime_to_string(interval["next"] - timedelta(minutes=interval["interval"]))
            )
            embed.add_field(
                name="Next Backup",
                value=helpers.datetime_to_string(interval["next"])
            )
            await ctx.send(embed=embed)
            return

        if interval[0].lower() == "off":
            await ctx.db.table("intervals").get(str(ctx.guild.id)).delete().run(ctx.db.con)
            await ctx.send(**ctx.em("Successfully **turned off the backup** interval.", type="success"))
            return

        delta_types = {"m": 1, "h": 60, "d": 60 * 24, "w": 60 * 24 * 7}
        minutes = 0
        for part in interval:
            type = delta_types.get(part[-1], 1)
            try:
                minutes += int(part[:-1]) * type
            except ValueError:
                continue

        minutes = minutes if minutes >= min_interval else min_interval
        await ctx.db.table("intervals").insert({
            "id": str(ctx.guild.id),
            "interval": minutes,
            "next": datetime.now(pytz.utc) + timedelta(minutes=minutes),
            "chatlog": 0
        }, conflict="replace").run(ctx.db.con)

        embed = ctx.em("Successfully updated the backup interval.\n"
                       "Use `x!backup load interval` to load the latest automated backup.", type="success")["embed"]
        embed.add_field(name="Interval", value=str(timedelta(minutes=minutes)).split(".")[0])
        embed.add_field(
            name="Next Backup",
            value=helpers.datetime_to_string(datetime.now(pytz.utc) + timedelta(minutes=minutes))
        )
        await ctx.send(embed=embed)
        await self.run_backup(ctx.guild.id)

    async def run_backup(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            raise ValueError

        handler = BackupSaver(self.bot, self.bot.session, guild)
        data = await handler.save(0)
        await self._create_backup(guild.owner.id, data, id=str(guild_id))

    async def interval_loop(self):
        filter = self.bot.db.table("intervals").filter(lambda iv: iv["next"].during(
            self.bot.db.time(2000, 1, 1, 'Z'), self.bot.db.now()))

        await self.bot.wait_until_ready()
        while True:
            try:
                to_backup = await filter.run(self.bot.db.con)
                while await to_backup.fetch_next():
                    interval = await to_backup.next()
                    try:
                        await self.run_backup(int(interval["id"]))

                        next = interval["next"]
                        while next < datetime.now(pytz.utc):
                            next += timedelta(minutes=interval["interval"])

                        await self.bot.db.table("intervals").update({"id": interval["id"], "next": next}).run(
                            self.bot.db.con)
                    except:
                        traceback.print_exc()

            except:
                traceback.print_exc()

            await sleep(60)


def setup(bot):
    bot.add_cog(Backups(bot))
