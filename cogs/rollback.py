import time
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from cogs.utils import formatter

em = formatter.embed_message


class Rollback:
    def __init__(self, bot):
        self.bot = bot
        self.rollbacks = {}
        self.id_translator = {}

    @commands.group(invoke_without_command=True, hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(administrator=True)
    async def rollback(self, ctx, minutes: int):
        events = self.rollbacks.get(str(ctx.guild.id))
        if events is None:
            raise commands.BadArgument("")

        in_timespan = list(
            filter(lambda e: e["timestamp"] - (time.mktime(datetime.utcnow().timetuple()) - minutes * 60) > 0,
                   events)
        )

        functions = {
            "edit": self._edit_guild
        }
        print(events)
        print(in_timespan)
        for event in reversed(in_timespan):
            await functions[event["reverse"]](ctx.guild, **event["content"])

        self.rollbacks[str(ctx.guild.id)] = [event for event in events if event not in in_timespan]
        await ctx.send(**em(f"Successfully reversed **{len(in_timespan)}** events", type="success"))

    @rollback.command(aliases=["enable"])
    @commands.has_permissions(administrator=True)
    async def activate(self, ctx):
        self.rollbacks[str(ctx.guild.id)] = []
        await ctx.send(**em("Successfully **enabled rollback** for this guild.", type="success"))

    @rollback.command(aliases=["disable"])
    @commands.has_permissions(administrator=True)
    async def deactivate(self, ctx):
        self.rollbacks.pop(str(ctx.guild.id), None)
        await ctx.send(**em("Successfully **disabled rollback** for this guild.", type="success"))

    def _is_rollback_enabled(self, guild):
        return str(guild.id) in self.rollbacks.keys()

    def _add_event(self, guild, event):
        if not self._is_rollback_enabled(guild):
            return

        data = {
            "timestamp": time.mktime(datetime.utcnow().timetuple())
        }
        data.update(event)
        self.rollbacks[str(guild.id)].append(data)

    async def on_guild_channel_delete(self, channel):
        if isinstance(channel, discord.TextChannel):
            self._add_event(channel.guild, {
                "event": "channel_delete",
                "reverse": "create_text_channel",
                "content": {
                    "id": channel.id
                }
            })

        elif isinstance(channel, discord.VoiceChannel):
            self._add_event(channel.guild, {
                "event": "channel_delete",
                "reverse": "create_voice_channel",
                "content": {
                    "id": channel.id
                }
            })

        else:
            self._add_event(channel.guild, {
                "event": "channel_delete",
                "reverse": "create_category",
                "content": {
                    "id": channel.id
                }
            })

    async def on_guild_channel_create(self, channel):
        self._add_event(channel.guild, {
            "event": "channel_create",
            "reverse": "delete_channel",
            "content": {
                "id": channel.id
            }
        })

    async def on_guild_channel_update(self, before, after):
        pass

    async def on_webhooks_update(self, channel):
        pass

    async def on_guild_update(self, before, after):
        self._add_event(after, {
            "event": "guild_update",
            "reverse": "edit",
            "content": {
                "name": before.name,
                "region": before.region.value,
                "afk_channel": None if before.afk_channel is None else before.afk_channel.id,
                "afk_timeout": before.afk_timeout,
                "verification_level": before.verification_level.value,
                "system_channel": None if before.system_channel is None else before.system_channel.id
            }
        })

    async def _edit_guild(self, guild, **content):
        await guild.edit(
            name=content["name"],
            region=discord.VoiceRegion(content["region"]),
            afk_channel=guild.get_channel(self.id_translator.get(content["afk_channel"]) or content["afk_channel"]),
            afk_timeout=content["afk_timeout"],
            verification_level=discord.VerificationLevel(content["verification_level"]),
            system_channel=guild.get_channel(self.id_translator.get(content["system_channel"]) or content["system_channel"])
        )

    async def on_guild_role_create(self, role):
        self._add_event(role.guild, {
            "event": "guild_role_update",
            "reverse": f"delete_role",
            "content": {
                "id": role.id
            }
        })

    async def on_guild_role_delete(self, role):
        self._add_event(role.guild, {
            "event": "guild_role_delete",
            "reverse": f"create_role",
            "content": {
                "id": role.id,
                "name": role.name,
                "color": role.color.value,
                "permissions": role.permissions.value,
                "hoist": role.hoist,
                "mentionable": role.mentionable
            }
        })

    async def on_guild_role_update(self, before, after):
        self._add_event(after.guild, {
            "event": "guild_role_update",
            "reverse": f"edit_role",
            "content": {
                "name": after.name,
                "color": after.color.value,
                "permissions": after.permissions.value,
                "hoist": after.hoist,
                "mentionable": after.mentionable
            }
        })

    async def on_member_ban(self, guild, user):
        self._add_event(guild, {
            "event": "member_ban",
            "reverse": "unban",
            "content": {
                "id": user.id
            }
        })

    async def on_member_unban(self, guild, user):
        self._add_event(guild, {
            "event": "member_unban",
            "reverse": "ban",
            "content": {
                "id": user.id
            }
        })


def setup(bot):
    bot.add_cog(Rollback(bot))
