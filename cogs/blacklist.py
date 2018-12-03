from discord.ext import commands as cmd
import discord
from datetime import datetime
import pytz
from prettytable import PrettyTable

from utils import formatter, helpers, checks


class Blacklist:
    def __init__(self, bot):
        self.bot = bot

        @bot.check
        async def not_blacklisted(ctx):
            entry = await ctx.db.table("users").get(str(ctx.author.id)).run(ctx.db.con)
            if entry is None or entry.get("blacklist") is None:
                return True

            raise cmd.CommandError("Sorry, **you are blacklisted**.\n\n"
                                   f"**Reason**: {entry['blacklist']['reason']}")

    @cmd.group(aliases=["bl"], hidden=True, invoke_without_command=True)
    @checks.has_role_on_support_guild("Admin")
    async def blacklist(self, ctx):
        blacklist = await ctx.db.table("users").filter({"blacklist": {"state": True}}).run(ctx.db.con)
        table = PrettyTable()
        table.field_names = ["User", "Reason", "Admin", "Timestamp"]
        while (await blacklist.fetch_next()):
            entry = await blacklist.next()
            try:
                user = await self.bot.get_user_info(int(entry["id"]))
                admin = await self.bot.get_user_info(int(entry["blacklist"]["admin"]))
            except:
                continue

            table.add_row([
                f"{user} ({entry['id']})",
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
        await ctx.db.table("users").insert({
            "id": str(user.id),
            "blacklist": {
                "state": True,
                "reason": reason,
                "admin": str(ctx.author.id),
                "timestamp": datetime.now(pytz.utc)
            }
        }, conflict="update").run(ctx.db.con)
        await ctx.send(**ctx.em(f"Successfully **blacklisted** the user **{str(user)}** (<@{user.id}>).", type="success"))

    @blacklist.command(aliases=["rm", "remove", "del"])
    @checks.has_role_on_support_guild("Admin")
    async def delete(self, ctx, user: discord.User):
        await ctx.db.table("users").get(str(user.id)).replace(ctx.db.row.without('blacklist')).run(ctx.db.con)
        await ctx.send(**ctx.em(f"Successfully **removed** the user **{str(user)}** (<@{user.id}>) from the **blacklist**.", type="success"))


def setup(bot):
    bot.add_cog(Blacklist(bot))
