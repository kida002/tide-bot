import os
import json
import requests
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 🔐 ENV
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TIDE_API_KEY = os.environ.get("tide_key")

# 📍 Locations
locations = {
    "kundalika": {"name": "Kundalika", "lat": 18.45, "lng": 73.20},
    "bankot":    {"name": "Bankot Creek Bridge", "lat": 17.98, "lng": 73.03},
    "jaigarh":   {"name": "JSW Jaigarh Port", "lat": 16.59, "lng": 73.35},
    "daman":     {"name": "Daman (Jampur Beach)", "lat": 20.41, "lng": 72.83}
}

# 🇮🇳 IST
IST = timezone(timedelta(hours=5, minutes=30))

# 📂 File storage
DATA_FILE = "tide_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def get_week_key(lat, lng):
    now = datetime.now(IST)
    week_str = now.strftime("%Y-W%W")
    return f"{lat},{lng}_{week_str}"


def get_tide(lat, lng, location_name):
    try:
        now = datetime.now(IST)
        today = now.date()

        week_key = get_week_key(lat, lng)
        day_key = f"{week_key}_{today.strftime('%Y-%m-%d')}"

        data_store = load_data()

        # ✅ Use today's already-formatted message if saved
        if day_key in data_store:
            print(f"⚡ Using saved data for {today} (no API call)")
            return data_store[day_key]

        # 🔍 Check if we already have raw 7-day data for this week
        raw_key = f"{week_key}_raw"

        if raw_key in data_store:
            print(f"📦 Using saved raw weekly data, extracting {today}")
            all_tides = data_store[raw_key]
        else:
            # 🌐 Call API — only once per week per location!
            print(f"🌐 Calling WorldTides API for week {week_key}")

            url = f"https://www.worldtides.info/api/v3?extremes&lat={lat}&lon={lng}&days=7&key={TIDE_API_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()

            extremes = data.get("extremes", [])
            if not extremes:
                return f"⚠️ No tide data for {location_name}"

            # 💾 Save raw 7-day data
            all_tides = []
            for tide in extremes:
                utc_time = datetime.fromtimestamp(tide["dt"], tz=timezone.utc)
                ist_time = utc_time.astimezone(IST)
                all_tides.append({
                    "time": ist_time.isoformat(),
                    "type": tide["type"],
                    "height": tide["height"]
                })

            data_store[raw_key] = all_tides
            save_data(data_store)
            print(f"✅ Saved 7 days of raw data for {location_name}")

        # 🔄 Parse saved tides
        tides = []
        for t in all_tides:
            ist_time = datetime.fromisoformat(t["time"])
            tides.append((ist_time, t["type"], t["height"]))

        tides.sort(key=lambda x: x[0])

        # 📅 Filter today's tides
        today_tides = [t for t in tides if t[0].date() == today]

        # 🔥 Ensure 4 tides
        if len(today_tides) < 4:
            for t in tides:
                if t not in today_tides:
                    today_tides.append(t)
                if len(today_tides) >= 4:
                    break

        today_tides.sort(key=lambda x: x[0])
        final_tides = today_tides[:4]

        # 🎯 Format message
        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {now.strftime('%A, %d %B %Y')}\n\n"

        for t in final_tides:
            time_str = t[0].strftime("%I:%M %p")
            date_str = t[0].strftime("%d %b")
            height = round(t[2], 3)
            icon = "🔴" if t[1] == "High" else "🔵"
            message += f"{icon} {t[1]} Tide: {time_str} ({date_str}) — {height}m\n"

        # 💾 Save today's formatted message
        data_store[day_key] = message
        save_data(data_store)

        return message

    except Exception as e:
        return f"❌ Error: {str(e)}"


# 🤖 /tide command
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


# 🚀 MAIN
if __name__ == "__main__":
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("tide", tide))
    app.add_handler(CallbackQueryHandler(button_click))
    print("✅ Bot running with weekly caching — 4 credits/week for all 4 locations...")
    app.run_polling()