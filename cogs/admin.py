from discord.ext import commands as cmd
import discord
import traceback
import inspect
from contextlib import redirect_stdout
import textwrap
import io
from datetime import datetime
import pytz
from prettytable import PrettyTable

from utils import formatter, helpers


class Admin:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

        @bot.check
        async def not_blacklisted(ctx):
            entry = await ctx.db.rdb.table("blacklist").get(str(ctx.author.id)).run(ctx.db.con)
            if entry is None:
                return True

            raise cmd.CommandError("Sorry, **you are blacklisted**.\n\n"
                                   f"**Reason**: {entry['reason']}")

    @cmd.group(aliases=["bl"], hidden=True, invoke_without_command=True)
    @cmd.is_owner()
    async def blacklist(self, ctx):
        blacklist = await ctx.db.rdb.table("blacklist").run(ctx.db.con)
        table = PrettyTable()
        table.field_names = ["User", "Reason", "Admin", "Timestamp"]
        while (await blacklist.fetch_next()):
            entry = await blacklist.next()
            try:
                user = await self.bot.get_user_info(int(entry["id"]))
                admin = await self.bot.get_user_info(int(entry["admin"]))
            except:
                continue

            table.add_row([
                f"{user} ({entry['id']})",
                entry["reason"],
                f"{admin} ({entry['admin']})",
                helpers.datetime_to_string(entry["timestamp"])
            ])

        pages = formatter.paginate(str(table))
        for page in pages:
            await ctx.send(f"```diff\n{page}```")

    @blacklist.command()
    @cmd.is_owner()
    async def add(self, ctx, user: discord.User, *, reason):
        await ctx.db.rdb.table("blacklist").insert({
            "id": str(user.id),
            "reason": reason,
            "admin": str(ctx.author.id),
            "timestamp": datetime.now(pytz.utc)
        }, conflict="replace").run(ctx.db.con)
        await ctx.send(**ctx.em(f"Successfully **blacklisted** the user {str(user)} (<@{user.id}>).", type="success"))

    @blacklist.command(aliases=["rm", "remove", "del"])
    @cmd.is_owner()
    async def delete(self, ctx, user: discord.User):
        await ctx.db.rdb.table("blacklist").get(str(user.id)).delete().run(ctx.db.con)
        await ctx.send(**ctx.em(f"Successfully **removed** the user {str(user)} (<@{user.id}>) from the **blacklist**.", type="success"))

    @cmd.command(aliases=["rl"], hidden=True)
    @cmd.is_owner()
    async def reload(self, ctx, cog):
        """
        Reload a cog


        cog ::      The name of the cod
        """
        if cog.lower() == "all":
            failed = 0
            success = 0
            for cog in self.bot.config.extensions:
                try:
                    self.bot.unload_extension(cog)
                    self.bot.load_extension(cog)
                    success += 1
                except:
                    failed += 1
                    traceback.print_exc()

            await ctx.send(**ctx.em(f"Reloaded all cogs.\n**Success**: {success} **Failed**: {failed}", type="info"))
            return

        base_path = "cogs."
        try:
            self.bot.unload_extension(base_path + cog.lower())
            self.bot.load_extension(base_path + cog.lower())
            await ctx.send(**ctx.em(f"Successfully reloaded the cog named **{cog}**.", type="success"))
        except:
            traceback.print_exc()
            raise cmd.CommandError(f"Error while reloading the cog named **{cog}**.")

    @cmd.command(hidden=True)
    @cmd.is_owner()
    async def exec(self, ctx, *, body: str):
        """
        Executes something, uses exec not eval -> returns None
        **body**: The code to get executed
        """

        def cleanup_code(content):
            """Automatically removes code blocks from the code."""
            # remove ```py\n```
            if content.startswith('```') and content.endswith('```'):
                return '\n'.join(content.split('\n')[1:-1])

            # remove `foo`
            return content.strip('` \n')

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'msg': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()

        except:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @cmd.command(hidden=True)
    @cmd.is_owner()
    async def eval(self, ctx, *, code: str):
        to_eval = code.replace("await ", "")
        try:
            result = eval(to_eval)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            result = type(e).__name__ + ": " + str(e)

        result = str(result).replace(ctx.config.token, "you tried")

        embed = ctx.em("")["embed"]
        embed.title = "Eval Result"
        embed.add_field(name="Input 📥", value=f"```Python\n{code}```", inline=False)
        embed.add_field(name="Output 📤", value=f"```Python\n{result}```", inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Admin(bot))
