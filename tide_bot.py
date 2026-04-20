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


def get_tide(lat, lng, location_name):
    try:
        # Find nearest tide station
        search_url = f"https://tidecheck.com/api/stations/nearest?lat={lat}&lng={lng}"
        headers = {"X-API-Key": TIDE_API_KEY}
        search_res = requests.get(search_url, headers=headers, timeout=10).json()

        if not search_res or "stations" not in search_res:
            return "❌ Could not find tide station."

        station_id = search_res["stations"][0]["id"]
        station_name = search_res["stations"][0].get("name", "Nearest Station")

        # Get today's tide predictions
        tide_url = f"https://tidecheck.com/api/station/{station_id}/tides?days=1&datum=LAT"
        tide_res = requests.get(tide_url, headers=headers, timeout=10).json()

        if "tides" not in tide_res:
            return "❌ Could not fetch tide data."

        today = datetime.now().strftime("%A, %d %B %Y")
        IST = timezone(timedelta(hours=5, minutes=30))

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today}\n"
        message += f"📍 Station: {station_name}\n\n"

        # Get today's date in IST
        today_date = datetime.now(IST).date()

        for tide in tide_res["tides"]:
            if tide.get("type") in ["H", "L"]:
                # Convert UTC time to IST
                utc_time = datetime.fromisoformat(tide["time"].replace("Z", "+00:00"))
                ist_time = utc_time.astimezone(IST)

                # Only show today's tides
                if ist_time.date() == today_date:
                    time_str = ist_time.strftime("%I:%M %p")
                    height = tide.get("height", "")
                    tide_type = "High" if tide["type"] == "H" else "Low"
                    icon = "🔴" if tide["type"] == "H" else "🔵"
                    message += f"{icon} *{tide_type} Tide:* {time_str} — {height}m\n"

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