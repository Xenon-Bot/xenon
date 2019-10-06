from discord.ext import commands as cmd
import sys
from datetime import datetime
import logging


class Logstalgia(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

        handler = logging.FileHandler("logs/logstalgia.log")
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

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
        self.logger.info("%s - - [%s] \"GET /%s  HTTP/1.0\" 200 %s" % (
            self.get_initiator(msg) or 0,
            datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S") + " +0000",
            msg.get("t") or "UNDEFINED",
            self.get_size(msg)
        ))


def setup(bot):
    bot.add_cog(Logstalgia(bot))
