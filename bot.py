import asyncio
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running"


@app.route("/health")
def health():
    return "OK"


async def post_news(bot: Bot):
    # Пока просто тестовый текст. Позже заменим на реальные новости.
    news_text = "📰 **Тестовая новость**\n\nЗдесь будет текст."
    try:
        await bot.send_message(CHANNEL_ID, news_text, parse_mode=ParseMode.MARKDOWN)
        print("Пост отправлен", flush=True)
    except Exception as e:
        print(f"Ошибка при отправке поста: {e}", flush=True)


async def run_bot():
    try:
        print(f"Старт бота. CHANNEL_ID={CHANNEL_ID}", flush=True)
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        me = await bot.get_me()
        print(f"Токен действителен, бот авторизован: @{me.username}", flush=True)

        dp = Dispatcher()
        scheduler = AsyncIOScheduler()
        scheduler.add_job(post_news, "interval", minutes=60, args=[bot])
        scheduler.start()
        print("Бот запущен и планировщик работает", flush=True)

    

        await asyncio.Event().wait()
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА при запуске бота: {e}", flush=True)


def start_bot_thread():
    asyncio.run(run_bot())


if __name__ == "__main__":
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()
    app.run(host="0.0.0.0", port=PORT)
