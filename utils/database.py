import rethinkdb as rdb
from discord.ext import commands as cmd


rdb.set_loop_type("asyncio")
con = None

host, port, database = "localhost", 28015, "xenon"
table_setup = {
    "xenon": {
        "backups": {},
        "templates": {},
        "intervals": {},
        "blacklist": {}
    }
}


async def setup():
    global con
    con = await rdb.connect(host=host, port=port, db=database)

    for db_name, tables in table_setup.items():
        if db_name not in await rdb.db_list().run(con):
            await rdb.db_create(db_name).run(con)

        db = rdb.db(db_name)
        for table_name, data in tables.items():
            if table_name not in await db.table_list().run(con):
                await db.table_create(table_name).run(con)

                await db.table(table_name).insert(data).run(con)


async def update_stats(**keys):
    await rdb.table("bot").get("stats").update(keys).run(con)


class DatabaseConverter(cmd.Converter):
    def __init__(self, table):
        self.table = table

    async def convert(self, ctx, argument):
        return await rdb.table(self.table).get(argument).run(con)
