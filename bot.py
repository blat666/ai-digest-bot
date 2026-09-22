import asyncio
import os
import re
import threading
from datetime import datetime, timedelta, timezone

import feedparser
from flask import Flask
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PORT = int(os.environ.get("PORT", 10000))

# ---- Источники RSS: название -> ссылка ----
RSS_FEEDS = {
    "Tproger AI": "https://tproger.ru/feed/",
    "Habr: ИИ": "https://habr.com/ru/rss/hubs/artificial_intelligence/all/",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "Wired AI": "https://www.wired.com/feed/tag/ai/latest/rss",
    "SiliconANGLE": "https://siliconangle.com/feed/",
}

# ---- Настройки ----
MAX_POSTS_PER_RUN = 3   # сколько новостей за один цикл
FRESH_HOURS = 24        # свежесть: только новости за последние N часов
POST_INTERVAL_MINUTES = 60  # раз в час

app = Flask(__name__)
seen_urls = set()


@app.route("/")
def home():
    return "Bot is running"


@app.route("/health")
def health():
    return "OK"


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_fresh_items():
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=FRESH_HOURS)
    items = []

    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                link = entry.get("link", "").strip()
                if not link or link in seen_urls:
                    continue

                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < threshold:
                        continue
                    sort_key = pub_dt
                else:
                    sort_key = now

                title = clean_html(entry.get("title", ""))[:200]
                summary = clean_html(entry.get("summary", ""))[:300]

                items.append({
                    "source": source,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "sort_key": sort_key,
                })
        except Exception as e:
            print(f"Ошибка RSS {source}: {e}", flush=True)

    items.sort(key=lambda x: x["sort_key"], reverse=True)
    return items


async def post_news(bot: Bot):
    items = fetch_fresh_items()
    if not items:
        print("Нет свежих новостей", flush=True)
        return

    posts = items[:MAX_POSTS_PER_RUN]
    print(f"Найдено {len(items)} свежих, публикую {len(posts)}", flush=True)

    for item in posts:
        text = (
            f"🤖 <b>{item['source']}</b>\n\n"
            f"<b>{item['title']}</b>\n\n"
            f"{item['summary']}\n\n"
            f'🔗 <a href="{item["link"]}">Читать полностью</a>'
        )
        try:
            await bot.send_message(
                CHANNEL_ID,
                text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            seen_urls.add(item["link"])
            print(f"Опубликовано: {item['title'][:60]}", flush=True)
        except Exception as e:
            print(f"Ошибка отправки: {e}", flush=True)
        await asyncio.sleep(3)


async def run_bot():
    try:
        print(f"Старт бота. CHANNEL_ID={CHANNEL_ID}", flush=True)
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        me = await bot.get_me()
        print(f"Токен действителен: @{me.username}", flush=True)

        scheduler = AsyncIOScheduler()
        scheduler.add_job(post_news, "interval", minutes=POST_INTERVAL_MINUTES, args=[bot])
        scheduler.start()
        print("Бот запущен, планировщик работает", flush=True)

        await asyncio.Event().wait()
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", flush=True)


def start_bot_thread():
    asyncio.run(run_bot())


if __name__ == "__main__":
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()
    app.run(host="0.0.0.0", port=PORT)
