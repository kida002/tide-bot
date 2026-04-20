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


def get_tide(url, location_name, ref):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        today = datetime.now().strftime("%A, %d %B %Y")

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today}\n"
        message += f"📍 Reference: {ref}\n\n"

        # Find today's summary paragraph
        paragraphs = soup.find_all("p")
        tide_text = ""
        for p in paragraphs:
            text = p.get_text()
            if "predicted tides today" in text.lower():
                tide_text = text
                break

        if not tide_text:
            return message + "❌ Could not fetch tide data."

        # Extract high and low tides using regex
        # Pattern: "high tide at TIME" or "low tide at TIME"
        highs = re.findall(r'high tide at\s+([\d:apm]+)', tide_text, re.IGNORECASE)
        lows = re.findall(r'low tide at\s+([\d:apm]+)', tide_text, re.IGNORECASE)

        # Also find heights from table
        table = soup.find("table")
        heights = []
        if table:
            first_td = table.find("td")
            if first_td:
                items = first_td.find_all("li")
                for item in items:
                    text = item.get_text().strip()
                    # Extract height like (4.82m)
                    height_match = re.search(r'\(([\d.]+m)', text)
                    if height_match:
                        heights.append(height_match.group(1))

        # Build tide list in order from table
        if table:
            first_td = table.find("td")
            if first_td:
                items = first_td.find_all("li")
                if items:
                    for item in items:
                        text = item.get_text().strip()
                        # Extract time and height
                        time_match = re.search(r'([\d:]+(?:am|pm))', text, re.IGNORECASE)
                        height_match = re.search(r'\(([\d.]+m)', text)
                        tide_type = "High" if "High" in text else "Low"
                        icon = "🔴" if tide_type == "High" else "🔵"

                        time = time_match.group(1) if time_match else "N/A"
                        height = height_match.group(1) if height_match else ""

                        message += f"{icon} *{tide_type} Tide:* {time}"
                        if height:
                            message += f" — {height}"
                        message += "\n"
                    return message

        # Fallback: use paragraph data
        if highs or lows:
            all_tides = []
            for h in highs:
                all_tides.append(("High", h))
            for l in lows:
                all_tides.append(("Low", l))

            for tide_type, time in all_tides:
                icon = "🔴" if tide_type == "High" else "🔵"
                message += f"{icon} *{tide_type} Tide:* {time}\n"

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