import asyncio
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from telethon.sync import TelegramClient, events

api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")


client = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)


async def run_command(*args):
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode == 0


@client.on(events.NewMessage)
async def my_event_handler(event):
    if "download" in event.raw_text:
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
            await event.reply(
                "There was a problem with the url, please try again later"
            )


if __name__ == "__main__":
    client.start()
    client.run_until_disconnected()
