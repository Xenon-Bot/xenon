from discord.ext import commands as cmd, tasks
from aiohttp import web
import prometheus_client as prometheus
import traceback


registry = prometheus.CollectorRegistry()
events = prometheus.Counter("events", "The count of events the bot processed", ["type"], registry=registry)
latencies = prometheus.Gauge('latencies', "The shard latencies", ["shard"], registry=registry)


class Api(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.add_routes([
            web.get("/health", self.liveness_probe)
        ])
        self.metric_task.start()
        self.runner = web.AppRunner(self.app)
        self.bot.loop.create_task(self.start_app())

    def cog_unload(self):
        self.metric_task.cancel()
        self.bot.loop.create_task(self.runner.cleanup())

    async def start_app(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, port=9090)
        await site.start()

    async def liveness_probe(self, request):
        if self.bot.is_ready():
            raise web.HTTPOk()

        raise web.HTTPNotAcceptable()

    @cmd.Cog.listener()
    async def on_socket_response(self, msg):
        if msg.get("t"):
            events.labels(type=msg["t"]).inc()

    @tasks.loop(minutes=1)
    async def metric_task(self):
        raise ValueError
        def async_handler(url, method, timeout, headers, data):
            async def handle():
                async with self.bot.session.request(
                    method=method,
                    url=url,
                    data=data,
                    headers=headers
                ) as resp:
                    if resp.status >= 400:
                        raise IOError("error talking to pushgateway: {0} {1}".format(resp.status, await resp.text()))

            return lambda: self.bot.loop.create_task(handle())

        try:
            prometheus.push_to_gateway(
                gateway="prometheus-pushgateway.monitoring:9091",
                job=self.bot.config.db_name,
                registry=registry,
                handler=async_handler
            )
        except Exception:
            traceback.print_exc()

    @cmd.Cog.listener()
    async def on_connect(self):
        # Might be called multiple time, but doesn't really matter
        for shard_id, shard in self.bot.shards.items():
            latencies.labels(shard=shard_id).set_function(lambda: shard.ws.latency)


def setup(bot):
    bot.add_cog(Api(bot))
