
# Mirror Bot (Hybrid Version)

This Telegram bot uses both a bot token (`bot.py`) and a user session (`userbot.py`) to mirror data from another bot.

## Features
- Mirror data from @ttmlog_bot using userbot
- Anti-spam with auto-ban
- Admin panel with inline actions (refill, ban, premium, export)
- Queue system with database
- English-only messages and UI

## Setup

1. Clone or extract this repo
2. Create a virtual environment and activate it:
   ```
   python -m venv env
   env\Scripts\activate  (on Windows)
   source env/bin/activate (on Linux/macOS)
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Edit `config.py` with your:
   - `api_id`, `api_hash` (from https://my.telegram.org)
   - `bot_token` (from @BotFather)
   - `phone_number` (Telegram account for userbot)
   - `admin_group_id` (group for usage reports)
   - Add your Telegram user ID to `ADMINS` in `bot.py`

## Run

In **2 separate terminals** (after venv is activated):

### Terminal 1:
```
python userbot.py
```
- Will ask for phone verification on first run

### Terminal 2:
```
python bot.py
```
- Starts the bot for user interaction

## Notes
- You must keep both running for full functionality
- Database file `hybrid_queue.db` is auto-created
- Files are downloaded and renamed before being sent to the user

Enjoy your own professional mirror bot!
