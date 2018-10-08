from datetime import datetime


def get_now_utc():
    return datetime.utcnow()


def format_datetime(time, short=False):
    if short:
        return time.strftime("%d. %b %Y, %I:%M %p")
    return time.strftime("%a the %d. %b %Y, %I:%M %p")


def format_timedelta(delta):
    return str(delta)[:-3] + " hours"
