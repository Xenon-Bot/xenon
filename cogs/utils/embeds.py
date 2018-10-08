import discord

import statics


error_icon = "http://discord.club/images/error.png"
input_icon = "https://image.ibb.co/iLBP9o/devices_18_512.png"
warning_icon = "http://discord.club/images/warning.png"
success_icon = "http://discord.club/images/success.png"
working_icon = "https://cdn.discordapp.com/emojis/424900448663633920.gif"
info_icon = "http://discord.club/images/info.png"


class Embeds:
    def unexpected_error(self, code):
        embed = discord.Embed(color=statics.embed_color,
                              description=f"Sorry, something went wrong. Please report this on the [support discord]({statics.support_invite})!")
        embed.add_field(name="Code", value=f"```Python\n{code}```")
        embed.set_author(name="Unexpected Error", icon_url=error_icon)

        return embed

    def error(self, message):
        embed = discord.Embed(color=statics.embed_color, description=message)
        embed.set_author(name="Error", icon_url=error_icon)

        return embed

    def warning(self, message):
        embed = discord.Embed(color=statics.embed_color, description=message)
        embed.set_author(name="Warning", icon_url=warning_icon)

        return embed

    def input(self, message):
        embed = discord.Embed(color=statics.embed_color, description=message)
        embed.set_author(name="Waiting for input", icon_url=info_icon)

        return embed

    def success(self, message):
        embed = discord.Embed(color=statics.embed_color, description=message)
        embed.set_author(name="Success", icon_url=success_icon)

        return embed

    def working(self, message):
        embed = discord.Embed(color=statics.embed_color, description=message)
        embed.set_author(name="Working ...", icon_url=working_icon)

        return embed

    def info(self, message):
        embed = discord.Embed(color=statics.embed_color, description=message)
        embed.set_author(name="Info", icon_url=info_icon)

        return embed


def setup(bot):
    bot.embeds = Embeds()