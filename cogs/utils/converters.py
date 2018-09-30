from discord.ext import commands


class Options(commands.Converter):
    async def convert(self, ctx, args):
        options = {}
        for arg in args:
            if arg.startswith("--"):
                options[arg[2:]] = True

            elif arg.startswith("-!"):
                options[arg[2:]] = False

        return options