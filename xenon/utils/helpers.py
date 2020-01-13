from discord.ext import commands as cmd
import asyncio


async def async_cursor_to_list(cursor):
    result = []
    while await cursor.fetch_next():
        result.append(await cursor.next())

    return result


def datetime_to_string(datetime):
    return datetime.strftime("%d. %b %Y - %H:%M")


def clean_content(content):
    content = content.replace("@everyone", "@\u200beveryone")
    content = content.replace("@here", "@\u200bhere")
    return content


def format_number(number):
    suffix = ""
    if number >= 1000:
        suffix = "k"
        number = round(number / 1000, 1)

    return "{:,}{}".format(number, suffix)


async def ask_question(ctx, question, converter=str):
    question_msg = await ctx.send(**ctx.em(question, type="wait_for"))
    try:
        msg = await ctx.bot.wait_for(
            event="message",
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
            timeout=60
        )

    except asyncio.TimeoutError:
        raise cmd.CommandError("**Canceled process**, because you didn't respond.")

    else:
        if msg.content.lower() == "cancel":
            raise cmd.CommandError("**Canceled process**.")

        try:
            return converter(msg.content)
        except ValueError:
            convert_name = str(converter).replace("int", "number").replace("float", "decimal number")
            raise cmd.CommandError(f"`{msg.content}` is **not a valid {convert_name}**.")

        finally:
            try:
                await msg.delete()
            except Exception:
                pass

    finally:
        await question_msg.delete()


class IterWaitFor:
    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        self.args = args
        self.kwargs = kwargs

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.bot.wait_for(*self.args, **self.kwargs)
