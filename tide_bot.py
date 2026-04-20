import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# 📍 Locations using tidetime.org
locations = {
    "kundalika": {
        "name": "Kundalika",
        "url": "https://www.tidetime.org/asia/india/revadanda.htm",
        "ref": "Revadanda"
    },
    "bankot": {
        "name": "Bankot Creek Bridge",
        "url": "https://www.tidetime.org/asia/india/revadanda.htm",
        "ref": "Revadanda"
    },
    "jaigarh": {
        "name": "JSW Jaigarh Port",
        "url": "https://www.tidetime.org/asia/india/ratnagiri.htm",
        "ref": "Ratnagiri"
    },
    "daman": {
        "name": "Daman (Jampur Beach)",
        "url": "https://www.tidetime.org/asia/india/daman.htm",
        "ref": "Daman"
    }
}


# 🌊 Scrape tide data from tidetime.org
def get_tide(url, location_name, ref):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        today = datetime.now().strftime("%A, %d %B %Y")

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today}\n"
        message += f"📍 Reference: {ref}\n\n"

        # Find the paragraph that has today's tide summary
        paragraphs = soup.find_all("p")
        tide_para = None
        for p in paragraphs:
            text = p.get_text()
            if "predicted tides today" in text.lower():
                tide_para = text
                break

        if tide_para:
            message += f"ℹ️ {tide_para.strip()}\n\n"

        # Also get table data for detailed view
        table = soup.find("table")
        if table:
            first_td = table.find("td")
            if first_td:
                items = first_td.find_all("li")
                if items:
                    for item in items:
                        text = item.get_text().strip()
                        if "High" in text:
                            message += f"🔴 {text}\n"
                        elif "Low" in text:
                            message += f"🔵 {text}\n"
                    return message

        if tide_para:
            return message

        return "❌ Could not fetch tide data."

    except Exception as e:
        return f"❌ Error: {str(e)}"


# 🤖 /tide command — show 4 buttons
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