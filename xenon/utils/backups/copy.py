import discord

from . import utils


async def copy_guild(origin, target, chatlog=20):
    ids = {}

    def convert_overwrites(overwrites):
        ret = {}
        for union, overwrite in overwrites.items():
            try:
                if isinstance(union, discord.Role):
                    role = target.get_role(ids.get(union.id))
                    if role is not None:
                        ret[role] = overwrite

                elif isinstance(union, discord.Member):
                    ret[union] = overwrite
            except:
                continue

        return ret

    for channel in target.channels:
        try:
            await channel.delete()
        except:
            pass

    for role in target.roles:
        try:
            if role.managed or role.is_default():
                continue

            await role.delete()
        except:
            pass

    for role in reversed(origin.roles):
        try:
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
        except:
            pass

    for category in origin.categories:
        try:
            created = await target.create_category(
                name=category.name,
                overwrites=convert_overwrites(category.overwrites),
            )
            ids[category.id] = created.id
        except:
            pass

    for channel in origin.text_channels:
        try:
            created = await target.create_text_channel(
                name=channel.name,
                overwrites=convert_overwrites(channel.overwrites),
                category=None if channel.category is None else target.get_channel(
                    ids.get(channel.category.id))
            )
            await created.edit(
                topic=channel.topic,
                nsfw=channel.is_nsfw(),
                slowmode_delay=channel.slowmode_delay
            )
            webh = await created.create_webhook(
                name="sync"
            )
            for message in reversed(await channel.history(limit=chatlog).flatten()):
                if message.system_content.replace(" ", "") == "" and len(message.embeds) == 0:
                    continue

                try:
                    await webh.send(
                        username=message.author.name,
                        avatar_url=message.author.avatar_url,
                        content=utils.clean_content(
                            message.system_content) + "\n".join([attach.url for attach in message.attachments]),
                        embeds=message.embeds
                    )
                except:
                    pass

            await webh.delete()
            ids[channel.id] = created.id
        except:
            pass

    for vchannel in origin.voice_channels:
        try:
            created = await target.create_voice_channel(
                name=vchannel.name,
                overwrites=convert_overwrites(vchannel.overwrites),
                category=None if vchannel.category is None else target.get_channel(
                    ids.get(vchannel.category.id))
            )
            await created.edit(
                bitrate=vchannel.bitrate,
                user_limit=vchannel.user_limit,
            )
        except:
            pass

    for reason, user in await origin.bans():
        try:
            await target.ban(user=user, reason=reason)
        except:
            pass

    for tmember in target.members:
        omember = origin.get_member(tmember.id)
        if omember is None:
            continue

        try:
            await tmember.add_roles(*[discord.Object(ids.get(role.id)) for role in omember.roles if role.id in ids and not role.is_default()])
        except:
            pass

    await target.edit(
        name=origin.name,
        region=origin.region,
        afk_channel=None if origin.afk_channel is None else target.get_channel(
            ids.get(origin.afk_channel.id)),
        afk_timeout=origin.afk_timeout,
        verification_level=origin.verification_level,
        system_channel=None if origin.system_channel is None else target.get_channel(
            ids.get(origin.system_channel.id)),
    )

    return ids
