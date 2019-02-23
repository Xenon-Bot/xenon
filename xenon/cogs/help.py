from discord.ext import commands as cmd
import inspect
import itertools


class HelpFormatter(cmd.HelpFormatter):
    def __init__(self, show_hidden=False, show_check_failure=True):
        super().__init__(show_hidden, show_check_failure)

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
                should_print = param.default if isinstance(
                    param.default, str) else param.default is not None
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
        """
        Added asciidoc highlighting
        """
        self._paginator = cmd.formatter.Paginator(prefix="```asciidoc")

        # we need a padding of ~80 or so

        description = self.command.description if not self.is_cog() else inspect.getdoc(self.command)

        if description:
            # <description> portion
            self._paginator.add_line(description, empty=True)

        if isinstance(self.command, cmd.Command):
            # <signature portion>
            signature = self.get_command_signature()
            self._paginator.add_line(signature, empty=True)

            # <long doc> section
            if self.command.help:
                self._paginator.add_line(self.command.help, empty=True)

            # end it here if it's just a regular command
            if not self.has_subcommands():
                self._paginator.close_page()
                return self._paginator.pages

        max_width = self.max_name_size

        def category(tup):
            cog = tup[1].cog_name
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + ':' if cog is not None else '\u200bNo Category:'

        filtered = await self.filter_command_list()
        if self.is_bot():
            data = sorted(filtered, key=category)
            for category, commands in itertools.groupby(data, key=category):
                # there simply is no prettier way of doing this.
                commands = sorted(commands)
                if len(commands) > 0:
                    self._paginator.add_line(category)

                self._add_subcommands_to_page(max_width, commands)
        else:
            filtered = sorted(filtered)
            if filtered:
                self._paginator.add_line('Commands:')
                self._add_subcommands_to_page(max_width, filtered)

        # add the ending note
        self._paginator.add_line()
        ending_note = self.get_ending_note()
        self._paginator.add_line(ending_note)
        return self._paginator.pages


def setup(bot):
    bot.formatter = HelpFormatter()
