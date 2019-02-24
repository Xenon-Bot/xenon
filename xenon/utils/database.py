import rethinkdb as rdb
from os import environ as env


rdb.set_loop_type("asyncio")

host, port, database = env.get("DB_HOST") or "localhost", env.get("DB_PORT") or 28015, "xenon"
table_setup = {
    "xenon": {
        "backups": {},
        "templates": {},
        "intervals": {},
        "users": {},
        "syncs": {},
        "shards": {},
        "pubsub": {}
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

                if len(data) > 0:
                    await db.table(table_name).insert(data).run(rdb.con)
