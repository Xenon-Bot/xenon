from discord.ext import commands as cmd
from prettytable import PrettyTable
import psutil

from utils import formatter


class Basics:
    def __init__(self, bot):
        self.bot = bot

    @cmd.command()
    async def ping(self, ctx):
        """Pong"""
        await ctx.send(**ctx.em(f"I have a **latency** of **{round(self.bot.latency * 1000, 1)} ms**.", type="info"))

    @cmd.command()
    async def shards(self, ctx):
        """Show shard stats"""
        table = PrettyTable()
        table.field_names = ["Shard-Id", "Latency", "Guilds", "Members"]
        shards = {shard_id: {"latency": latency, "guilds": 0, "members": 0}
                  for shard_id, latency in self.bot.latencies}
        for guild in self.bot.guilds:
            shards[guild.shard_id]["guilds"] += 1
            shards[guild.shard_id]["members"] += guild.member_count

        for shard_id, values in shards.items():
            table.add_row([shard_id, f"{round(values['latency'] * 1000, 1)} ms",
                           values["guilds"], values["members"]])

        pages = formatter.paginate(str(table))
        for page in pages:
            await ctx.send(f"```diff\n{page}```")

    @cmd.command()
    async def invite(self, ctx):
        """Invite Xenon"""
        await ctx.send(**ctx.em("You can **invite Xenon** [here](https://discord.club/invite/xenon).", type="info"))

    @cmd.command(aliases=["i", "stats", "status"])
    async def info(self, ctx):
        embed = ctx.em("")["embed"]
        embed.description = "Server Backups, Templates and more"
        embed.title = "Xenon"
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Invite", value="[Click Here](https://discord.club/invite/xenon)")
        embed.add_field(name="Discord", value="[Click Here](https://discord.club/discord)")
        embed.add_field(name="Prefix", value=ctx.config.prefix)
        embed.add_field(name="Guilds", value=len(self.bot.guilds))
        embed.add_field(name="Shards", value=self.bot.shard_count)
        embed.add_field(name="Users", value=len(self.bot.users))
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%")
        embed.add_field(name="RAM Usage", value=f"{psutil.virtual_memory().percent}%")

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Basics(bot))
