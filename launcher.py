from bot import Xenon
import json

with open("secrets.json") as config:
    config_contents = json.load(config)

bot = Xenon(**config_contents)
bot.run(config_contents["token"])