import inspect
import io
import textwrap
import traceback
from contextlib import redirect_stdout
from prettytable import PrettyTable

import discord
from discord.ext import commands

import statics
from cogs.utils import checks, formatter

fake_token = "mfa.VkO_2G4Qv3T--YOU--lWetW_tjND--TRIED--QFTm6YGtzq9PH--4U--tG0"
em = formatter.embed_message


class Admin:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def __local_check(self, ctx):
        return checks.is_bot_admin(ctx)

    @commands.command()
    async def guilds(self, ctx, limit: int = 20, reverse: bool = True, owner: discord.User = None):
        guilds = sorted([guild for guild in self.bot.guilds if owner is None or guild.owner.id == owner.id],
                        reverse=reverse, key=lambda g: g.member_count)[:limit]
        table = PrettyTable()
        table.field_names = ["Place", "Name", "Guild-Id", "Owner", "Members"]
        table.align["Name"] = "l"
        table.align["Owner"] = "l"
        for place, guild in enumerate(guilds):
            table.add_row([place + 1, formatter.clean(guild.name), guild.id, formatter.clean(guild.owner.name), guild.member_count])

        pages = formatter.paginate(str(table), limit=1500)
        for page in pages:
            await ctx.send(f"```diff\n{page}```")

    @commands.command(hidden=True)
    async def debug(self, ctx):
        """Runs the debug protocol"""
        await ctx.invoke(self.bot.get_command("extension reload"), "all")


    @commands.command(hidden=True)
    @commands.is_owner()
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
        except Exception as e:
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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def eval(self, ctx, *, code: str):
        to_eval = code.replace("await ", "")
        try:
            result = eval(to_eval)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            result = type(e).__name__ + ": " + str(e)

        if "token" in to_eval:
            result = fake_token

        result = str(result).replace(statics.token, fake_token)

        embed = discord.Embed(title="Evaluate", color=statics.embed_color)
        embed.add_field(name="Input 📥", value=f"```Python\n{code}```", inline=False)
        embed.add_field(name="Output 📤", value=f"```Python\n{result}```", inline=False)

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True, hidden=True)
    async def notify(self, ctx):
        """Notify users of this bot"""
        await ctx.invoke(self.bot.get_command("help"), "notify")

    @notify.command()
    @commands.is_owner()
    async def owners(self, ctx, *, message: str):
        """Notify the owners of all guilds this bot is on"""
        done = []
        for guild in self.bot.guilds:
            if guild.id in (264445053596991498, 110373943822540800):
                continue

            owner = guild.owner
            if owner.id in done:
                continue

            try:
                await owner.send(embed=self.bot.embeds.info(message))
            except:
                general = None
                for channel in guild.channels:
                    if channel.name.lower() == "general":
                        general = channel

                try:
                    await general.send(embed=self.bot.embeds.info(message))
                    continue
                except:
                    for channel in guild.channels:
                        try:
                            await channel.send(embed=self.bot.embeds.info(message))
                            break
                        except:
                            continue

            done.append(owner.id)

        await ctx.send(**em(f"Successfully **notified {len(done)} owners**!", type="success"))



def setup(bot):
    bot.add_cog(Admin(bot))