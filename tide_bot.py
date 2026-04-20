import os
import requests
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# 🔐 ENV
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TIDE_API_KEY = os.environ.get("tide_key")

# 📍 Locations
locations = {
    "kundalika": {"name": "Kundalika", "lat": 18.45, "lng": 73.20},
    "bankot": {"name": "Bankot Creek Bridge", "lat": 17.98, "lng": 73.03},
    "jaigarh": {"name": "JSW Jaigarh Port", "lat": 16.59, "lng": 73.35},
    "daman": {"name": "Daman (Jampur Beach)", "lat": 20.41, "lng": 72.83}
}

# 🇮🇳 IST
IST = timezone(timedelta(hours=5, minutes=30))

# 🧠 CACHE (daily)
cache = {}


def get_tide(lat, lng, location_name):
    try:
        today_key = datetime.now(IST).strftime("%Y-%m-%d")
        cache_key = f"{lat},{lng}_{today_key}"

        # ✅ USE CACHE
        if cache_key in cache:
            print("⚡ Using cached data")
            return cache[cache_key]

        print("🌐 Calling WorldTides API")

        url = f"https://www.worldtides.info/api/v3?extremes&lat={lat}&lon={lng}&days=2&key={TIDE_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()

        extremes = data.get("extremes", [])
        station = data.get("station", location_name)

        if not extremes:
            return f"⚠️ No tide data for {location_name}"

        now = datetime.now(IST)
        today = now.date()
        today_str = now.strftime("%A, %d %B %Y")

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today_str}\n\n"

        # 🔥 Convert all tides
        tides = []
        for tide in extremes:
            utc_time = datetime.fromtimestamp(tide["dt"], tz=timezone.utc)
            ist_time = utc_time.astimezone(IST)
            tides.append((ist_time, tide["type"], tide["height"]))

        # sort
        tides.sort(key=lambda x: x[0])

        # 🔥 take nearest 4 tides around today
        today_tides = [t for t in tides if t[0].date() == today]

        if len(today_tides) < 4:
            for t in tides:
                if t not in today_tides:
                    today_tides.append(t)
                if len(today_tides) >= 4:
                    break

        today_tides.sort(key=lambda x: x[0])
        final_tides = today_tides[:4]

        # 🔥 clean format
        for t in final_tides:
            time_str = t[0].strftime("%I:%M %p")
            icon = "🔴" if t[1] == "High" else "🔵"
            message += f"{icon} {t[1]} Tide — {time_str}\n"

        # 💾 SAVE CACHE
        cache[cache_key] = message

        return message

    except Exception as e:
        return f"❌ Error: {str(e)}"


# 🤖 /tide
async def tide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📍 Kundalika", callback_data="kundalika")],
        [InlineKeyboardButton("📍 Bankot Creek Bridge", callback_data="bankot")],
        [InlineKeyboardButton("📍 JSW Jaigarh Port", callback_data="jaigarh")],
        [InlineKeyboardButton("📍 Daman (Jampur Beach)", callback_data="daman")]
    ]

    await update.message.reply_text(
        "🌊 *Select Location:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# 🖱 click
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    loc = locations[query.data]

    await query.edit_message_text("⏳ Fetching...")

    result = get_tide(loc["lat"], loc["lng"], loc["name"])

    await query.edit_message_text(result, parse_mode="Markdown")


# 🚀 RUN
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("tide", tide))
app.add_handler(CallbackQueryHandler(button_click))

print("✅ Bot running with caching...")
app.run_polling()