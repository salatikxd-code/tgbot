# app/bot/bot_instance.py
from aiogram import Bot
from app.config import TELEGRAM_TOKEN

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set. Set TELEGRAM_TOKEN in environment or .env")

bot = Bot(token=TELEGRAM_TOKEN)
