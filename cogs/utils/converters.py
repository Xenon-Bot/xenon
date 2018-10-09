from discord.ext import commands
import json
import traceback


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

        raise commands.BadArgument("Nothing Found")


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


class JsonFileContent(commands.Converter):
    def __init__(self, base_path):
        self.base_path = base_path

    async def convert(self, ctx, argument):
        try:
            with open(self.base_path + argument + ".json", "r") as f:
                content = json.load(f)
                return content
        except:
            return None