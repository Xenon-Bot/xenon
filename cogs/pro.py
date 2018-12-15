from discord.ext import commands as cmd
from discord_backups import copy_guild
import discord

from utils import checks, helpers
from cogs import backups


class Pro:
    def __init__(self, bot):
        self.bot = bot

    @cmd.command()
    async def pro(self, ctx):
        """Shows information about Xenon Pro"""
        await ctx.send(**ctx.em(
            "**Xenon Pro** is the **paid version** of xenon. It includes some **exclusive features**.\n"
            "You can buy it [here](https://donatebot.io/checkout/410488579140354049).\n\n"
            "You can find **more information** about the subscription and a **detailed list of perks** [here](https://docs.discord.club/xenon/how-to/xenon-pro).",
            type="info"
        ))
        await ctx.invoke(self.bot.get_command("help"), "Pro")

    @cmd.command(aliases=["cp"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.is_pro()
    @checks.bot_has_managed_top_role()
    @cmd.cooldown(1, 5 * 60, cmd.BucketType.guild)
    async def copy(self, ctx, guild_id: int, chatlog: int = backups.max_chatlog):
        """
        Copy all channels and roles from another guild to this guild


        guild_id ::     The id of the guild

        chatlog  ::     The count of messages to load per channel (max. 20) (default 20)
        """
        chatlog = chatlog if chatlog < backups.max_chatlog and chatlog >= 0 else backups.max_chatlog
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            raise cmd.CommandError(f"There is **no guild with the id** `{guild_id}`.")

        if guild.get_member(ctx.author.id) is None or not guild.get_member(ctx.author.id).guild_permissions.administrator:
            raise cmd.MissingPermissions([f"administrator` on the guild `{guild.name}"])

        if not guild.me.guild_permissions.administrator:
            raise cmd.BotMissingPermissions([f"administrator` on the guild `{guild.name}"])

        warning = await ctx.send(**ctx.em("Are you sure you want to copy that guild? **All channels and roles will get replaced!**", type="warning"))
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

        await copy_guild(guild, ctx.guild, chatlog)
        await ctx.guild.text_channels[0].send(**ctx.em("Successfully copied guild.", type="success"))

    @cmd.group(invoke_without_command=True, aliases=["unsync"])
    async def sync(self, ctx):
        """
        Sync messages, channel & bans from one to another server

        The sync command works only in one direction, but you can run the command in both guilds / channel to sync it in both directions.
        """
        await ctx.invoke(self.bot.get_command("help"), "sync")

    @sync.command()
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.is_pro()
    async def bans(self, ctx, guild_id: int):
        """
        Copy all bans from another guild to this guild and keep them up to date


        guild_id ::     The id of the guild
        """
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            raise cmd.CommandError(f"There is **no guild with the id** `{guild_id}`.")

        if guild.get_member(ctx.author.id) is None or not guild.get_member(ctx.author.id).guild_permissions.administrator:
            raise cmd.MissingPermissions([f"administrator` on the guild `{guild.name}"])

        if not guild.me.guild_permissions.administrator:
            raise cmd.BotMissingPermissions([f"administrator` on the guild `{guild.name}"])

        current = await ctx.db.table("syncs").get(f"{guild.id}{ctx.guild.id}").run(ctx.db.con)
        types = []
        if current is not None:
            types = current.get("types", [])

        if "bans" not in types:
            types.append("bans")
            await ctx.send(**ctx.em(f"Successfully **enabled ban sync** from **{guild.name}** to **{ctx.guild.name}**.", type="success"))
            for reason, user in await guild.bans():
                try:
                    await ctx.guild.ban(user, reason=reason)
                except:
                    pass

        else:
            types.remove("bans")
            await ctx.send(**ctx.em(f"Successfully **disabled ban sync** from **{guild.name}** to **{ctx.guild.name}**.", type="success"))

        await ctx.db.table("syncs").insert({
            "id": f"{guild.id}{ctx.guild.id}",
            "types": types,
            "origin": str(guild.id),
            "target": str(ctx.guild.id)
        }, conflict="update").run(ctx.db.con)

    async def on_member_ban(self, guild, user):
        syncs = await self.bot.db.table("syncs").get_all(str(guild.id), index="origin").filter(lambda s: s["types"].contains("bans")).run(self.bot.db.con)
        while await syncs.fetch_next():
            sync = await syncs.next()
            target = self.bot.get_guild(sync.get("target"))
            if target is None:
                continue

            try:
                await target.ban(user, reason=f"Banned on {sync.get('origin')}")

            except:
                pass

    async def on_member_unban(self, guild, user):
        syncs = await self.bot.db.table("syncs").get_all(str(guild.id), index="origin").filter(lambda s: s["types"].contains("bans")).run(self.bot.db.con)
        while await syncs.fetch_next():
            sync = await syncs.next()
            target = self.bot.get_guild(int(sync["target"]))
            if target is None:
                continue

            try:
                await target.unban(user, reason=f"Unbanned on {sync['origin']}")

            except:
                pass

    @sync.command(aliases=["channel"])
    @cmd.guild_only()
    @cmd.has_permissions(administrator=True)
    @cmd.bot_has_permissions(administrator=True)
    @checks.is_pro()
    async def messages(self, ctx, channel_id: int):
        """
        Synchronize all new messages from another channel to this channel


        channel_id ::     The id of the channel
        """
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            raise cmd.CommandError(f"There is **no channel with the id** `{channel_id}`.")

        if channel.id == ctx.channel.id:
            raise cmd.CommandError(f"**No lol.**")

        if channel.guild.get_member(ctx.author.id) is None or not channel.permissions_for(channel.guild.get_member(ctx.author.id)).administrator:
            raise cmd.MissingPermissions([f"administrator` in the channel `{channel.name}"])

        if not channel.guild.me.guild_permissions.administrator:
            raise cmd.BotMissingPermissions([f"administrator` in the channel `{channel.name}"])

        current = await ctx.db.table("syncs").get(f"{channel.id}{ctx.channel.id}").run(ctx.db.con)
        types = []
        if current is not None:
            types = current.get("types", [])

        if "messages" not in types:
            types.append("messages")
            await ctx.send(**ctx.em(f"Successfully **enabled message sync** from **<#{channel.id}> to <#{ctx.channel.id}>**.", type="success"))

        else:
            types.remove("messages")
            await ctx.send(**ctx.em(f"Successfully **disabled message sync** from **<#{channel.id}> to <#{ctx.channel.id}>**.", type="success"))

        await ctx.db.table("syncs").insert({
            "id": f"{channel.id}{ctx.channel.id}",
            "types": types,
            "origin": str(channel.id),
            "target": str(ctx.channel.id)
        }, conflict="update").run(ctx.db.con)

    async def on_message(self, msg):
        if msg.author.discriminator == "0000":
            return

        wait_for = []
        syncs = await self.bot.db.table("syncs").get_all(str(msg.channel.id), index="origin").filter(lambda s: s["types"].contains("messages")).run(self.bot.db.con)
        while await syncs.fetch_next():
            sync = await syncs.next()
            target = self.bot.get_channel(int(sync["target"]))
            if target is None:
                continue

            webhooks = await target.webhooks()
            if len(webhooks) == 0:
                webhook = await target.create_webhook(name="message sync")

            else:
                webhook = webhooks[0]

            embeds = msg.embeds
            for attachment in msg.attachments:
                embed = discord.Embed()
                embed.set_image(url=attachment.url)
                embeds.append(embed)

            wait_for.append(await webhook.send(username=msg.author.name, avatar_url=msg.author.avatar_url, content=helpers.clean_content(msg.content), embeds=embeds))


def setup(bot):
    bot.add_cog(Pro(bot))
