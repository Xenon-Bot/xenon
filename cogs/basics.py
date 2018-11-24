from discord.ext import commands as cmd
from prettytable import PrettyTable

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


def setup(bot):
    bot.add_cog(Basics(bot))
