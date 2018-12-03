import rethinkdb as rdb
from discord.ext import commands as cmd


rdb.set_loop_type("asyncio")

host, port, database = "localhost", 28015, "xenon"
table_setup = {
    "xenon": {
        "backups": {},
        "templates": {},
        "intervals": {},
        "users": {},
        "syncs": {}
    }
}


async def setup():
    rdb.con = await rdb.connect(host=host, port=port, db=database)

    for db_name, tables in table_setup.items():
        if db_name not in await rdb.db_list().run(rdb.con):
            await rdb.db_create(db_name).run(rdb.con)

        db = rdb.db(db_name)
        for table_name, data in tables.items():
            if table_name not in await db.table_list().run(rdb.con):
                await db.table_create(table_name).run(rdb.con)

                if len(data) >= 0:
                    await db.table(table_name).insert(data).run(rdb.con)


async def update_stats(**keys):
    await rdb.table("bot").get("stats").update(keys).run(rdb.con)


class DatabaseConverter(cmd.Converter):
    def __init__(self, table):
        self.table = table

    async def convert(self, ctx, argument):
        return await rdb.table(self.table).get(argument).run(rdb.con)
