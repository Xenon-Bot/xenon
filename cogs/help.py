import itertools
import inspect
from discord.ext import commands
import discord
import re

import statics


_mentions_transforms = {
    '@everyone': '@\u200beveryone',
    '@here': '@\u200bhere'
}
_mention_pattern = re.compile('|'.join(_mentions_transforms.keys()))


class HelpFormatter(commands.HelpFormatter):
    def __init__(self, show_hidden=False, show_check_failure=True, width=80):
        super().__init__(show_hidden, show_check_failure, width)

    def _get_subcommands(self, max_width, commands):
        result = ""
        for name, command in commands:
            if name in command.aliases:
                continue

            entry = '**{0:<{width}}** {1}'.format(name, command.short_doc, width=max_width)
            shortened = self.shorten(entry)
            result += shortened + "\n"

        return result

    def _signature(self, cmd):
        """Default signature function from the commands.Command class, but ignoring aliases."""
        result = []
        parent = cmd.full_parent_name

        name = cmd.name if not parent else parent + ' ' + cmd.name
        result.append(name)

        if cmd.usage:
            result.append(cmd.usage)
            return ' '.join(result)

        params = cmd.clean_params
        if not params:
            return ' '.join(result)

        for name, param in params.items():
            if param.default is not param.empty:
                # We don't want None or '' to trigger the [name=value] case and instead it should
                # do [name] since [name=None] or [name=] are not exactly useful for the user.
                should_print = param.default if isinstance(param.default, str) else param.default is not None
                if should_print:
                    result.append('[%s=%s]' % (name, param.default))
                else:
                    result.append('[%s]' % name)
            elif param.kind == param.VAR_POSITIONAL:
                result.append('[%s...]' % name)
            else:
                result.append('<%s>' % name)

        return ' '.join(result)

    def get_command_signature(self):
        """Retrieves the signature portion of the help page."""
        prefix = self.clean_prefix
        cmd = self.command

        return prefix + self._signature(cmd)

    async def format(self):
        """Handles the actual behaviour involved with formatting.
        To change the behaviour, this method should be overridden.
        Returns
        --------
        list
            A paginated output of the help command.
        """
        self.embed = discord.Embed(color=statics.embed_color)
        self.embed.set_footer(text=f"Type {self.clean_prefix}{self.context.invoked_with} command for more info on a command.")

        # we need a padding of ~80 or so

        description = self.command.description if not self.is_cog() else inspect.getdoc(self.command)

        if description:
            # <description> portion
            self.embed.description = description

        from discord.ext import commands
        if isinstance(self.command, commands.Command):
            # <signature portion>
            signature = self.get_command_signature()

            self.embed.set_author(name=signature)

            # <long doc> section
            if self.command.help:
                self.embed.description = self.command.help

            # end it here if it's just a regular command
            if not self.has_subcommands():
                self.embed.set_footer(text="<> required    |    [] optional")
                return self.embed

        max_width = self.max_name_size

        def category(tup):
            cog = tup[1].cog_name
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + ':' if cog is not None else '\u200bNo Category:'

        filtered = await self.filter_command_list()
        if self.is_bot():
            self.embed.set_author(name="Commands")
            data = sorted(filtered, key=category)
            for category, commands in itertools.groupby(data, key=category):
                # there simply is no prettier way of doing this.
                commands = sorted(commands)
                if len(commands) > 0:
                    self.embed.add_field(name=category, value=self._get_subcommands(max_width, commands), inline=False)

        else:
            filtered = sorted(filtered)
            if filtered:
                self.embed.add_field(name="Commands", value=self._get_subcommands(max_width, filtered), inline=False)

        # add the ending note
        return self.embed


class Help:
    def __init__(self, bot):
        self. bot = bot


    @commands.command(hidden=True)
    async def help(self, ctx, *commands):
        destination = ctx.message.author if self.bot.pm_help else ctx.message.channel

        def repl(obj):
            return _mentions_transforms.get(obj.group(0), '')

        # help by itself just lists our own commands.
        if len(commands) == 0:
            pages = await self.bot.formatter.format_help_for(ctx, self.bot)
        elif len(commands) == 1:
            # try to see if it is a cog name
            name = _mention_pattern.sub(repl, commands[0])
            command = None
            if name in self.bot.cogs:
                command = self.bot.cogs[name]
            else:
                command = self.bot.all_commands.get(name)
                if command is None:
                    await destination.send(self.bot.command_not_found.format(name))
                    return

            pages = await self.bot.formatter.format_help_for(ctx, command)
        else:
            name = _mention_pattern.sub(repl, commands[0])
            command = self.bot.all_commands.get(name)
            if command is None:
                await destination.send(embed=self.bot.embeds.error(f"No command called `{name}` found."))
                return

            for key in commands[1:]:
                try:
                    key = _mention_pattern.sub(repl, key)
                    command = command.all_commands.get(key)
                    if command is None:
                        await destination.send(self.bot.command_not_found.format(key))
                        return
                except AttributeError:
                    await destination.send(self.bot.command_has_no_subcommands.format(command, key))
                    return

            pages = await self.bot.formatter.format_help_for(ctx, command)

        if self.bot.pm_help is None:
            characters = sum(map(lambda l: len(l), pages))
            # modify destination based on length of pages.
            if characters > 1000:
                destination = ctx.message.author

        await destination.send(embed=pages)


def setup(bot):
    bot.formatter = HelpFormatter()

    bot.remove_command("help")
    bot.add_cog(Help(bot))