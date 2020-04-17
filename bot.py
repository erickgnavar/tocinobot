import asyncio
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from telethon.sync import TelegramClient, events

SUPERADMIN = os.environ.get("SUPERADMIN")

api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")


client = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

db = set([SUPERADMIN])


def is_allowed_user(username):
    return username in db


async def run_command(*args):
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode == 0


@client.on(events.NewMessage(pattern=r"^add (?P<username>\w+)$"))
async def add_user_handler(event):
    if event.chat.username != SUPERADMIN:
        return

    (username,) = event.pattern_match.groups()
    db.add(username)
    await event.reply(f"{username} was added")


@client.on(events.NewMessage(pattern=r"^remove (?P<username>\w+)$"))
async def remove_user_handler(event):
    if event.chat.username != SUPERADMIN:
        return

    (username,) = event.pattern_match.groups()

    if username == SUPERADMIN:
        await event.reply("admin can't be deleted :P")
    elif username in db:
        db.remove(username)
        await event.reply(f"{username} was removed")
    else:
        await event.reply(f"{username} doesn't exist")


@client.on(events.NewMessage(pattern=r"^users$"))
async def list_users_handler(event):
    if event.chat.username != SUPERADMIN:
        return

    text = ", ".join(db)
    await event.reply(f"users: {text}")


@client.on(events.NewMessage(pattern=r"^download "))
async def download_video_handler(event):
    if not is_allowed_user(event.chat.username):
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
        await done_message.delete()
    else:
        await event.reply("There was a problem, please try again later")


if __name__ == "__main__":
    client.start()
    client.run_until_disconnected()
