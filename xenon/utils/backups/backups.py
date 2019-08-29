import discord
import traceback

from . import utils


class BackupSaver():
    def __init__(self, bot, session, guild):
        self.session = session
        self.bot = bot
        self.guild = guild
        self.data = {}

    def _overwrites_to_json(self, overwrites):
        try:
            return {str(target.id): overwrite._values for target, overwrite in overwrites.items()}
        except:
            return {}

    async def _save_channels(self):
        for category in self.guild.categories:
            try:
                self.data["categories"].append({
                    "name": category.name,
                    "position": category.position,
                    "category": None if category.category is None else str(category.category.id),
                    "id": str(category.id),
                    "overwrites": self._overwrites_to_json(category.overwrites)
                })
            except:
                traceback.print_exc()

        for tchannel in self.guild.text_channels:
            try:
                self.data["text_channels"].append({
                    "name": tchannel.name,
                    "position": tchannel.position,
                    "category": None if tchannel.category is None else str(tchannel.category.id),
                    "id": str(tchannel.id),
                    "overwrites": self._overwrites_to_json(tchannel.overwrites),
                    "topic": tchannel.topic,
                    "slowmode_delay": tchannel.slowmode_delay,
                    "nsfw": tchannel.is_nsfw(),
                    "messages": [{
                        "id": str(message.id),
                        "content": message.system_content,
                        "author": {
                            "id": str(message.author.id),
                            "name": message.author.name,
                            "discriminator": message.author.discriminator,
                            "avatar_url": str(message.author.avatar_url)
                        },
                        "pinned": message.pinned,
                        "attachments": [attach.url for attach in message.attachments],
                        "embeds": [embed.to_dict() for embed in message.embeds],
                        "reactions": [
                            str(reaction.emoji.name)
                            if isinstance(reaction.emoji, discord.Emoji) else str(reaction.emoji)
                            for reaction in message.reactions
                        ],

                    } for message in reversed(await tchannel.history(limit=self.chatlog).flatten())],

                    "webhooks": [{
                        "channel": str(webhook.channel.id),
                        "name": webhook.name,
                        "avatar": str(webhook.avatar_url),
                        "url": webhook.url

                    } for webhook in await tchannel.webhooks()]
                })
            except:
                traceback.print_exc()

        for vchannel in self.guild.voice_channels:
            try:
                self.data["voice_channels"].append({
                    "name": vchannel.name,
                    "position": vchannel.position,
                    "category": None if vchannel.category is None else str(vchannel.category.id),
                    "id": str(vchannel.id),
                    "overwrites": self._overwrites_to_json(vchannel.overwrites),
                    "bitrate": vchannel.bitrate,
                    "user_limit": vchannel.user_limit,
                })
            except:
                traceback.print_exc()

    async def _save_roles(self):
        for role in self.guild.roles:
            try:
                if role.managed:
                    continue

                self.data["roles"].append({
                    "id": str(role.id),
                    "default": role.is_default(),
                    "name": role.name,
                    "permissions": role.permissions.value,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "position": role.position,
                    "mentionable": role.mentionable
                })
            except:
                traceback.print_exc()

    async def _save_members(self):
        for member in sorted(self.guild.members, key=lambda m: len(m.roles), reverse=True)[:1000]:
            try:
                self.data["members"].append({
                    "id": str(member.id),
                    "name": member.name,
                    "discriminator": member.discriminator,
                    "nick": member.nick,
                    "roles": [str(role.id) for role in member.roles[1:] if not role.managed]
                })
            except:
                traceback.print_exc()

    async def _save_bans(self):
        for reason, user in await self.guild.bans():
            try:
                self.data["bans"].append({
                    "user": str(user.id),
                    "reason": reason
                })
            except:
                # User probably doesn't exist anymore
                traceback.print_exc()

    async def save(self, chatlog=20):
        self.chatlog = chatlog
        self.data = {
            "id": str(self.guild.id),
            "name": self.guild.name,
            "icon_url": str(self.guild.icon_url),
            "owner": str(self.guild.owner_id),
            "member_count": self.guild.member_count,
            "region": str(self.guild.region),
            "system_channel": str(self.guild.system_channel),
            "afk_timeout": self.guild.afk_timeout,
            "afk_channel": None if self.guild.afk_channel is None else str(self.guild.afk_channel.id),
            "mfa_level": self.guild.mfa_level,
            "verification_level": str(self.guild.verification_level),
            "explicit_content_filter": str(self.guild.explicit_content_filter),
            "large": self.guild.large,

            "text_channels": [],
            "voice_channels": [],
            "categories": [],
            "roles": [],
            "members": [],
            "bans": [],
        }

        execution_order = [self._save_roles, self._save_channels, self._save_members, self._save_bans]

        for method in execution_order:
            try:
                await method()
            except:
                traceback.print_exc()

        return self.data

    def __dict__(self):
        return self.data


