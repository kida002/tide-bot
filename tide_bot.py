import os
import requests
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TIDE_API_KEY = os.environ.get("TIDE_API_KEY")

# 📍 Locations with coordinates
locations = {
    "kundalika": {
        "name": "Kundalika",
        "lat": 18.45,
        "lng": 73.20
    },
    "bankot": {
        "name": "Bankot Creek Bridge",
        "lat": 17.98,
        "lng": 73.03
    },
    "jaigarh": {
        "name": "JSW Jaigarh Port",
        "lat": 16.59,
        "lng": 73.35
    },
    "daman": {
        "name": "Daman (Jampur Beach)",
        "lat": 20.41,
        "lng": 72.83
    }
}

IST = timezone(timedelta(hours=5, minutes=30))


def get_tide(lat, lng, location_name):
    try:
        headers = {"X-API-Key": TIDE_API_KEY}

        # Step 1 — Find nearest station
        search_url = f"https://tidecheck.com/api/stations/nearest?lat={lat}&lng={lng}"
        search_res = requests.get(search_url, headers=headers, timeout=10).json()

        # Get station ID from response
        stations = search_res.get("stations", [])
        if not stations:
            return f"❌ No tide station found near {location_name}."

        station_id = stations[0]["id"]
        station_name = stations[0].get("name", "Nearest Station")

        # Step 2 — Get tide predictions
        tide_url = f"https://tidecheck.com/api/station/{station_id}/tides?days=1&datum=LAT"
        tide_res = requests.get(tide_url, headers=headers, timeout=10).json()

        # Get extremes from response
        extremes = tide_res.get("extremes", [])
        if not extremes:
            return f"❌ No tide data found for {location_name}."

        today = datetime.now(IST).strftime("%A, %d %B %Y")
        today_date = datetime.now(IST).date()

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today}\n"
        message += f"📍 Station: {station_name}\n\n"

        found = False
        for extreme in extremes:
            tide_type = extreme.get("type", "")
            time_str = extreme.get("time", "")
            height = extreme.get("height", "")

            # Convert UTC to IST
            utc_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            ist_time = utc_time.astimezone(IST)

            # Only today's tides
            if ist_time.date() == today_date:
                found = True
                time_formatted = ist_time.strftime("%I:%M %p")
                icon = "🔴" if tide_type == "high" else "🔵"
                tide_label = "High" if tide_type == "high" else "Low"
                message += f"{icon} *{tide_label} Tide:* {time_formatted} — {height}m\n"

        if not found:
            message += "❌ No tides found for today."

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


# 🖱 Button click handler
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

print("Tide bot started...")
app.run_polling()