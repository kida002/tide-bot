import os
import json
import requests
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TIDE_API_KEY = os.environ.get("tide_key")

# 📍 Locations
locations = {
    "kundalika": {"name": "Kundalika", "lat": 18.45, "lng": 73.20},
    "bankot": {"name": "Bankot Creek Bridge", "lat": 17.98, "lng": 73.03},
    "jaigarh": {"name": "JSW Jaigarh Port", "lat": 16.59, "lng": 73.35},
    "daman": {"name": "Daman (Jampur Beach)", "lat": 20.41, "lng": 72.83}
}

IST = timezone(timedelta(hours=5, minutes=30))

DATA_FILE = "tide_data.json"


# 📂 Load file
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


# 💾 Save file
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def get_tide(lat, lng, location_name):
    try:
        today_key = datetime.now(IST).strftime("%Y-%m-%d")
        key = f"{lat},{lng}_{today_key}"

        data_store = load_data()

        # ✅ USE FILE CACHE
        if key in data_store:
            print("⚡ Using saved file data")
            return data_store[key]

        print("🌐 Calling API...")

        url = f"https://www.worldtides.info/api/v3?extremes&lat={lat}&lon={lng}&days=2&key={TIDE_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()

        extremes = data.get("extremes", [])
        if not extremes:
            return f"⚠️ No tide data for {location_name}"

        now = datetime.now(IST)
        today = now.date()

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {now.strftime('%A, %d %B %Y')}\n\n"

        tides = []

        for tide in extremes:
            utc_time = datetime.fromtimestamp(tide["dt"], tz=timezone.utc)
            ist_time = utc_time.astimezone(IST)
            tides.append((ist_time, tide["type"], tide["height"]))

        tides.sort(key=lambda x: x[0])

        today_tides = [t for t in tides if t[0].date() == today]

        # ensure 4 tides
        if len(today_tides) < 4:
            for t in tides:
                if t not in today_tides:
                    today_tides.append(t)
                if len(today_tides) >= 4:
                    break

        today_tides.sort(key=lambda x: x[0])
        final = today_tides[:4]

        for t in final:
            icon = "🔴" if t[1] == "High" else "🔵"
            time_str = t[0].strftime("%I:%M %p")
            message += f"{icon} {t[1]} Tide — {time_str}\n"

        # 💾 SAVE TO FILE
        data_store[key] = message
        save_data(data_store)

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


# 🖱 Button click
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

print("✅ Bot running with FILE caching...")
app.run_polling()