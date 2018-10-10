import asyncio
import datetime
import traceback

import aiohttp
import discord

import statics
from cogs.utils import checks, time, file_system, oauth, formatter

cache = {}
em = formatter.embed_message


async def copy_guild(origin, target, chatlog=20):
    ids = {}

    def convert_overwrites(overwrites: list):
        ret = {}
        for union, overwrite in overwrites:
            if isinstance(union, discord.Role):
                role = target.get_role(ids.get(union.id))
                if role is not None:
                    ret[role] = overwrite

            elif isinstance(union, discord.Member):
                ret[union] = overwrite

        return ret

    for channel in target.channels:
        await channel.delete()

    for role in target.roles:
        if role.managed or role.is_default():
            continue

        await role.delete()

    for role in reversed(origin.roles):
        if role.managed:
            continue

        if role.is_default():
            created = target.default_role

        else:
            created = await target.create_role(
                name=role.name,
                hoist=role.hoist,
                mentionable=role.mentionable,
                color=role.color
            )

        await created.edit(
            permissions=role.permissions
        )
        ids[role.id] = created.id

    for category in origin.categories:
        created = await target.create_category(
            name=category.name,
            overwrites=convert_overwrites(category.overwrites),
        )
        ids[category.id] = created.id

    for channel in origin.text_channels:
        created = await target.create_text_channel(
            name=channel.name,
            overwrites=convert_overwrites(channel.overwrites),
            category=None if channel.category is None else target.get_channel(ids.get(channel.category.id))
        )
        await created.edit(
            topic=channel.topic,
            nsfw=channel.is_nsfw(),
            slowmode_delay=channel.slowmode_delay
        )
        webh = await created.create_webhook(
            name="sync"
        )
        async for message in channel.history(limit=chatlog, reverse=True):
            if message.system_content.replace(" ", "") == "" and len(message.embeds) == 0:
                continue

            await webh.send(
                username=message.author.name,
                avatar_url=message.author.avatar_url,
                content=message.system_content,
                embeds=message.embeds
            )

        await webh.delete()
        ids[channel.id] = created.id

    for vchannel in origin.voice_channels:
        created = await target.create_voice_channel(
            name=vchannel.name,
            overwrites=convert_overwrites(vchannel.overwrites),
            category=None if vchannel.category is None else target.get_channel(ids.get(vchannel.category.id))
        )
        await created.edit(
            bitrate=vchannel.bitrate,
            user_limit=vchannel.user_limit,
        )

    await target.edit(
        name=origin.name,
        region=origin.region,
        afk_channel=None if origin.afk_channel is None else target.get_channel(ids.get(origin.afk_channel.id)),
        afk_timeout=origin.afk_timeout,
        verification_level=origin.verification_level,
        system_channel=None if origin.system_channel is None else target.get_channel(ids.get(origin.system_channel.id)),
    )

    return ids


