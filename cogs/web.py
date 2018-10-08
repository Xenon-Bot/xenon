from aiohttp import web
import traceback

from cogs.utils import oauth, file_system


routes = web.RouteTableDef()


@routes.get("/rejoin")
async def rejoin(request):
    code = request.query.get("code")
    if code is None:
        raise web.HTTPFound("https://discordapp.com/api/oauth2/authorize?client_id=416358583220043796&redirect_uri=http%3A%2F%2Flocalhost%3A8089%2Frejoin&response_type=code&scope=guilds.join")

    try:
        token, response = await oauth.client.get_access_token(code=code, redirect_uri="http://localhost:8089/rejoin", loop=request.app.loop)
        user = await oauth.client.request(method="GET", url="https://discordapp.com/api/v6/users/@me")
        file_system.save_json_file(f"rejoin/{user['id']}", response)
    except:
        raise web.HTTPBadRequest

    return web.Response(status=200, text="<h1>Thanks for authorizing</h1>", content_type="text/html")


class WebServer:
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.start())

    async def start(self):
        app = web.Application()
        app["bot"] = self.bot
        app.add_routes(routes)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8089)
        await site.start()


def setup(bot):
    bot.add_cog(WebServer(bot))