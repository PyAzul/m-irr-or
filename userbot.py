import os, asyncio
from telethon import TelegramClient, events
from config import api_id, api_hash, phone_number
from shared import init_shared_db, fetch_pending, mark_processing, mark_done

client = TelegramClient("userbot_session", api_id, api_hash)
init_shared_db()

active_job = None

@client.on(events.NewMessage(from_users='ttmlog_bot'))
async def button_handler(event):
    global active_job
    if not active_job:
        return

    if event.buttons:
        await asyncio.sleep(4)
        for i, row in enumerate(event.buttons):
            for j, btn in enumerate(row):
                if btn.text.lower().startswith("url:"):
                    try:
                        await event.click(i, j)
                    except Exception as e:
                        print(f"[Userbot] Failed to click button: {e}")
                    break

async def process_queue():
    global active_job
    while True:
        jobs = fetch_pending()
        for job in jobs:
            queue_id, user_id, username, keyword = job
            print(f"[Userbot] Processing: {keyword}")
            mark_processing(queue_id)
            active_job = (queue_id, keyword)

            await client.send_message('@ttmlog_bot', f'/search {keyword}')
            await asyncio.sleep(20)

            async for msg in client.iter_messages('ttmlog_bot', limit=10):
                if msg.file:
                    ext = os.path.splitext(msg.file.name or "")[-1]
                    if ext in ['.txt', '.zip']:
                        new_filename = f"result_{keyword.replace('.', '_')}{ext}"
                        await client.download_media(msg, file=new_filename)
                        mark_done(queue_id, new_filename)
                        print(f"[Userbot] DONE: {new_filename}")
                        break

            active_job = None
        await asyncio.sleep(5)

client.start(phone=phone_number)
print("[Userbot] Active and ready to mirror.")
client.loop.create_task(process_queue())
client.run_until_disconnected()