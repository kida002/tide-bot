import os
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

        # Find today's tide table — first table on the page
        tables = soup.find_all("table")
        today_table = None
        for table in tables:
            headers_row = table.find("tr")
            if headers_row:
                headers_text = headers_row.get_text().lower()
                if "state" in headers_text and "time" in headers_text:
                    today_table = table
                    break

        if not today_table:
            return message + "❌ Could not fetch tide data."

        rows = today_table.find_all("tr")[1:]  # skip header row
        if not rows:
            return message + "❌ No tide data found."

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                state = cells[0].get_text().strip()
                time = cells[1].get_text().strip()
                height = cells[2].get_text().strip()
                # Clean height — keep only metric (e.g. 4.82m)
                height_clean = height.split("m")[0] + "m" if "m" in height else height

                icon = "🔴" if "high" in state.lower() else "🔵"
                message += f"{icon} *{state} Tide:* {time} — {height_clean}\n"

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