import json
import os
import aiofiles


base_path = "storage/"


async def save_json_file(file, data):
    async with aiofiles.open(base_path + file + ".json", "w") as f:
        await f.write(json.dumps(data))
        await f.close()

async def get_json_file(file):
    try:
        async with aiofiles.open(base_path + file + ".json", "r") as f:
            return json.loads(await f.read())

    except:
        return None

async def delete(file):
    os.remove(base_path + file + ".json")