from discord.ext import commands
import discord


class AllInOneConverter(commands.Converter):
    async def convert(self, ctx, argument):
        converters = [commands.MemberConverter(), commands.TextChannelConverter(), commands.RoleConverter(), commands.UserConverter()]
        if argument == "everyone":
            argument = "@everyone"

        for converter in converters:
            try:
                result = await converter.convert(ctx, argument)
                return result
            except:
                pass

        raise commands.BadArgument(message="Nothing Found")


class MemberUserConvert(commands.Converter):
    async def convert(self, ctx, argument):
        converters = [commands.MemberConverter(), commands.UserConverter()]
        if argument == "everyone":
            argument = "@everyone"

        for converter in converters:
            try:
                result = await converter.convert(ctx, argument)
                return result
            except:
                pass

        raise commands.BadArgument