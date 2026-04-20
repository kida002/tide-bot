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

        # ---- FORMAT 1: Table with State/Time/Height columns (Revadanda style) ----
        tables = soup.find_all("table")
        for table in tables:
            header = table.find("tr")
            if header and "state" in header.get_text().lower() and "time" in header.get_text().lower():
                rows = table.find_all("tr")[1:]
                if rows:
                    for row in rows:
                        cells = row.find_all("td")
                        if len(cells) >= 3:
                            state = cells[0].get_text().strip()
                            time = cells[1].get_text().strip()
                            height_raw = cells[2].get_text().strip()
                            # Keep only metric part e.g. "4.82m"
                            height = re.search(r'[\d.]+m', height_raw)
                            height = height.group(0) if height else height_raw
                            icon = "🔴" if "high" in state.lower() else "🔵"
                            message += f"{icon} *{state} Tide:* {time} — {height}\n"
                    return message

        # ---- FORMAT 2: List items inside table (Daman style) ----
        for table in tables:
            first_td = table.find("td")
            if first_td:
                items = first_td.find_all("li")
                if items:
                    for item in items:
                        text = item.get_text().strip()
                        # Extract: "High 8:37am (4.82m)"
                        match = re.match(r'(High|Low)\s+([\d:apm]+)\s*\(([\d.]+m)', text, re.IGNORECASE)
                        if match:
                            tide_type = match.group(1)
                            time = match.group(2)
                            height = match.group(3) + "m"
                            icon = "🔴" if "high" in tide_type.lower() else "🔵"
                            message += f"{icon} *{tide_type} Tide:* {time} — {height}\n"
                        else:
                            # Try without height
                            match2 = re.match(r'(High|Low)\s+([\d:apm]+)', text, re.IGNORECASE)
                            if match2:
                                tide_type = match2.group(1)
                                time = match2.group(2)
                                icon = "🔴" if "high" in tide_type.lower() else "🔵"
                                message += f"{icon} *{tide_type} Tide:* {time}\n"
                    if "Tide:" in message:
                        return message

        # ---- FORMAT 3: Paragraph fallback ----
        for p in soup.find_all("p"):
            text = p.get_text()
            if "predicted tides today" in text.lower():
                pattern = r'(high|low) tide at\s+([\d:]+(?:am|pm))'
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for tide_type, time in matches:
                        icon = "🔴" if "high" in tide_type.lower() else "🔵"
                        message += f"{icon} *{tide_type.capitalize()} Tide:* {time}\n"
                    return message

        return message + "❌ Could not fetch tide data."

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