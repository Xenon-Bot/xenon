# Rename this to "config.py"

token = "your-bot-token"
shard_count = 1  # ~ guilds // 1000
shard_ids = None  # ~ Optional

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

self_host = True
# The options below are not required if "self_host" is enabled

dbl_token = ""
