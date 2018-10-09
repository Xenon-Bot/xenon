import traceback
import sys

from cogs.utils import formatter
import statics

em = formatter.embed_message


class SpecialEvents:
    def __init__(self, bot):
        bot.on_error = self.on_error
        self.bot = bot

    async def on_guild_join(self, guild):
        if statics.test_mode:
            return

        channel = self.bot.get_channel(499210092214747147)
        embed = em(f"**{guild.name}** by **{guild.owner}**", type="success")["embed"]
        embed.set_author(name="Joined guild", icon_url="https://cdn0.iconfinder.com/data/icons/small-n-flat/24/678092-sign-add-512.png")
        embed.set_footer(text=f"Now on {len(self.bot.guilds)} guilds")
        await channel.send(embed=embed)

    async def on_guild_remove(self, guild):
        if statics.test_mode:
            return

        channel = self.bot.get_channel(499210092214747147)
        embed = em(f"**{guild.name}** by **{guild.owner}**", type="error")["embed"]
        embed.set_author(name="Left guild", icon_url="https://cdn4.iconfinder.com/data/icons/gradient-ui-1/512/minus-512.png")
        embed.set_footer(text=f"Now on {len(self.bot.guilds)} guilds")
        await channel.send(embed=embed)

    async def on_shard_ready(self, shard_id):
        if statics.test_mode:
            return

        channel = self.bot.get_channel(499211087628206110)
        embed = em(f"Shard **{shard_id}** (re)connected", type="warning")["embed"]
        embed.set_author(name="Shard connected", icon_url="https://cdn4.iconfinder.com/data/icons/small-n-flat/24/star-512.png")
        await channel.send(embed=embed)

    async def on_error(self, event_method, *args, **kwargs):
        if statics.test_mode:
            return

        print('Ignoring exception in {}'.format(event_method), file=sys.stderr)
        traceback.print_exc()
        channel = self.bot.get_channel(499211087628206110)
        embed = em(str(traceback.extract_stack()), type="unex_error")["embed"]
        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(SpecialEvents(bot))