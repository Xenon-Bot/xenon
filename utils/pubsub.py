from utils.database import rdb as db
import traceback


table = db.table("pubsub")


async def subscribe(topic, handler, delete=True):
    feed = await table.changes()["new_val"].filter(lambda row: row["topic"] == topic).run(db.con)
    while await feed.fetch_next():
        update = await feed.next()
        if delete:
            await table.get(update["id"]).delete().run(db.con)

        update.pop("id", None)
        update.pop("topic", None)
        try:
            await handler(**update)
        except:
            traceback.print_exc()


async def publish(topic, **values):
    await table.insert({"topic": topic, **values}).run(db.con)
