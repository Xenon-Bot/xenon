from discord.ext import commands as cmd
import discord
from datetime import datetime
import pytz

from utils import checks


class Users(cmd.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot

        @bot.check
        async def not_blacklisted(ctx):
            entry = await ctx.db.users.find_one({"_id": ctx.author.id, "blacklist.state": True})
            if entry is None:
                return True

            raise cmd.CommandError("Sorry, **you are blacklisted**.\n\n"
                                   f"**Reason**: {entry['blacklist']['reason']}")

    @cmd.group(aliases=["bl"], invoke_without_command=True)
    @checks.has_role_on_support_guild("Staff")
    async def blacklist(self, ctx):
        embed = ctx.em("", type="info", title="Blacklist")["embed"]
        count = await ctx.db.users.count_documents({"blacklist.state": True})
        blacklist = await ctx.db.users.find({"blacklist.state": True}).to_list(count)
        if len(blacklist) == 0:
            await ctx.send(**ctx.em("The blacklist is empty", type="info"))

        for entry in blacklist:
            user = await self.bot.fetch_user(entry["_id"])
            embed.add_field(name=f"{user} ({user.id})", value=f"```{entry['blacklist']['reason']}```")
            if len(embed.fields) == 10:
                await ctx.send(embed=embed)
                embed.clear_fields()

        if len(embed.fields) > 0:
            await ctx.send(embed=embed)

    @blacklist.command()
    @checks.has_role_on_support_guild("Admin")
    async def add(self, ctx, user_id: int, *, reason):
        user = await ctx.bot.fetch_user(user_id)
        await ctx.db.users.update_one({"_id": user.id}, {"$set": {
            "_id": user.id,
            "blacklist": {
                "state": True,
                "reason": reason,
                "admin": ctx.author.id,
                "timestamp": datetime.now(pytz.utc)
            }
        }}, upsert=True)
        await ctx.send(**ctx.em(f"Successfully **blacklisted** the user **{str(user)}** (<@{user.id}>).", type="success"))

    @blacklist.command(aliases=["rm", "remove", "del"])
    @checks.has_role_on_support_guild("Admin")
    async def delete(self, ctx, user: discord.User):
        await ctx.db.users.update_one({"_id": user.id}, {"$set": {"blacklist": {"state": False}}})
        await ctx.send(**ctx.em(f"Successfully **removed** the user **{str(user)}** (<@{user.id}>) from the **blacklist**.", type="success"))


def setup(bot):
    bot.add_cog(Users(bot))
