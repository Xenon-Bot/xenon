from discord.ext import commands as cmd
from discord import Embed
import itertools


class HelpCommand(cmd.HelpCommand):
    def __init__(self, **options):
        self.sort_commands = options.pop('sort_commands', True)
        self.commands_heading = options.pop('commands_heading', "Commands")
        self.dm_help = options.pop('dm_help', False)
        self.dm_help_threshold = options.pop('dm_help_threshold', 1000)
        self.aliases_heading = options.pop('aliases_heading', "Aliases:")
        self.no_category = options.pop('no_category', 'No Category')
        self.paginator = options.pop('paginator', None)

        if self.paginator is None:
            self.paginator = cmd.Paginator(suffix=None, prefix=None)

        super().__init__(**options)

    async def send_pages(self):
        """A helper utility to send the page output from :attr:`paginator` to the destination."""
        destination = self.get_destination()
        for page in self.paginator.pages:
            emb = Embed(description='%s\n​' % page, color=0x478fce)
            emb.set_footer(text=self.get_ending_note())
            await destination.send(embed=emb)

    def command_not_found(self, string):
        return 'There is no command with that name.'

    def get_opening_note(self):
        """Returns help command's opening note. This is mainly useful to override for i18n purposes.

        The default implementation returns ::

            Use `{prefix}{command_name} [command]` for more info on a command.
            You can also use `{prefix}{command_name} [category]` for more info on a category.

        """
        return None

    def get_command_signature(self, command):
        return '%s%s %s' % (self.clean_prefix, command.qualified_name, command.signature)

    def get_ending_note(self):
        """Return the help command's ending note. This is mainly useful to override for i18n purposes.

        The default implementation does nothing.
        """
        command_name = self.invoked_with
        return "Use `{0}{1} [command]` for more info on a command.\n" \
               "You can also use `{0}{1} [category]` for more info on a category.".format(self.clean_prefix,
                                                                                          command_name)

    def add_bot_commands_formatting(self, commands, heading):
        """Adds the minified bot heading with commands to the output.

        The formatting should be added to the :attr:`paginator`.

        The default implementation is a bold underline heading followed
        by commands separated by an EN SPACE (U+2002) in the next line.

        Parameters
        -----------
        commands: Sequence[:class:`Command`]
            A list of commands that belong to the heading.
        heading: :class:`str`
            The heading to add to the line.
        """
        if commands:
            # U+2002 Middle Dot
            joined = '\n'.join("**{0}{1:{s}<{n}}** {2}".format(
                self.clean_prefix,
                c.qualified_name,
                c.short_doc,
                s='\u2002',
                n=15
            ) for c in commands)
            self.paginator.add_line('__**%s**__\n' % heading)
            self.paginator.add_line('%s\n' % joined)

    def add_subcommand_formatting(self, command):
        """Adds formatting information on a subcommand.

        The formatting should be added to the :attr:`paginator`.

        The default implementation is the prefix and the :attr:`Command.qualified_name`
        optionally followed by an En dash and the command's :attr:`Command.short_doc`.

        Parameters
        -----------
        command: :class:`Command`
            The command to show information of.
        """
        fmt = '**{0}{1:{s}<{n}}** {2}' if command.short_doc else '**{0}{1}**'
        self.paginator.add_line(
            fmt.format(self.clean_prefix, command.qualified_name, command.short_doc, s='\u2002', n=20))

    def add_aliases_formatting(self, aliases):
        """Adds the formatting information on a command's aliases.

        The formatting should be added to the :attr:`paginator`.

        The default implementation is the :attr:`aliases_heading` bolded
        followed by a comma separated list of aliases.

        This is not called if there are no aliases to format.

        Parameters
        -----------
        aliases: Sequence[:class:`str`]
            A list of aliases to format.
        """
        self.paginator.add_line('**%s** %s' % (self.aliases_heading, ', '.join(aliases)), empty=True)

    def add_command_formatting(self, command):
        """A utility function to format commands and groups.

        Parameters
        ------------
        command: :class:`Command`
            The command to format.
        """

        if command.description:
            self.paginator.add_line(command.description, empty=True)

        signature = self.get_command_signature(command)
        self.paginator.add_line('**{0}**'.format(signature), empty=True)

        if command.help:
            try:
                self.paginator.add_line(command.help.format(c=__import__("config")), empty=True)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
                self.paginator.add_line()

    def get_destination(self):
        ctx = self.context
        if self.dm_help is True:
            return ctx.author
        elif self.dm_help is None and len(self.paginator) > self.dm_help_threshold:
            return ctx.author
        else:
            return ctx.channel

    async def prepare_help_command(self, ctx, command):
        self.paginator.clear()
        await super().prepare_help_command(ctx, command)

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            self.paginator.add_line(bot.description, empty=True)

        note = self.get_opening_note()
        if note:
            self.paginator.add_line(note, empty=True)

        no_category = '\u200b{0.no_category}'.format(self)

        def get_category(command, *, no_category=no_category):
            cog = command.cog
            return cog.qualified_name if cog is not None else no_category

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name) if self.sort_commands else list(commands)
            self.add_bot_commands_formatting(commands, category)

        await self.send_pages()

    async def send_cog_help(self, cog):
        bot = self.context.bot
        if bot.description:
            self.paginator.add_line(bot.description, empty=True)

        note = self.get_opening_note()
        if note:
            self.paginator.add_line(note, empty=True)

        filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
        if filtered:
            self.paginator.add_line('__**%s %s**__' % (cog.qualified_name, self.commands_heading), empty=True)
            for command in filtered:
                self.add_subcommand_formatting(command)

        await self.send_pages()

    async def send_group_help(self, group):
        self.add_command_formatting(group)

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        if filtered:
            self.paginator.add_line('__**%s**__' % self.commands_heading, empty=True)
            for command in filtered:
                self.add_subcommand_formatting(command)

        await self.send_pages()

    async def send_command_help(self, command):
        self.add_command_formatting(command)
        self.paginator.close_page()
        await self.send_pages()


class Help(cmd.Cog, name="\u200BOthers"):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = HelpCommand(verify_checks=False)
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command


def setup(bot):
    bot.add_cog(Help(bot))
