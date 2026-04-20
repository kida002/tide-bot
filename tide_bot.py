import os
import requests
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# 🔐 ENV VARIABLES
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TIDE_API_KEY = os.environ.get("TIDE_API_KEY")

# 📍 Locations
locations = {
    "kundalika": {"name": "Kundalika", "lat": 18.45, "lng": 73.20},
    "bankot": {"name": "Bankot Creek Bridge", "lat": 17.98, "lng": 73.03},
    "jaigarh": {"name": "JSW Jaigarh Port", "lat": 16.59, "lng": 73.35},
    "daman": {"name": "Daman (Jampur Beach)", "lat": 20.41, "lng": 72.83}
}

# 🇮🇳 IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# 🧠 Cache
cache = {}

def get_tide(lat, lng, location_name):
    try:
        url = f"https://www.worldtides.info/api/v3?extremes&lat={lat}&lon={lng}&key={TIDE_API_KEY}"

        response = requests.get(url, timeout=10)

        print("STATUS:", response.status_code)
        print("RAW RESPONSE:", response.text)  # 🔥 DEBUG

        data = response.json()

        # 🔥 IMPORTANT FIX
        if "extremes" not in data or not data["extremes"]:
            return f"❌ API returned no data for {location_name}.\nCheck logs."

        extremes = data["extremes"]

        message = f"🌊 *Tide Times - {location_name}*\n\n"

        for tide in extremes[:6]:
            tide_type = tide.get("type")
            timestamp = tide.get("dt")
            height = tide.get("height")

            utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            ist_time = utc_time.astimezone(IST)

            time_formatted = ist_time.strftime("%I:%M %p")
            date_formatted = ist_time.strftime("%d %b")

            icon = "🔴" if tide_type == "High" else "🔵"

            message += f"{icon} {tide_type} Tide: {time_formatted} ({date_formatted}) — {height}m\n"

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

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌊 *Select Location for Tide Times:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


# 🖱 Button handler
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    location_key = query.data
    location = locations[location_key]

    await query.edit_message_text("⏳ Fetching tide data...")

    message = get_tide(location["lat"], location["lng"], location["name"])

    await query.edit_message_text(message, parse_mode="Markdown")


# 🚀 MAIN
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("tide", tide))
app.add_handler(CallbackQueryHandler(button_click))

print("✅ Tide bot started...")
app.run_polling()