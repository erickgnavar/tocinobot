import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

from telethon.sync import TelegramClient, events

SUPERADMIN = os.environ.get("SUPERADMIN")

api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")

NOT_PASS_MESSAGE = "🧙‍♂️you shall not pass!"

client = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)


def setup_db(path):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("create table if not exists users (username text)")
    cursor.execute("select * from users where username = ?", (SUPERADMIN,))
    if cursor.fetchone() is None:
        cursor.execute("insert into users values (?)", (SUPERADMIN,))
    conn.commit()
    return conn


# TODO: place this connection in a better place
conn = setup_db("data.db")


def list_users(conn):
    cursor = conn.cursor()
    cursor.execute("select username from users")
    return [row[0] for row in cursor.fetchall()]


def add_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("insert into users values (?)", (username,))
    conn.commit()


def remove_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("delete from users where username = (?)", (username,))
    conn.commit()


def is_allowed_user(username):
    return username in list_users(conn)


async def run_command(*args):
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode == 0


@client.on(events.NewMessage(pattern=r"^add (?P<username>\w+)$"))
async def add_user_handler(event):
    if event.chat.username != SUPERADMIN:
        await event.reply(NOT_PASS_MESSAGE)
        return

    (username,) = event.pattern_match.groups()
    add_user(conn, username)
    await event.reply(f"{username} was added")


@client.on(events.NewMessage(pattern=r"^remove (?P<username>\w+)$"))
async def remove_user_handler(event):
    if event.chat.username != SUPERADMIN:
        return

    (username,) = event.pattern_match.groups()

    if username == SUPERADMIN:
        await event.reply("admin can't be deleted :P")
    elif username in list_users(conn):
        remove_user(conn, username)
        await event.reply(f"{username} was removed")
    else:
        await event.reply(f"{username} doesn't exist")


@client.on(events.NewMessage(pattern=r"^users$"))
async def list_users_handler(event):
    if event.chat.username != SUPERADMIN:
        await event.reply(NOT_PASS_MESSAGE)
        return

    text = ", ".join(list_users(conn))
    await event.reply(f"users: {text}")


@client.on(events.NewMessage(pattern=r"^video "))
async def download_video_handler(event):
    if not is_allowed_user(event.chat.username):
        await event.reply(NOT_PASS_MESSAGE)
        return

    notify_message = await event.reply("we're working on it...")

    _, url = event.raw_text.split(" ")

    filepath = Path(tempfile.gettempdir()) / Path(f"{uuid4().hex}.mp4")

    args = ["youtube-dl", "-f", "mp4", "-o", filepath, url]

    result = await run_command(*args)

    await notify_message.delete()

    if result:
        sender = await event.get_input_sender()
        done_message = await event.reply("Your video is uploading")

        await client.send_file(sender, file=filepath)

        # delete original message after the requested file is sent successfully
        await event.delete()
        await done_message.delete()
    else:
        await event.reply("There was a problem, please try again later")


@client.on(events.NewMessage(pattern=r"^mp3 "))
async def download_audio_handler(event):
    if not is_allowed_user(event.chat.username):
        await event.reply(NOT_PASS_MESSAGE)
        return

    notify_message = await event.reply("we're working on it...")

    _, url = event.raw_text.split(" ")

    # TODO: use metadata to name the resulting file
    filepath = Path(tempfile.gettempdir()) / Path(f"{uuid4().hex}.%(ext)s")

    args = ["youtube-dl", url, "--audio-format=mp3", "-o", filepath, "-x"]

    result = await run_command(*args)

    await notify_message.delete()

    if result:
        sender = await event.get_input_sender()
        done_message = await event.reply("Your mp3 is uploading")

        # we need to replace this because the extension will be inserted by youtube-dl
        # and the filepath have the youtube-dl template
        filepath = str(filepath).replace("%(ext)s", "mp3")

        await client.send_file(sender, file=filepath)

        # delete original message after the requested file is sent successfully
        await event.delete()
        await done_message.delete()
    else:
        await event.reply("There was a problem, please try again later")


if __name__ == "__main__":
    client.start()
    client.run_until_disconnected()
