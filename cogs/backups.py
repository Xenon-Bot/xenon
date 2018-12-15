from discord.ext import commands as cmd
from discord_backups import BackupSaver, BackupLoader, BackupInfo
import string
import random
import traceback
from asyncio import TimeoutError, sleep
from datetime import datetime, timedelta
import pytz

from utils import checks, helpers


max_chatlog = 20
max_reinvite = 100


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
        chatlog = chatlog if chatlog < max_chatlog and chatlog >= 0 else max_chatlog
        status = await ctx.send(**ctx.em("**Creating backup** ... Please wait", type="working"))
        handler = BackupSaver(self.bot, self.bot.session, ctx.guild)
        backup = await handler.save(chatlog)
        id = self.random_id()
        await ctx.db.table("backups").insert({
            "id": id,
            "creator": str(ctx.author.id),
            "timestamp": datetime.now(pytz.utc),
            "backup": backup
        }).run(ctx.db.con)

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
            await status.edit(**ctx.em("I was **unable to send you the backup-id**. Please make sure you have dm's enabled.", type="error"))

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
        backup = await ctx.db.table("backups").get(backup_id).run(ctx.db.con)
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
                "bans": True,
                "members": True,
                "settings": True
            }

        else:
            options = {}
            for opt in load_options:
                options[opt.lower()] = True

        handler = BackupLoader(self.bot, self.bot.session, backup["backup"])
        await handler.load(ctx.guild, ctx.author, chatlog, **options)
        await ctx.guild.text_channels[0].send(**ctx.em("Successfully loaded backup.", type="success"))

    @backup.command(aliases=["reinv"])
    @cmd.guild_only()
    @checks.is_pro()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @cmd.cooldown(1, 3 * 60 * 60, cmd.BucketType.user)
    async def reinvite(self, ctx, backup_id, limit=max_reinvite):
        """
        Reinvite members from a backup
        Abusing this feature will result in a ban!


        backup_id ::    The id of the backup

        limit     ::    The maxmimal count of members (max. 100) (default 100)
        """
        limit = limit if limit < max_reinvite and limit >= 0 else max_reinvite
        backup = await ctx.db.table("backups").get(backup_id).run(ctx.db.con)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        warning = await ctx.send(**ctx.em(
            "Are you sure you want to reinvite the members from this backup? **That could be interpreted as massive spam!**\n\n"
            f"If the backup saved more than {limit} members, the will only load the {limit} members with the most roles.",
            type="warning"
        ))
        await warning.add_reaction("✅")
        await warning.add_reaction("❌")
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == warning.id and u.id == ctx.author.id,
                timeout=60)
        except TimeoutError:
            raise cmd.CommandError(
                "Please make sure to **click the ✅ reaction** in order to reinvite the members.")
            await warning.delete()

        if str(reaction.emoji) != "✅":
            ctx.command.reset_cooldown(ctx)
            await warning.delete()
            return

        members = backup["backup"]["members"]
        if len(members) > limit:
            members = sorted(members, key=lambda m: len(m["roles"]), reverse=True)
            members = members[:limit]

        invite = await ctx.channel.create_invite(unique=False)

        status = await ctx.send(**ctx.em("**Reinviting members** ... Please wait", type="working"))
        skipped = 0
        for member in members:
            member = await self.bot.get_user_info(int(member["id"]))
            if member is None:
                continue

            try:
                await member.send(
                    f"The user **{ctx.author}** reinvited you to the backed up guild **{backup['backup']['name']}**.\n\n"
                    f"**Invite: <{invite}>**\n\n"
                    f"If you get spammed or think someone abuses this feature, please report them here <https://discord.club/discord>!"
                )
            except:
                skipped += 1

        await status.edit(**ctx.em(
            f"Successfully **reinvited {len(members) - skipped} members**. Skipped: {skipped}",
            type="success"
        ))

    @backup.command(aliases=["del", "remove", "rm"])
    @cmd.cooldown(1, 5, cmd.BucketType.user)
    async def delete(self, ctx, backup_id):
        """
        Delete a backup

        backup_id::    The id of the backup
        """
        backup = await ctx.db.table("backups").get(backup_id).run(ctx.db.con)
        if backup is None or backup.get("creator") != str(ctx.author.id):
            raise cmd.CommandError(f"You have **no backup** with the id `{backup_id}`.")

        await ctx.db.table("backups").get(backup_id).delete().run(ctx.db.con)
        await ctx.send(**ctx.em("Successfully **deleted backup**.", type="success"))

    @backup.command(aliases=["i", "inf"])
    @cmd.cooldown(1, 5, cmd.BucketType.user)
    async def info(self, ctx, backup_id):
        """
        Get information about a backup

        backup_id::    The id of the backup
        """
        backup = await ctx.db.table("backups").get(backup_id).run(ctx.db.con)
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

        interval::     The time between every backup or "off".
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

        minutes = minutes if minutes >= 60 else 60
        await ctx.db.table("intervals").insert({
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
                        continue

                    handler = BackupSaver(self.bot, self.bot.session, guild)
                    backup = await handler.save(max_chatlog)
                    id = self.random_id()
                    await db.table("backups").insert({
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
                    await guild.owner.send(embed=embed)
            except:
                traceback.print_exc()

    async def interval_loop(self):
        db = self.bot.db
        while True:
            try:
                await sleep(60)

                await db.table("intervals").update({"remaining": db.row["remaining"] - 1}).run(db.con)
                filter = db.table("intervals").filter(
                    lambda interval: (interval["remaining"] <= 0)
                )
                to_backup = await filter.run(db.con)
                await filter.update({"remaining": db.row["interval"]}).run(db.con)
                self.to_backup += [int(iv["id"]) for iv in await helpers.async_cursor_to_list(to_backup)]
            except:
                traceback.print_exc()


def setup(bot):
    bot.add_cog(Backups(bot))
