import os
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# 📍 Locations and their URLs
locations = {
    "kundalika": {
        "name": "Kundalika",
        "url": "https://www.tideschart.com/India/Maharashtra/Raigarh/Bankot/"
    },
    "bankot": {
        "name": "Bankot Creek Bridge",
        "url": "https://www.tideschart.com/India/Maharashtra/Raigarh/Bankot/"
    },
    "jaigarh": {
        "name": "JSW Jaigarh Port",
        "url": "https://www.tideschart.com/India/Maharashtra/Ratnagiri/Jaigarh/"
    },
    "daman": {
        "name": "Daman (Jampur Beach)",
        "url": "https://www.tidetime.org/asia/india/daman.htm"
    }
}


# 🌊 Scrape tide data from tideschart.com
def get_tide_tideschart(url, location_name):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # Find today's tide table
        table = soup.find("table")
        if not table:
            return "❌ Could not fetch tide data."

        rows = table.find_all("tr")
        if len(rows) < 2:
            return "❌ No tide data found."

        # Get today's first row
        today_row = rows[1]
        cells = today_row.find_all("td")

        if len(cells) < 4:
            return "❌ Tide data format changed."

        from datetime import datetime
        today = datetime.now().strftime("%A, %d %B %Y")

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today}\n\n"

        tides = []
        for cell in cells[:4]:
            text = cell.get_text(separator=" ").strip()
            if text:
                tides.append(text)

        labels = ["1st Tide", "2nd Tide", "3rd Tide", "4th Tide"]
        icons = ["🔴", "🔵", "🔴", "🔵"]

        for i, tide in enumerate(tides):
            if i < len(labels):
                message += f"{icons[i]} {labels[i]}: {tide}\n"

        return message

    except Exception as e:
        return f"❌ Error fetching data: {str(e)}"


# 🌊 Scrape tide data from tidetime.org (Daman)
def get_tide_tidetime(url, location_name):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        from datetime import datetime
        today = datetime.now().strftime("%A, %d %B %Y")

        message = f"🌊 *Tide Times - {location_name}*\n"
        message += f"📅 {today}\n\n"

        # Find tide table
        table = soup.find("table", {"class": "tide-table"})
        if not table:
            table = soup.find("table")

        if not table:
            return "❌ Could not fetch tide data."

        rows = table.find_all("tr")
        for row in rows[1:5]:
            cells = row.find_all("td")
            if len(cells) >= 2:
                time = cells[0].get_text().strip()
                height = cells[1].get_text().strip()
                tide_type = cells[2].get_text().strip() if len(cells) > 2 else ""
                icon = "🔴" if "High" in tide_type else "🔵"
                message += f"{icon} {tide_type}: {time} — {height}\n"

        return message

    except Exception as e:
        return f"❌ Error fetching data: {str(e)}"


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

    if location_key == "daman":
        message = get_tide_tidetime(location["url"], location["name"])
    else:
        message = get_tide_tideschart(location["url"], location["name"])

    await query.edit_message_text(message, parse_mode="Markdown")


# 🚀 MAIN
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("tide", tide))
app.add_handler(CallbackQueryHandler(button_click))

print("Tide bot started...")
app.run_polling()