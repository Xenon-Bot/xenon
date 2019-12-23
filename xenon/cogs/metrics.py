from discord.ext import commands as cmd, tasks
import prometheus_client as prometheus
import logging

log = logging.getLogger(__name__)


registry = prometheus.CollectorRegistry()
events = prometheus.Counter("bot_events", "The count of events the bot processed", ["type"], registry=registry)
latencies = prometheus.Gauge('bot_latencies', "The shard latencies", ["shard"], registry=registry)
guilds = prometheus.Gauge('bot_guilds', "Total guild count per shard", ["shard"], registry=registry)
guilds_unavailable = prometheus.Gauge('bot_guilds_unavailable', "Total guilds that are unavailable", registry=registry)
members = prometheus.Gauge('bot_members', "Total member count per shard", ["shard"], registry=registry)


class Metrics(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.metric_task.start()

    def cog_unload(self):
        self.metric_task.cancel()

    @cmd.Cog.listener()
    async def on_socket_response(self, msg):
        if msg.get("t"):
            events.labels(type=msg["t"]).inc()

    @tasks.loop(minutes=1)
    async def metric_task(self):
        def async_handler(url, method, timeout, headers, data):
            async def handle():
                async with self.bot.session.request(
                    method=method,
                    url=url,
                    data=data,
                    headers=headers
                ) as resp:
                    if resp.status >= 400:
                        log.error("Error pushing metrics to gateway: %s %s" % (resp.status, await resp.text()))

            return lambda: self.bot.loop.create_task(handle())

        log.debug("Pushing metrics to gateway")
        try:
            prometheus.push_to_gateway(
                gateway="prometheus-pushgateway.monitoring:9091",
                job=self.bot.config.identifier,
                grouping_key={"pod": self.bot.shard_ids[0]},
                registry=registry,
                handler=async_handler
            )
        except Exception as e:
            log.error("Error pushing metrics to gateway: %s %s" % (type(e), str(e)))

    @cmd.Cog.listener()
    async def on_connect(self):
        # Might be called multiple time, but doesn't really matter
        for shard_id, shard in self.bot.shards.items():
            latencies.labels(shard=shard_id).set_function(lambda: shard.ws.latency)

            def shard_guilds():
                return list(filter(lambda g: ((g.id >> 22) % self.bot.shard_count) == shard_id, self.bot.guilds))

            guilds.labels(shard=shard_id).set_function(lambda: len(shard_guilds()))
            guilds_unavailable.labels(shard=shard_id).set_function(lambda: len([
                g for g in shard_guilds() if g.unavailable
            ]))
            members.labels(shard=shard_id).set_function(lambda: sum([g.member_count for g in shard_guilds()]))


def setup(bot):
    bot.add_cog(Metrics(bot))
