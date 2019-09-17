from os import environ as env

db_host = env.get('DB_HOST') or "localhost"
db_user = env.get('DB_USER')
db_password = env.get('DB_PASSWORD')

token = env.get('TOKEN')
shard_count = int(env.get('SHARD_COUNT') or 1)
shards_per_pod = int(env.get('SHARDS_PER_POD') or 1)

_hostname = env.get("HOSTNAME")
pod_id = 0
if _hostname is not None:
    try:
        pod_id = int(_hostname.split("-")[-1])
    except ValueError:
        pass  # Probably using docker

prefix = "x!"

extensions = [
    "cogs.errors",
    "cogs.help",
    "cogs.admin",
    "cogs.backups",
    "cogs.templates",
    "cogs.users",
    "cogs.basics",
    "cogs.sharding",
    "cogs.botlist",
    "cogs.api"
]

support_guild = 410488579140354049
owner_id = 386861188891279362

template_approval_channel = 565845836529926144
template_list = env.get('TEMPLATE_LIST')
template_approval = env.get('TEMPLATE_APPROVAL')
template_featured = env.get('TEMPLATE_FEATURED')

dbl_token = env.get('DBL_TOKEN')
