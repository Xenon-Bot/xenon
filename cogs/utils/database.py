import rethinkdb as r
import asyncio

class Database:
    def __init__(self, host="localhost", port=28015):
        r.set_loop_type("asyncio")
        self.host = host
        self.port = port
        self.c = None

    async def setup(self):
        self.c = await r.connect(host=self.host, port=self.port, db="Xenon")

    async def save_backup(self, backup_data: dict):
        return await r.table("backups").insert(backup_data).run(self.c)

    async def get_backup(self, backup_id: str):
        return await r.table("backups").get(backup_id).run(self.c)