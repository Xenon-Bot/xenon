async def async_cursor_to_list(cursor):
    result = []
    while await cursor.fetch_next():
        result.append(await cursor.next())

    return result


def datetime_to_string(datetime):
    return datetime.strftime("%d. %b %Y - %H:%M")
