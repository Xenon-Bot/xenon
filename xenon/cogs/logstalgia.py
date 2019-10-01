from discord.ext import commands as cmd, tasks
import sys
from datetime import datetime
import traceback
import asyncio
import aiohttp


LOG_URL = "http://logstalgia.discord.club/log/"


class Logstalgia(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = []
        self.post_loop.start()

    def cog_unload(self):
        self.post_loop.cancel()

    def get_initiator(self, data):
        if data.get("id"):
            return data["id"]

        for sub_data in data.values():
            if isinstance(sub_data, dict):
                result = self.get_initiator(sub_data)
                if result:
                    return result

    def get_time(self):
        return datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S") + " +0000"

    def get_size(self, msg, seen=None):
        """Recursively finds size of objects"""
        size = sys.getsizeof(msg)
        if seen is None:
            seen = set()
        obj_id = id(msg)
        if obj_id in seen:
            return 0
        seen.add(obj_id)
        if isinstance(msg, dict):
            size += sum([self.get_size(v, seen) for v in msg.values()])
            size += sum([self.get_size(k, seen) for k in msg.keys()])
        elif hasattr(msg, '__dict__'):
            size += self.get_size(msg.__dict__, seen)
        elif hasattr(msg, '__iter__') and not isinstance(msg, (str, bytes, bytearray)):
            size += sum([self.get_size(i, seen) for i in msg])
        return size

    @cmd.Cog.listener()
    async def on_socket_response(self, msg):
        self.events.append({
            "initiator": self.get_initiator(msg) or 0,
            "timestamp": datetime.utcnow().timestamp(),
            "event": msg.get("t") or "UNDEFINED",
            "size": self.get_size(msg)
        })

    @tasks.loop(minutes=1, reconnect=True)
    async def post_loop(self):
        self.bot.log.debug("Posting %s events to logstalgia" % len(self.events))
        try:
            try:
                await self.bot.session.post(
                    LOG_URL,
                    headers={"Authorization": self.bot.config.logstalgia_token},
                    json=self.events,
                    timeout=aiohttp.ClientTimeout(total=30)
                )
            except asyncio.TimeoutError:
                pass
        except Exception:
            traceback.print_exc()

        finally:
            self.events = []


def setup(bot):
    bot.add_cog(Logstalgia(bot))
