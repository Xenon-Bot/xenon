import discord
import random

reason = "Part of a backup"


class BackupSaver:
    def __init__(self, bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.data = {}

    async def _save_channels(self):
        for channel in self.guild.channels:
            channel_data = {
                "name": channel.name,
                "position": channel.position,
                "category": None if channel.category is None else channel.category.id,
                "id": channel.id,
                "overwrites": [{
                    str(union.id): overwrite._values
                } for union, overwrite in channel.overwrites]
            }

            if isinstance(channel, discord.TextChannel):
                channel_data.update({
                    "type": "text",
                    "topic": channel.topic,
                    # "slowmode_delay": channel.slowmode_delay,
                    "nsfw": channel.is_nsfw(),
                    "messages": [{
                        "id": message.id,
                        "system_content": message.system_content,
                        "content": message.clean_content,
                        "author": message.author.id,
                        "pinned": message.pinned,
                        "attachments": [attach.url for attach in message.attachments],
                        "embed": [embed.to_dict() for embed in message.embeds],
                        "reactions": [
                            str(reaction.emoji.name)
                            if isinstance(reaction.emoji, discord.Emoji) else str(reaction.emoji)
                            for reaction in message.reactions
                        ],

                    } async for message in channel.history(limit=100, reverse=True)],

                    "webhooks": [{
                        "channel": webhook.channel.id,
                        "name": webhook.name,
                        "avatar": webhook.avatar_url,
                        "url": webhook.url

                    } for webhook in await channel.webhooks()]
                })

                self.data["text_channels"].append(channel_data)

            elif isinstance(channel, discord.VoiceChannel):
                channel_data.update({
                    "type": "voice",
                    "bitrate": channel.bitrate,
                    "user_limit": channel.user_limit,
                })

                self.data["voice_channels"].append(channel_data)

            if isinstance(channel, discord.CategoryChannel):
                channel_data.update({
                    "type": "category",
                })

                self.data["categories"].append(channel_data)

        self.data["text_channels"] = sorted(self.data["text_channels"], key=lambda c: c["position"])
        self.data["voice_channels"] = sorted(self.data["voice_channels"], key=lambda c: c["position"])
        self.data["categories"] = sorted(self.data["categories"], key=lambda c: c["position"])

    async def _save_roles(self):
        for role in self.guild.roles:
            if role.managed or role.is_default():
                continue

            role_data = {
                "id": role.id,
                "name": role.name,
                "permissions": role.permissions.value,
                "color": role.color.value,
                "hoist": role.hoist,
                "position": role.position,
                "mentionable": role.mentionable
            }

            self.data["roles"].append(role_data)

    async def _save_members(self):
        for member in self.guild.members:
            member_data = {
                "id": member.id,
                "name": member.name,
                "nick": member.nick,
                "roles": [role.id for role in member.roles[1:]]
            }

            self.data["members"].append(member_data)

    async def save_from_guild(self, backup_id: str, creator: discord.User):
        self.data = {
            "creator": creator.id,
            "id": self.guild.id,
            "name": self.guild.name,
            "owner": self.guild.owner.id,
            "region": str(self.guild.region),
            "afk_timeout": self.guild.afk_timeout,
            "afk_channel": None if self.guild.afk_channel is None else self.guild.afk_channel.id,
            "mfa_level": self.guild.mfa_level,
            "verification_level": str(self.guild.verification_level),
            "explicit_content_filter": str(self.guild.explicit_content_filter),
            "large": self.guild.large,

            "text_channels": [],
            "voice_channels": [],
            "categories": [],
            "roles": [],
            "members": [],
            "bans": []
        }

        await self._save_channels()
        await self._save_roles()
        await self._save_members()


class BackupLoader:
    def __init__(self, bot, data: dict):
        self.bot = bot
        self.data = data
        self.id_translator = {}

    async def _load_roles(self):
        positioner = {}
        for role in self.data["roles"]:
            matching_roles = filter(lambda r: r.name == role["name"], self.guild.roles)
            matched = False
            for match in matching_roles:
                if match.color.value == role["color"] and match.permissions.value == role["permissions"]:
                    matched = True
                    positioner[match] = role["position"]
                    self.id_translator[role["id"]] = match.id
                    break

            if not matched:
                created = await self.guild.create_role(
                    name=role["name"],
                    color=discord.Color(role["color"]),
                    permissions=discord.Permissions(role["permissions"]),
                    hoist=role["hoist"],
                    mentionable=role["mentionable"],
                    reason=reason

                )
                positioner[created] = role["position"]
                self.id_translator[role["id"]] = created.id

        for role in filter(lambda r: r not in positioner.keys(), self.guild.roles):
            if role.managed or role.is_default():
                continue

            await role.delete()

        for role, position in positioner.items():
            await role.edit(position=position)

    async def _load_channels(self):
        positioner = {}

        for category in self.data["categories"]:
            matching_categories = filter(lambda r: r.name == category["name"], self.guild.categories)
            matched = False
            for match in matching_categories:
                if None:
                    matched = True
                    positioner[match] = category["position"]
                    self.id_translator[category["id"]] = match.id
                    break

    async def load_to_guild(self, guild: discord.Guild, options: dict):
        self.guild = guild
        self.id_translator = {}
        await self._load_roles()
        await self._load_channels()


class Backup(BackupSaver, BackupLoader):
    def __init__(self, bot, data=None, guild=None, creator=None):
        self.guild = guild
        self.bot = bot
        self.data = data

        if data is not None:
            super().__init__(bot=bot, data=data)

        else:
            super().__init__(bot=bot, guild=guild)

    async def load(self):
        await super().load_to_guild(self.guild, {})

    def to_dict(self):
        return self.data

    @classmethod
    async def from_backup(cls, bot, data: dict):
        return cls(bot, data=data)

    @classmethod
    async def from_guild(cls, bot, guild: discord.Guild, creator: discord.User):
        instance = cls(bot, guild=guild, creator=discord.User)
        await instance.save_from_guild(instance._backup_id, creator)
        return instance

    @property
    def _backup_id(self):
        allowed_characters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r",
                              "s", "t", "u", "v", "w", "x", "y", "z",
                              "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

        return "".join([random.choice(allowed_characters) for i in range(16)])
