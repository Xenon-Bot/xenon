from discord.ext import commands as cmd
import traceback
import asyncio
from datetime import datetime
import aioredis
import uuid
import json
import inspect
from contextlib import redirect_stdout
import io
import textwrap


class PublishReturn:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis
        self.channel = None
        self.responses = []

    async def _response_reader(self):
        async for msg in self.channel.iter(decoder=json.loads):
            self.responses.append(msg)

    async def _wait_for_responses(self, nonce, timeout=0.5):
        responses = []

        async def with_timeout():
            while True:
                for i, response in enumerate(self.responses):
                    if response["nonce"] == nonce:
                        responses.append(self.responses.pop(i))

                await asyncio.sleep(0)

        try:
            await asyncio.wait_for(with_timeout(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        return responses

    async def start(self, loop, channel):
        self.channel = channel
        loop.create_task(self._response_reader())

    async def respond(self, msg, json):
        await self.redis.publish_json(self.channel.name, {"nonce": msg["nonce"], **json})

    async def publish(self, channel, json: dict, timeout=0.5):
        nonce = str(uuid.uuid4())
        await self.redis.publish_json(channel, {"nonce": nonce, **json})
        return await self._wait_for_responses(nonce, timeout=timeout)


class Sharding(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.update_loop())
        self.bot.loop.create_task(self.subscribe())

        self.pubre = None

    async def update_database(self):
        latencies = self.bot.latencies
        shards = {id: {"latency": latency, "guilds": 0, "users": 0, "seen": datetime.utcnow()}
                  for id, latency in latencies}
        for guild in self.bot.guilds:
            try:
                shards[guild.shard_id]["guilds"] += 1
                shards[guild.shard_id]["users"] += guild.member_count
            except:
                pass

        for id, shard in shards.items():
            await self.bot.db.shards.update_one({"_id": id}, {"$set": shard}, upsert=True)

    async def update_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self.update_database()
            except:
                traceback.print_exc()

            await asyncio.sleep(60)

    async def _eval_reader(self, channel):
        async for msg in channel.iter(decoder=json.loads):
            try:
                to_eval = msg["statement"].replace("await ", "")
                try:
                    result = eval(to_eval)
                    if inspect.isawaitable(result):
                        result = await result
                except Exception as e:
                    result = type(e).__name__ + ": " + str(e)

                await self.pubre.respond(msg, {"result": result})
            except Exception:
                traceback.print_exc()

    async def _exec_reader(self, channel):
        async for msg in channel.iter(decoder=json.loads):
            try:
                env = {
                    'bot': self.bot,
                    "self": self,
                    "config": self.bot.config
                }

                env.update(globals())
                stdout = io.StringIO()
                to_compile = f'async def func():\n{textwrap.indent(msg["body"], "  ")}'

                try:
                    exec(to_compile, env)
                except Exception as e:
                    await self.pubre.respond(msg, {"success": 0, "result": str(e.__class__.__name__)})
                    return

                func = env['func']
                try:
                    with redirect_stdout(stdout):
                        ret = await func()

                except Exception:
                    await self.pubre.respond(msg, {"success": 0, "result": str(traceback.format_exc())})
                else:
                    value = stdout.getvalue()

                    if ret is None:
                        await self.pubre.respond(msg, {"success": 1, "result": str(value)})
                    else:
                        await self.pubre.respond(msg, {"success": 1, "result": str(value) + str(ret)})
            except Exception:
                traceback.print_exc()

    async def subscribe(self):
        await self.bot.wait_until_ready()
        eval_channel, exec_channel, response_channel = await self.bot.redis.subscribe("eval", "exec", "responses")
        self.bot.loop.create_task(self._eval_reader(eval_channel))
        self.bot.loop.create_task(self._exec_reader(exec_channel))
        self.pubre = PublishReturn(self.bot.redis)
        await self.pubre.start(self.bot.loop, response_channel)

    @staticmethod
    def _format_results(operator, results):
        operators = {
            "+": lambda rts: sum([float(r) for r in rts]),
            "~": lambda rts: sum([float(r) for r in rts]) / len(rts)
        }
        operator_func = operators.get(operator, lambda rts: (operator + " ").join([str(r) for r in rts]))
        return operator_func(results)

    @cmd.command(hidden=True)
    @cmd.is_owner()
    async def geval(self, ctx, timeout: float, operator: str, *, statement):
        statement = statement.strip("`")
        results = await self.pubre.publish("eval", {"statement": statement}, timeout=timeout)
        formatted_results = str(self._format_results(operator, [r['result'] for r in results]))
        if len(formatted_results) > 1800:
            pass

        else:
            await ctx.send(
                f"__{len(results)} Results:__```{formatted_results}```"
            )

    @cmd.command(hidden=True)
    @cmd.is_owner()
    async def gexec(self, ctx, timeout: float, operator: str, *, body):
        def cleanup_code(content):
            """Automatically removes code blocks from the code."""
            # remove ```py\n```
            if content.startswith('```') and content.endswith('```'):
                return '\n'.join(content.split('\n')[1:-1])

            # remove `foo`
            return content.strip('` \n')

        results = await self.pubre.publish("exec", {"body": cleanup_code(body)}, timeout=timeout)
        formatted_results = str(self._format_results(operator, [r['result'] for r in results]))
        if len(formatted_results) > 1800:
            pass

        else:
            await ctx.send(
                f"__{len(results)} Results:__```{formatted_results}```"
            )


def setup(bot):
    bot.add_cog(Sharding(bot))
