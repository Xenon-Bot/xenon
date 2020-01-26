from aiohttp import ClientSession
from asyncio import get_event_loop

# Using aiohttp because it's installed anyways


async def check():
    session = ClientSession()
    resp = await session.request("GET", "http://localhost:9090/health")
    await session.close()

    if resp.status == 200:
        exit(0)

    else:
        exit(1)


if __name__ == "__main__":
    loop = get_event_loop()
    loop.run_until_complete(check())