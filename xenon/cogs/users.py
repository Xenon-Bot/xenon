from discord.ext import commands as cmd
import discord
from datetime import datetime
import pytz
from prettytable import PrettyTable

from utils import formatter, helpers, checks


class Users(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

        @bot.check
        async def not_blacklisted(ctx):
            entry = await ctx.db.users.find_one({"id": ctx.author.id, "blacklist.state": True})
            if entry is None:
                return True

            raise cmd.CommandError("Sorry, **you are blacklisted**.\n\n"
                                   f"**Reason**: {entry['blacklist']['reason']}")

    @cmd.group(aliases=["bl"], hidden=True, invoke_without_command=True)
    @checks.has_role_on_support_guild("Admin")
    async def blacklist(self, ctx):
        table = PrettyTable()
        table.field_names = ["User", "Reason", "Admin", "Timestamp"]

        blacklist = ctx.db.users.find({"blacklist.state": True})
        async for entry in blacklist:
            user = await self.bot.fetch_user(entry["_id"])
            admin = await self.bot.fetch_user(entry["blacklist"]["admin"])

            table.add_row([
                f"{user} ({user.id})",
                entry["blacklist"]["reason"],
                f"{admin} ({entry['blacklist']['admin']})",
                helpers.datetime_to_string(entry["blacklist"]["timestamp"])
            ])

        pages = formatter.paginate(str(table))
        for page in pages:
            await ctx.send(f"```diff\n{page}```")

    @blacklist.command()
    @checks.has_role_on_support_guild("Admin")
    async def add(self, ctx, user: discord.User, *, reason):
        await ctx.db.users.update_one({"id": user.id}, {"$set": {
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
