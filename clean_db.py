import asyncio
from datetime import datetime
import pytz
import traceback

from utils import database as db


rdb = db.rdb


async def clean():
    await db.setup()
    backups = await rdb.table("backups").run(rdb.con)
    i = 0
    while await backups.fetch_next():
        i += 1
        backup = await backups.next()
        if backup["timestamp"] < datetime(2018, 11, 27, tzinfo=pytz.utc) and backup.get("keep") != True:
            print(i, backup["id"], backup["timestamp"], backup.get("keep"))
            try:
                await rdb.table("backups").get(backup["id"]).delete().run(rdb.con)
            except:
                traceback.print_exc()


loop = asyncio.get_event_loop()
loop.run_until_complete(clean())