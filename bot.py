from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import api_id, api_hash, bot_token, admin_group_id
from shared import (
    init_shared_db, add_to_queue, get_result, is_spamming,
    get_token, get_status, add_user
)
import sqlite3, asyncio, os

app = Client("mirror_bot", bot_token=bot_token, api_id=api_id, api_hash=api_hash)
init_shared_db()

ADMINS = [123456789]  # Replace with your Telegram ID
pending_keywords = {}
admin_pending_action = {}

def is_admin(user_id):
    return user_id in ADMINS

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user = message.from_user
    user_id = user.id
    username = user.username or "None"
    add_user(user_id, username)
    await message.reply(
        "Welcome to **DataGate** – your secure gateway to curated datasets.

"
        "To begin, send:
`/search domain.com`
Example:
`/search netflix.com`

"
        "For help, type `/help`.",
        quote=True
    )

@app.on_message(filters.command("help") & filters.private)
async def help_handler(client, message):
    await message.reply(
        "**Usage Guide:**

"
        "`/search domain.com`
Submit a dataset request using a valid domain name.
"
        "Example: `/search netflix.com`

"
        "**Limits:**
Free users: 3 searches/day
Premium users: Unlimited access.",
        quote=True
    )

@app.on_message(filters.command("profile") & filters.private)
async def profile_handler(client, message):
    user = message.from_user
    user_id = user.id
    username = user.username or "None"
    token = get_token(user_id)
    status = get_status(user_id)
    await message.reply(
        f"**Your Profile**

"
        f"Username : @{username}
"
        f"ID       : {user_id}
"
        f"Token    : {token}
"
        f"Status   : {status}"
    )

@app.on_message(filters.command("search") & filters.private)
async def search_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: /search domain.com")
    user_id = message.from_user.id
    keyword = message.command[1].strip()
    pending_keywords[user_id] = keyword
    await message.reply(
        f"Confirm search for: `{keyword}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm", callback_data="confirm_search")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_search")]
        ])
    )

@app.on_callback_query(filters.regex("confirm_search|cancel_search"))
async def confirm_callback(client, callback):
    user = callback.from_user
    user_id = user.id
    username = user.username or "None"
    keyword = pending_keywords.pop(user_id, None)
    if not keyword:
        return await callback.answer("No pending search.")
    if callback.data == "cancel_search":
        return await callback.edit_message_text("❌ Search cancelled.")
    spam_check = is_spamming(user_id)
    if spam_check == "warn":
        await callback.message.reply("Too fast. Please wait before trying again.")
        return
    elif spam_check == "banned":
        await callback.message.reply("You have been blocked due to repeated abuse.")
        return
    add_user(user_id, username)
    queue_id = add_to_queue(user_id, username, keyword)
    await callback.edit_message_text(f"✅ Search confirmed for `{keyword}`. Please wait...")
    for _ in range(12):
        await asyncio.sleep(5)
        result = get_result(queue_id)
        if result and os.path.exists(result):
            await client.send_document(user_id, result, caption=f"✅ Dataset for `{keyword}`")
            os.remove(result)
            return
    await client.send_message(user_id, "⚠️ Data not found or request failed.")

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("Not authorized.")
    await message.reply(
        "**[ADMIN PANEL]**
Select an action:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Refill", callback_data="admin_refill")],
            [InlineKeyboardButton("✨ Premium", callback_data="admin_premium")],
            [InlineKeyboardButton("⛔ Ban", callback_data="admin_ban"),
             InlineKeyboardButton("✅ Unban", callback_data="admin_unban")],
            [InlineKeyboardButton("📋 Users", callback_data="admin_users"),
             InlineKeyboardButton("📦 Export", callback_data="admin_export")]
        ])
    )

@app.on_callback_query(filters.regex(r"admin_(refill|premium|ban|unban|users|export)"))
async def admin_callback(client, callback):
    action = callback.data.split("_")[1]
    if not is_admin(callback.from_user.id):
        return await callback.answer("Not allowed.", show_alert=True)
    if action in ["users", "export"]:
        dummy = type("Dummy", (), {"from_user": callback.from_user, "reply": callback.message.reply})
        dummy.command = [f"/{action}"]
        if action == "users":
            return await users_handler(client, dummy)
        if action == "export":
            return await export_users_handler(client, dummy)
    admin_pending_action[callback.from_user.id] = action
    await callback.message.edit(f"Send user ID or @username for `{action}`")

@app.on_message(filters.private & filters.text)
async def handle_admin_input(client, message):
    admin_id = message.from_user.id
    if admin_id not in admin_pending_action:
        return
    action = admin_pending_action.pop(admin_id)
    target = message.text.strip()
    conn = sqlite3.connect("hybrid_queue.db")
    cur = conn.cursor()
    if target.startswith("@"):
        cur.execute("SELECT user_id FROM users WHERE username = ?", (target[1:],))
        row = cur.fetchone()
        if not row:
            return await message.reply("User not found.")
        target_id = row[0]
    else:
        try:
            target_id = int(target)
        except:
            return await message.reply("Invalid ID format.")
    if action == "refill":
        cur.execute("UPDATE users SET token = token + 5 WHERE user_id = ?", (target_id,))
        await client.send_message(target_id, "You received 5 bonus tokens.")
    elif action == "premium":
        cur.execute("UPDATE users SET token = 9999, is_premium = 1 WHERE user_id = ?", (target_id,))
        await client.send_message(target_id, "You are now a Premium user.")
    elif action == "ban":
        cur.execute("UPDATE users SET token = 0 WHERE user_id = ?", (target_id,))
        await client.send_message(target_id, "You have been banned.")
    elif action == "unban":
        cur.execute("UPDATE users SET token = 3 WHERE user_id = ?", (target_id,))
        await client.send_message(target_id, "Your access has been restored.")
    conn.commit()
    await message.reply(f"Action `{action}` completed for `{target}`.")

@app.on_message(filters.command("exportusers") & filters.private)
async def export_users_handler(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("Not authorized.")
    conn = sqlite3.connect("hybrid_queue.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, token, is_premium FROM users")
    rows = cur.fetchall()
    if not rows:
        return await message.reply("No users found.")
    filename = "users_export.csv"
    with open(filename, "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["User ID", "Username", "Token", "Status"])
        for uid, uname, token, prem in rows:
            status = "Premium" if prem else ("Banned" if token == 0 else "Free")
            writer.writerow([uid, uname, token, status])
    await message.reply_document(filename, caption="📦 Exported user list")
    os.remove(filename)

@app.on_message(filters.command("users") & filters.private)
async def users_handler(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("Not authorized.")
    conn = sqlite3.connect("hybrid_queue.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, token, is_premium FROM users ORDER BY rowid DESC LIMIT 40")
    rows = cur.fetchall()
    if not rows:
        return await message.reply("No users found.")
    text = "**[Latest Users]**

"
    for i, (uid, uname, token, prem) in enumerate(rows, 1):
        status = "Premium" if prem else ("Banned" if token == 0 else "Free")
        uname = f"@{uname}" if uname and uname != "None" else "(no username)"
        text += f"{i}. {uname} (ID: {uid}) - Token: {token} - {status}
"
    text += f"
Total: {len(rows)}"
    await message.reply(text)

app.run()