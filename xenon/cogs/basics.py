from discord.ext import commands as cmd
from prettytable import PrettyTable
import psutil
from datetime import datetime, timedelta

from utils import formatter, helpers


class Basics(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cmd.command()
    async def ping(self, ctx):
        """Pong"""
        await ctx.send(**ctx.em(f"I have a **latency** of **{round(self.bot.latency * 1000, 1)} ms**.", type="info"))

    @cmd.command(aliases=['shardid'])
    async def shard(self, ctx, guild_id: int = None):
        guild_id = guild_id or ctx.guild.id
        shard_id = (guild_id >> 22) % self.bot.shard_count
        await ctx.send(**ctx.em(f"The guild with the id **{guild_id}** is on **shard {shard_id}**.", type="info"))

    @cmd.command()
    @cmd.cooldown(1, 10, cmd.BucketType.user)
    async def shards(self, ctx):
        """Show information about the virtual shards in this physical shard"""
        table = PrettyTable()
        table.field_names = ["Shard-Id", "Latency", "Guilds", "Users"]
        shards = await self.bot.get_shards()
        for shard in shards:
            latency = f"{round(shard['latency'] * 1000, 1)} ms"
            if (datetime.utcnow() - shard["seen"]) > timedelta(minutes=3):
                latency = "offline?"

            table.add_row([str(shard["id"]), latency, helpers.format_number(shard["guilds"]),
                           helpers.format_number(shard["users"])])

        pages = formatter.paginate(str(table))
        for page in pages:
            await ctx.send(f"```diff\n{page}```")

    @cmd.command()
    async def invite(self, ctx):
        """Invite Xenon"""
        await ctx.send(**ctx.em(
            "**Invite Xenon**\n\n[Xenon](https://discord.club/invite/xenon)\n[Xenon Pro](https://discordapp.com/api/oauth2/authorize?client_id=524652984425250847&permissions=8&scope=bot) Use `x!pro` to get more information.",
            type="info"))

    @cmd.command(aliases=["i", "stats", "status"])
    @cmd.cooldown(1, 10, cmd.BucketType.user)
    async def info(self, ctx):
        embed = ctx.em("")["embed"]
        embed.description = "Server Backups, Templates and more"
        embed.title = "Xenon"
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Invite", value="[Click Here](https://discord.club/invite/xenon)")
        embed.add_field(name="Discord", value="[Click Here](https://discord.club/discord)")
        embed.add_field(name="Prefix", value=ctx.config.prefix)
        embed.add_field(name="Guilds", value=helpers.format_number(await self.bot.get_guild_count()))
        embed.add_field(name="Shards", value=self.bot.shard_count or 1)
        embed.add_field(name="Users", value=helpers.format_number(await self.bot.get_user_count()))
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%")
        embed.add_field(name="RAM Usage", value=f"{psutil.virtual_memory().percent}%")

        await ctx.send(embed=embed)

    @cmd.command()
    async def pro(self, ctx):
        """Shows information about Xenon Pro"""
        await ctx.send(**ctx.em(
            "**Xenon Pro** is the **paid version** of xenon. It includes some **exclusive features**.\n"
            "You can buy it [here](https://www.patreon.com/merlinfuchs).\n"
            "Invite it [here](https://discordapp.com/api/oauth2/authorize?client_id=524652984425250847&permissions=8&scope=bot)\n\n"
            "You can find **more information** about the subscription and a **detailed list of perks** [here](https://docs.discord.club/xenon/how-to/xenon-pro).",
            type="info"
        ))
        if ctx.bot.user.id == 524652984425250847:
            await ctx.invoke(self.bot.get_command("help"), "Pro")

    @cmd.Cog.listener()
    async def on_guild_join(self, guild):
        embed = self.bot.em("**Hello and thank you for inviting Xenon!** 😋\n"
                            f"Use `{self.bot.config.prefix}help` to get a list of commands.\n"
                            "For updates and further help, you can join the [support discord](https://discord.club/discord)!\n\n")


def setup(bot):
    bot.add_cog(Basics(bot))
