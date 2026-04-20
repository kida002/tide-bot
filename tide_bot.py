import os
import requests
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# 🔐 ENV VARIABLES
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TIDE_API_KEY = os.environ.get("tide_key")  # your Railway variable

# 📍 Locations
locations = {
    "kundalika": {"name": "Kundalika", "lat": 18.45, "lng": 73.20},
    "bankot": {"name": "Bankot Creek Bridge", "lat": 17.98, "lng": 73.03},
    "jaigarh": {"name": "JSW Jaigarh Port", "lat": 16.59, "lng": 73.35},
    "daman": {"name": "Daman (Jampur Beach)", "lat": 20.41, "lng": 72.83}
}

# 🇮🇳 IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


def get_tide(lat, lng, location_name):
    try:
        url = f"https://www.worldtides.info/api/v3?extremes&lat={lat}&lon={lng}&days=2&key={TIDE_API_KEY}"

        response = requests.get(url, timeout=10)
        data = response.json()

        extremes = data.get("extremes", [])
        station = data.get("station", location_name)

        if not extremes:
            return f"⚠️ No tide data for {location_name}"

        now = datetime.now(IST)
        today_str = now.strftime("%A, %d %B %Y")

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today_str}\n"
        message += f"📍 Station: {station}\n\n"

        # 🔥 Convert all tides to IST
        tides = []
        for tide in extremes:
            utc_time = datetime.fromtimestamp(tide["dt"], tz=timezone.utc)
            ist_time = utc_time.astimezone(IST)
            tides.append((ist_time, tide["type"], tide["height"]))

        # 🔥 Sort all tides
        tides.sort(key=lambda x: x[0])

        # 🔥 Find closest index to NOW
        closest_index = min(range(len(tides)), key=lambda i: abs(tides[i][0] - now))

        # 🔥 Take 2 before + 2 after → always 4 tides
        start = max(0, closest_index - 2)
        selected = tides[start:start + 4]

        # 🔥 If less than 4, extend
        if len(selected) < 4:
            selected = tides[:4]

        # 🔥 Print result
        for ist_time, tide_type, height in selected:
            time_formatted = ist_time.strftime("%I:%M %p")
            date_formatted = ist_time.strftime("%d %b")
            icon = "🔴" if tide_type == "High" else "🔵"

            message += f"{icon} *{tide_type} Tide:* {time_formatted} ({date_formatted}) — {round(height,3)}m\n"

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