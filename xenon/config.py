from os import environ as env


class Config:
    token = None
    shard_count = 1
    shards_per_pod = 1

    prefix = "x!"

    dbl_token = None

    support_guild = 410488579140354049
    owner_id = 386861188891279362

    identifier = "xenon"

    db_host = "localhost"
    db_user = None
    db_password = None

    redis_host = "localhost"

    template_approval_channel = 633228946875482112
    template_list = None
    template_approval = None
    template_featured = None

    extensions = [
        "errors",
        "help",
        "admin",
        "backups",
        "templates",
        "users",
        "basics",
        "sharding",
        "botlist",
        "api",
        "builder",
        "metrics"
    ]


def __getattr__(name):
    default = getattr(Config, name, None)
    value = env.get(name.upper())

    if value is not None:
        if isinstance(default, int):
            return int(value)

        if isinstance(default, float):
            return float(value)

        if isinstance(default, bool):
            valid = ["y", "yes", "true"]
            return value.lower() in valid

        if isinstance(default, list):
            return value.split(",")

        return value

    return default
