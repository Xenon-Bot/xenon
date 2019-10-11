from discord.ext import commands as cmd
from aiohttp import web
import prometheus_client as prometheus
from prometheus_client.exposition import choose_encoder


events = prometheus.Counter("events", "The count of events the bot processed", ["type"])
latencies = prometheus.Gauge('latencies', "The shard latencies", ["shard"])


class Api(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.add_routes([
            web.get("/health", self.liveness_probe),
            web.get("/metrics", self.metrics)
        ])
        self.runner = web.AppRunner(self.app)
        self.bot.loop.create_task(self.start_app())

    def cog_unload(self):
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

    async def metrics(self, request):
        r = prometheus.REGISTRY
        encoder, content_type = choose_encoder(request.headers.get('HTTP_ACCEPT'))
        if request.query.get("name[]"):
            r = r.restricted_registry(request.query['name[]'])

        return web.Response(body=encoder(r), headers={"Content-type": content_type})

    @cmd.Cog.listener()
    async def on_connect(self):
        # Might be called multiple time, but doesn't really matter
        for shard_id, shard in self.bot.shards.items():
            latencies.labels(shard=shard_id).set_function(lambda: shard.ws.latency)



def setup(bot):
    bot.add_cog(Api(bot))