class BackupLoader:
    def __init__(self, bot, session, data):
        self.session = session
        self.data = data
        self.bot = bot
        self.id_translator = {}
        self.options = {"settings": True, "channels": True, "roles": True}

    def _overwrites_from_json(self, json):
        overwrites = {}
        for union_id, overwrite in json.items():
            union = self.guild.get_member(int(union_id))
            if union is None:
                roles = list(
                    filter(lambda r: r.id == self.id_translator.get(union_id), self.guild.roles))
                if len(roles) == 0:
                    continue

                union = roles[0]

            overwrites[union] = discord.PermissionOverwrite(**overwrite)

        return overwrites

    async def _prepare_guild(self):
        if self.options.get("roles"):
            for role in self.guild.roles:
                if not role.managed and not role.is_default():
                    try:
                        await role.delete(reason=self.reason)
                    except:
                        traceback.print_exc()

        if self.options.get("channels"):
            for channel in self.guild.channels:
                try:
                    await channel.delete(reason=self.reason)
                except:
                    traceback.print_exc()

    async def _load_settings(self):
        await self.guild.edit(
            name=self.data["name"],
            region=discord.VoiceRegion(self.data["region"]),
            afk_channel=self.guild.get_channel(self.id_translator.get(self.data["afk_channel"])),
            afk_timeout=self.data["afk_timeout"],
            # verification_level=discord.VerificationLevel(self.data["verification_level"]),
            system_channel=self.guild.get_channel(
                self.id_translator.get(self.data["system_channel"]))
        )

    async def _load_roles(self):
        for role in reversed(self.data["roles"]):
            try:
                if role["default"]:
                    await self.guild.default_role.edit(
                        permissions=discord.Permissions(role["permissions"])
                    )
                    created = self.guild.default_role
                else:
                    created = await self.guild.create_role(
                        name=role["name"],
                        hoist=role["hoist"],
                        mentionable=role["mentionable"],
                        color=discord.Color(role["color"]),
                        permissions=discord.Permissions(role["permissions"])
                    )

                self.id_translator[role["id"]] = created.id
            except:
                traceback.print_exc()

    async def _load_categories(self):
        for category in self.data["categories"]:
            try:
                created = await self.guild.create_category_channel(
                    name=category["name"],
                    overwrites=self._overwrites_from_json(category["overwrites"])
                )
                self.id_translator[category["id"]] = created.id
            except:
                traceback.print_exc()

    async def _load_text_channels(self):
        for tchannel in self.data["text_channels"]:
            try:
                created = await self.guild.create_text_channel(
                    name=tchannel["name"],
                    overwrites=self._overwrites_from_json(tchannel["overwrites"]),
                    category=discord.Object(self.id_translator.get(tchannel["category"]))
                )
                await created.edit(
                    topic=tchannel["topic"],
                    nsfw=tchannel["nsfw"],
                )

                if self.chatlog != 0:
                    webh = await created.create_webhook(name="chatlog")
                    for message in tchannel["messages"][-self.chatlog:]:
                        attachments = []
                        for attachment in message["attachments"]:
                            emb = discord.Embed()
                            emb.set_image(url=attachment)
                            attachments.append(emb)

                        try:
                            await webh.send(
                                username=message["author"]["name"],
                                avatar_url=message["author"]["avatar_url"],
                                content=utils.clean_content(message["content"]),
                                embeds=[discord.Embed.from_dict(embed)
                                        for embed in message["embeds"]] + attachments
                            )
                        except:
                            # Content and embeds are probably empty
                            traceback.print_exc()

                    await webh.delete()

                self.id_translator[tchannel["id"]] = created.id
            except:
                traceback.print_exc()

    async def _load_voice_channels(self):
        for vchannel in self.data["voice_channels"]:
            try:
                created = await self.guild.create_voice_channel(
                    name=vchannel["name"],
                    overwrites=self._overwrites_from_json(vchannel["overwrites"]),
                    category=discord.Object(self.id_translator.get(vchannel["category"]))
                )
                await created.edit(
                    bitrate=vchannel["bitrate"],
                    user_limit=vchannel["user_limit"]
                )
                self.id_translator[vchannel["id"]] = created.id
            except:
                traceback.print_exc()

    async def _load_channels(self):
        await self._load_categories()
        await self._load_text_channels()
        await self._load_voice_channels()

    async def _load_bans(self):
        for ban in self.data["bans"]:
            try:
                await self.guild.ban(user=discord.Object(int(ban["user"])), reason=ban["reason"])
            except:
                # User probably doesn't exist anymore
                traceback.print_exc()

    async def _load_member(self):
        for member in self.guild.members:
            try:
                fits = list(filter(lambda m: m["id"] == str(member.id), self.data["members"]))
                if len(fits) == 0:
                    continue

                current_roles = [r.id for r in member.roles]
                roles = [
                    discord.Object(self.id_translator.get(role))
                    for role in fits[0]["roles"]
                    if role in self.id_translator and role not in current_roles
                ]

                try:
                    await member.edit(
                        nick=fits[0].get("nick"),
                        roles=member.roles + roles,
                        reason=self.reason
                    )
                except discord.Forbidden:
                    await member.add_roles(*roles)

            except:
                traceback.print_exc()

    async def load(self, guild, loader: discord.User, chatlog, **options):
        self.guild = guild
        self.chatlog = chatlog
        if len(options) != 0:
            self.options = options

        self.loader = loader
        self.reason = f"Backup loaded by {loader}"

        await self._prepare_guild()
        if self.options.get("roles"):
            try:
                await self._load_roles()
            except:
                traceback.print_exc()

        if self.options.get("channels"):
            try:
                await self._load_channels()
            except:
                traceback.print_exc()

        if self.options.get("settings"):
            try:
                await self._load_settings()
            except:
                traceback.print_exc()

        if self.options.get("bans"):
            try:
                await self._load_bans()
            except:
                traceback.print_exc()

        if self.options.get("members"):
            try:
                await self._load_member()
            except:
                traceback.print_exc()