class BackupHandler:
    def __init__(self, bot):
        self.bot = bot
        self.id_translator = {}
        self.info_channel = None

    async def _load_info(self):
        self.info_channel = await self.guild.create_text_channel(name="backup_info", reason="Loaded Backup")

        await self.info_channel.send(embed=self.get_backup_info(self.data))

        await self._load_bot_invites()

    async def _load_bot_invites(self):
        if self.info_channel is None:
            return

        for raw_member in self.data["members"]:
            try:
                if not raw_member["bot"]:
                    continue

                try:
                    bot_info = await self.bot.dblpy.get_bot_info(int(raw_member["id"]))
                except:
                    continue

                invite = bot_info.get("invite") if bot_info.get(
                    "invite") is not None else f"https://discordapp.com/oauth2/authorize?client_id={raw_member['id']}&permissions=0&scope=bot"
                owners = ""
                for owner in bot_info["owners"]:
                    owners += f"<@{owner}> "

                embed = discord.Embed(title=bot_info["username"], color=statics.embed_color,
                                      description=bot_info["shortdesc"])
                embed.set_author(name="Bot Info", url=f"https://discordbots.org/bot/{raw_member['id']}")
                embed.add_field(name="Prefix", value=bot_info["prefix"])
                embed.add_field(name="Invite", value=f"[Click Here]({invite})")
                embed.add_field(name="Owners", value=owners)
                embed.add_field(name="Votes", value=bot_info["points"])
                embed.add_field(name="Library", value=bot_info["lib"])

                await self.info_channel.send(embed=embed)
            except:
                pass

    async def _rejoin(self):
        for member in self.data["members"]:
            data = await file_system.get_json_file(f"rejoin/{member['id']}")
            print("rejoin", data)
            if data is None:
                continue

            try:
                await oauth.client.request("PUT",
                                           f"https://discordapp.com/api/v6/guilds/{self.guild.id}/members/{member['id']}",
                                           access_token=data["access_token"])
            except:
                traceback.print_exc()

    async def _load_settings(self):
        await self.guild.edit(
            name=self.data["name"],
            afk_timeout=self.data["afk_timeout"],
            reason="Loaded Backup"
        )

    async def _load_roles(self):
        for role in reversed(self.data["roles"]):
            try:
                permission = discord.Permissions(role["permissions"])
                if role["default"]:
                    default_role = self.guild.default_role
                    self.id_translator[role["id"]] = default_role.id
                    await default_role.edit(
                        name=role["name"],
                        permissions=permission,
                        colour=discord.Colour.from_rgb(role["colour"][0], role["colour"][1], role["colour"][2]),
                        hoist=role["hoist"],
                        mentionable=role["mentionable"],
                        reason="Loaded Backup"
                    )
                else:
                    created_role = await self.guild.create_role(
                        name=role["name"],
                        permissions=permission,
                        colour=discord.Colour.from_rgb(role["colour"][0], role["colour"][1], role["colour"][2]),
                        hoist=role["hoist"],
                        mentionable=role["mentionable"],
                        reason="Loaded Backup"
                    )
                    self.id_translator[role["id"]] = created_role.id
            except:
                pass

    async def _load_channels(self):
        for category_dict in self.data["categories"]:
            try:
                category = await self.guild.create_category(name=category_dict["name"], reason="Loaded Backup")
                await category.edit(nsfw=category_dict["nsfw"])

                if self.options.get("roles"):
                    for overwrite_target, overwrite in category_dict["overwrites"].items():
                        for role in self.guild.roles:
                            if role.id == self.id_translator.get(overwrite_target):
                                await category.set_permissions(role, overwrite=discord.PermissionOverwrite(**overwrite))

                for channel in category_dict["channels"]:
                    try:
                        if channel["type"] == "text":
                            text_channel = await self.guild.create_text_channel(
                                name=channel["name"],
                                category=category,
                                reason="Loaded Backup"
                            )
                            await text_channel.edit(
                                topic=channel["topic"],
                                nsfw=channel["nsfw"],
                                reason="Loaded Backup"
                            )
                            for webhook in channel["webhooks"]:
                                try:
                                    async with aiohttp.ClientSession() as session:
                                        async with session.get(webhook["avatar"]) as resp:
                                            await text_channel.create_webhook(name=webhook["name"],
                                                                              avatar=await resp.read())
                                except:
                                    await text_channel.create_webhook(name=webhook["name"])

                            if self.options.get("roles"):
                                for overwrite_target, overwrite in channel["overwrites"].items():
                                    for role in self.guild.roles:
                                        if role.id == self.id_translator.get(overwrite_target):
                                            await text_channel.set_permissions(role,
                                                                               overwrite=discord.PermissionOverwrite(
                                                                                   **overwrite))

                            if channel.get("messages") is not None and self.chatlog > 0:
                                try:
                                    webh = await text_channel.create_webhook(name="backup_load_temp")
                                    try:
                                        start = len(channel["messages"]) - self.chatlog
                                        if start < 0:
                                            start = 0
                                        for message in channel["messages"][::-1][start:]:
                                            message["content"] += "\n\n" + str(*message["attachments"])

                                            try:
                                                sended = await webh.send(username=message["author"]["name"],
                                                                         avatar_url=message["author"]["avatar"],
                                                                         content=message["content"],
                                                                         embeds=[discord.Embed.from_data(embed) for
                                                                                 embed in
                                                                                 message["embeds"]])
                                            except:
                                                pass
                                    except IndexError:
                                        pass
                                    await webh.delete()
                                except:
                                    pass
                        elif channel["type"] == "voice":
                            voice_channel = await self.guild.create_voice_channel(
                                name=channel["name"],
                                category=category,
                                reason="Loaded Backup"
                            )
                            await voice_channel.edit(
                                bitrate=channel["bitrate"],
                                user_limit=channel["limit"],
                                reason="Loaded Backup"
                            )
                            if self.options.get("roles"):
                                for overwrite_id, overwrite in channel["overwrites"].items():
                                    for role in self.guild.roles:
                                        if role.id == str(self.id_translator.get(overwrite_id)):
                                            await voice_channel.set_permissions(role,
                                                                                overwrite=discord.PermissionOverwrite(
                                                                                    **overwrite))
                    except:
                        pass
            except:
                pass

    async def _load_bans(self):
        for user_id, reason in self.data["bans"].items():
            try:
                user = self.bot.get_user(int(user_id))
                if user is not None:
                    await self.guild.ban(user=user, reason=reason)
            except:
                pass

    async def _load_members(self):
        for raw_member in self.data["members"]:
            try:
                if raw_member["bot"]:
                    continue

                member = self.guild.get_member(int(raw_member["id"]))
                if member is None:
                    continue

                roles = []
                for raw_role_id in raw_member["roles"]:
                    role_id = self.id_translator.get(raw_role_id)
                    if role_id is None:
                        continue

                    fitting = list(filter(lambda r: r.id == int(role_id), self.guild.roles))
                    if len(fitting) == 0:
                        continue

                    role = fitting[0]
                    if not role.managed and not role.is_default():
                        roles.append(role)

                await member.add_roles(*roles, reason="Loaded Backup")
                await member.edit(nick=raw_member.get("nick"), reason="Loaded Backup")
            except:
                pass

    async def _clear(self):
        for channel in self.guild.channels:
            try:
                await channel.delete(reason="Loaded Backup")
            except (discord.Forbidden, discord.NotFound):
                pass
        for category in self.guild.categories:
            try:
                await category.delete(reason="Loaded Backup")
            except (discord.Forbidden, discord.NotFound):
                pass
        roles = self.guild.roles.copy()
        for role in roles:
            try:
                if role.managed or role.is_default():
                    continue

                await role.delete(reason="Loaded Backup")
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def load_command(self, ctx, data, options_input, chatlog_override=None):
        options = {"info": True, "settings": True, "roles": True, "channels": True, "bans": True, "delete": True}

        for option in options_input:
            if option.startswith("!"):
                options[option[1:]] = False
            else:
                options[option] = True

        chatlog = chatlog_override
        if chatlog is None:
            chatlog = 0
            if options.get("channels"):
                await ctx.send(**em(
                    f"Please **input** the **amount of messages** you want to load: (`0-{statics.max_chatlog}`)",
                    type="wait_for"))
                try:
                    valid_answers = [str(x) for x in range(0, statics.max_chatlog + 1)]
                    chatlog_msg = await self.bot.wait_for("message",
                                                          check=lambda
                                                              m: m.channel == ctx.channel and m.author.id == ctx.author.id and m.content in valid_answers,
                                                          timeout=30)
                    chatlog = int(chatlog_msg.content)
                except asyncio.TimeoutError:
                    ctx.command.reset_cooldown(ctx)
                    raise checks.InputTimeout

        if options.get("delete"):
            delete_sended = await ctx.send(
                **em(f"Are you sure you want to load this backup? **All channels and roles will get replaced**!\n",
                     type="warning"))
            await delete_sended.add_reaction("✅")
            await delete_sended.add_reaction("❌")
            try:
                valid_answers = ["✅", "❌"]
                delete_r, delete_u = await self.bot.wait_for("reaction_add",
                                                             check=lambda r,
                                                                          u: u.id == ctx.author.id and r.message.id == delete_sended.id and str(
                                                                 r.emoji) in valid_answers,
                                                             timeout=30)
            except asyncio.TimeoutError:
                raise checks.InputTimeout

            if str(delete_r.emoji) == "✅":
                pass
            else:
                ctx.command.reset_cooldown(ctx)
                await ctx.send(**em("Successfully **canceled** loading backup.", type="success"))
                return

        await self.load(ctx.guild, data, chatlog, **options)

    async def load(self, guild: discord.Guild, data: dict, chatlog: int, **options):
        self.id_translator = {}
        self.guild = guild
        self.data = data
        self.chatlog = chatlog
        self.options = options

        if options.get("delete"):
            try:
                await self._clear()
            except:
                pass

        if options.get("info"):
            try:
                await self._load_info()
            except:
                pass

        if options.get("settings"):
            try:
                await self._load_settings()
            except:
                pass

        if options.get("roles"):
            try:
                await self._load_roles()
            except:
                pass

        if options.get("channels"):
            try:
                await self._load_channels()
            except:
                pass

        if options.get("bans"):
            try:
                await self._load_bans()
            except:
                pass

        if options.get("rejoin"):
            try:
                await self._rejoin()
            except:
                traceback.print_exc()

        try:
            await self._load_members()
        except:
            pass

        if options.get("info"):
            invite = await guild.channels[-1].create_invite(reason="Loaded Backup")
            await self.info_channel.send(**em(f"Successfully **loaded {data['name']}**!\n"
                                              f"Invite old members: {invite.url}", type="success"))

    async def save(self, guild: discord.Guild, creator: (discord.Member, discord.User), chatlog: int = 20):
        rtn_data = {
            "name": guild.name,
            "guild_id": guild.id,
            "creator": str(creator.id),
            "timestamp": time.format_datetime(datetime.datetime.utcnow()),
            "afk_timeout": guild.afk_timeout,
            "icon": guild.icon_url_as(format="png"),
            "mfa_level": guild.mfa_level,

            "roles": [{
                "name": role.name,
                "id": str(role.id),
                "colour": role.colour.to_rgb(),
                "hoist": role.hoist,
                "position": role.position,
                "mentionable": role.mentionable,
                "default": role.is_default(),
                "permissions": role.permissions.value
            } for role in guild.roles if not role.managed],

            "members": [{
                "id": str(member.id),
                "tag": str(member).encode("utf-8").decode(),
                "nick": member.nick,
                "roles": [str(role.id) for role in member.roles],
                "bot": member.bot
            } for member in guild.members],

            "bans": {},

            "categories": []
        }

        try:
            rtn_data["bans"] = {str(ban[1].id): ban[0] for ban in await guild.bans()}
        except discord.Forbidden:
            pass

        for category in guild.categories:
            category_data = {
                "name": category.name,
                "id": str(category.id),
                "position": category.position,
                "nsfw": category.is_nsfw(),

                "overwrites": {str(overwrite[0].id): overwrite[1]._values for overwrite in category.overwrites if
                               type(overwrite[0]) == discord.Role},

                "channels": []
            }

            for channel in category.channels:
                if type(channel) == discord.TextChannel:
                    channel_data = {
                        "name": channel.name,
                        "id": str(channel.id),
                        "topic": channel.topic,
                        "nsfw": channel.is_nsfw(),
                        "type": "text",

                        "overwrites": {str(overwrite[0].id): overwrite[1]._values for overwrite in channel.overwrites if
                                       type(overwrite[0]) == discord.Role},

                        "webhooks": [],
                        "messages": []
                    }

                    try:
                        channel_data["webhooks"] = [{
                            "name": webhook.name,
                            "avatar": webhook.avatar_url
                        } for webhook in await channel.webhooks()]
                    except discord.Forbidden:
                        pass

                    try:
                        async for message in channel.history(limit=chatlog):
                            if message.clean_content.replace(" ", "") != "" or len(message.embeds) != 0:
                                channel_data["messages"].append(
                                    {
                                        "content": message.system_content,
                                        "embeds": [embed.to_dict() for embed in message.embeds],
                                        "attachments": [attachment.url for attachment in message.attachments],
                                        "timestamp": message.created_at.strftime('%Y/%b/%d, %H:%M'),
                                        "pinned": message.pinned,

                                        "reactions": [str(reaction.emoji) for reaction in message.reactions if
                                                      type(reaction.emoji) == str],

                                        "author": {
                                            "name": message.author.name,
                                            "id": str(message.author.id),
                                            "avatar": message.author.avatar_url,
                                        }
                                    }
                                )
                    except discord.Forbidden:
                        pass

                    category_data["channels"].append(channel_data)

                elif type(channel) == discord.VoiceChannel:
                    channel_data = {
                        "name": channel.name,
                        "bitrate": channel.bitrate,
                        "limit": channel.user_limit,
                        "type": "voice",

                        "overwrites": {str(overwrite[0].id): overwrite[1]._values for overwrite in channel.overwrites if
                                       type(overwrite[0]) == discord.Role}
                    }

                    category_data["channels"].append(channel_data)

            rtn_data["categories"].append(category_data)

        return rtn_data

    def get_backup_info(self, data: dict):
        channel_tree = "```"
        roles = "```"
        for category in data["categories"]:
            channel_tree += category["name"] + "\n"
            for channel in category["channels"]:
                if channel["type"] == "voice":
                    channel_tree += "    ~ " + channel["name"] + "\n"
                else:
                    channel_tree += "    # " + channel["name"] + "\n"

        channel_tree += "```"

        for role in data["roles"]:
            roles += role["name"] + "\n"

        roles += "```"

        embed = discord.Embed(color=statics.embed_color, title=data["name"], description=data.get("description"))
        embed.add_field(name="Creator", value=f"<@{data['creator']}>")
        if len(data["members"]) > 0:
            embed.add_field(name="Members", value=str(len(data["members"])))
        embed.add_field(name="Timestamp", value=data["timestamp"], inline=False)
        embed.add_field(name="Channels", value=channel_tree[:999])
        embed.add_field(name="Roles", value=roles[:999])

        return embed
