import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

locations = {
    "kundalika": {
        "name": "Kundalika",
        "url": "https://www.tidetime.org/asia/india/revadanda.htm",
        "ref": "Revadanda"
    },
    "bankot": {
        "name": "Bankot Creek Bridge",
        "url": "https://www.tidetime.org/asia/india/srivardhan.htm",
        "ref": "Srivardhan"
    },
    "jaigarh": {
        "name": "JSW Jaigarh Port",
        "url": "https://www.tidetime.org/asia/india/harnai.htm",
        "ref": "Harnai"
    },
    "daman": {
        "name": "Daman (Jampur Beach)",
        "url": "https://www.tidetime.org/asia/india/daman.htm",
        "ref": "Daman"
    }
}


def get_tide(url, location_name, ref):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        today = datetime.now().strftime("%A, %d %B %Y")

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today}\n"
        message += f"📍 Reference: {ref}\n\n"

        # Find today's tide summary paragraph
        tide_text = ""
        for p in soup.find_all("p"):
            text = p.get_text()
            if "predicted tides today" in text.lower():
                tide_text = text
                break

        if not tide_text:
            return message + "❌ Could not fetch tide data."

        # Parse tides from paragraph using regex
        # matches like: "high tide at 8:37am" or "low tide at 1:51am"
        pattern = r'(high|low) tide at\s+([\d:]+(?:am|pm))'
        matches = re.findall(pattern, tide_text, re.IGNORECASE)

        # Also get heights from paragraph like "(4.82m)"
        height_pattern = r'\(([\d.]+m[\d.ft]*)\)'
        heights = re.findall(height_pattern, tide_text)

        if not matches:
            return message + "❌ Could not parse tide data."

        for i, (tide_type, time) in enumerate(matches):
            icon = "🔴" if tide_type.lower() == "high" else "🔵"
            height = heights[i] if i < len(heights) else ""
            if height:
                message += f"{icon} *{tide_type.capitalize()} Tide:* {time} — {height}\n"
            else:
                message += f"{icon} *{tide_type.capitalize()} Tide:* {time}\n"

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

    message = get_tide(location["url"], location["name"], location["ref"])
    await query.edit_message_text(message, parse_mode="Markdown")


# 🚀 MAIN
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("tide", tide))
app.add_handler(CallbackQueryHandler(button_click))

print("Tide bot started...")
app.run_polling()