class BackupInfo():
    def __init__(self, bot, data):
        self.bot = bot
        self.data = data

    @property
    def icon_url(self):
        return self.data["icon_url"]

    @property
    def name(self):
        return self.data["name"]

    def channels(self, limit=1000):
        ret = "```"
        for channel in self.data["text_channels"]:
            if channel.get("category") is None:
                ret += "\n#\u200a" + channel["name"]

        for channel in self.data["voice_channels"]:
            if channel.get("category") is None:
                ret += "\n \u200a" + channel["name"]

        ret += "\n"
        for category in self.data["categories"]:
            ret += "\n⯆\u200a" + category["name"]
            for channel in self.data["text_channels"]:
                if channel.get("category") == category["id"]:
                    ret += "\n  #\u200a" + channel["name"]

            for channel in self.data["voice_channels"]:
                if channel.get("category") == category["id"]:
                    ret += "\n   \u200a" + channel["name"]

            ret += "\n"

        return ret[:limit - 10] + "```"

    def roles(self, limit=1000):
        ret = "```"
        for role in reversed(self.data["roles"]):
            ret += "\n" + role["name"]

        return ret[:limit - 10] + "```"

    @property
    def member_count(self):
        return self.data["member_count"]

    @property
    def chatlog(self):
        max_messages = 0
        for channel in self.data["text_channels"]:
            if len(channel["messages"]) > max_messages:
                max_messages = len(channel["messages"])

        return max_messages
