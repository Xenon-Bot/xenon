# Rename this to "config.py"

token = "your-bot-token"
pasteee_key = ""
# shard_count and shard_ids can be overwritten by Command Line Arguments
shard_count = None  # ~ guilds // 1000
shard_ids = None

prefix = "x!"

extensions = [
    "cogs.errors",
    "cogs.help",
    "cogs.admin",
    "cogs.backups",
    "cogs.templates",
    "cogs.pro",
    "cogs.blacklist",
    "cogs.basics",
    "cogs.stats"
]

support_guild = 410488579140354049
update_channel = 526897380595859456

self_host = True
# The options below are not required if "self_host" is enabled

dbl_token = ""
