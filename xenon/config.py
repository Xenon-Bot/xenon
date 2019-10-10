from os import environ as env

_hostname = env.get("HOSTNAME")
_pod_id = 0
if _hostname is not None:
    try:
        _pod_id = int(_hostname.split("-")[-1])
    except ValueError:
        pass  # Probably using docker


class Config:
    token = None
    shard_count = 1
    shards_per_pod = 1
    pod_id = _pod_id

    prefix = "x!"

    dbl_token = None

    support_guild = 410488579140354049
    owner_id = 386861188891279362

    db_host = "localhost"
    db_name = "xenon"
    db_user = None
    db_password = None

    redis_host = "localhost"

    template_approval_channel = 565845836529926144
    template_list = None
    template_approval = None
    template_featured = None

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
        "cogs.api",
        "cogs.builder"
    ]

    def __getattribute__(self, item):
        default = getattr(Config, item, None)
        value = env.get(item.upper())

        if value is not None:
            if isinstance(default, int):
                return int(value)

            if isinstance(default, float):
                return float(value)

            if isinstance(default, list):
                return value.split(",")

            return value

        return default
