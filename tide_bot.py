#!/usr/bin/env python3
import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
TIDE_API_KEY = os.getenv("TIDE_API_KEY")
CACHE_FILE = "tide_data.json"

# Location coordinates
LOCATIONS = {
    "Kundalika": {"lat": 18.45, "lon": 73.20},
    "Bankot Creek Bridge": {"lat": 17.98, "lon": 73.03},
    "JSW Jaigarh Port": {"lat": 16.59, "lon": 73.35},
    "Daman Jampur Beach": {"lat": 20.41, "lon": 72.83}
}

def load_cache():
    """Load cached tide data from file"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Cache load error: {e}")
    return {}

def save_cache(data):
    """Save tide data to cache file"""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Cache saved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"⚠️ Cache save error: {e}")

def fetch_weekly_tides(location_name):
    """Fetch 7 days of tide data from WorldTides API"""
    loc = LOCATIONS[location_name]
    url = "https://www.worldtides.info/api/v3"
    
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)
    
    params = {
        "extremes": "",
        "lat": loc["lat"],
        "lon": loc["lon"],
        "key": TIDE_API_KEY,
        "start": int(start_date.timestamp()),
        "length": 604800  # 7 days in seconds
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "extremes" in data:
            print(f"✅ Fetched 7-day data for {location_name}")
            return data["extremes"]
        else:
            print(f"⚠️ No extremes data for {location_name}")
            return None
    except Exception as e:
        print(f"❌ API fetch error for {location_name}: {e}")
        return None

def format_tide_message(extremes, location_name, target_date):
    """Format tide data for a specific date"""
    if not extremes:
        return f"⚠️ No tide data available for {location_name}"
    
    # Filter extremes for target date
    day_extremes = []
    for ext in extremes:
        dt = datetime.fromtimestamp(ext["dt"])
        if dt.date() == target_date:
            day_extremes.append(ext)
    
    if not day_extremes:
        return f"📅 No tide data for {target_date.strftime('%d %b %Y')} at {location_name}"
    
    # Build message
    msg = f"🌊 *Tide Times - {location_name}*\n"
    msg += f"📅 {target_date.strftime('%A, %d %B %Y')}\n\n"
    
    for ext in day_extremes:
        dt = datetime.fromtimestamp(ext["dt"])
        time_str = dt.strftime("%I:%M %p")
        height = ext.get("height", 0)
        tide_type = "🔴 High Tide" if ext["type"] == "High" else "🔵 Low Tide"
        msg += f"{tide_type}: *{time_str}* ({height:.2f}m)\n"
    
    return msg

def update_cache_if_needed():
    """Check and update cache if older than 7 days"""
    cache = load_cache()
    now = datetime.now()
    
    for location_name in LOCATIONS.keys():
        needs_update = False
        
        if location_name not in cache:
            needs_update = True
            print(f"🔄 No cache for {location_name}")
        else:
            cache_date = datetime.fromisoformat(cache[location_name]["fetch_date"])
            age_days = (now - cache_date).days
            
            if age_days >= 7:
                needs_update = True
                print(f"🔄 Cache expired for {location_name} ({age_days} days old)")
        
        if needs_update:
            print(f"📡 Fetching fresh data for {location_name}...")
            extremes = fetch_weekly_tides(location_name)
            
            if extremes:
                # Pre-format messages for next 7 days
                daily_messages = {}
                for i in range(7):
                    target = (now + timedelta(days=i)).date()
                    daily_messages[target.isoformat()] = format_tide_message(extremes, location_name, target)
                
                cache[location_name] = {
                    "fetch_date": now.isoformat(),
                    "raw_extremes": extremes,
                    "daily_messages": daily_messages
                }
    
    save_cache(cache)
    return cache

async def tide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tide command - show location buttons"""
    print(f"📥 /tide command received from user {update.effective_user.id}")
    
    keyboard = [
        [InlineKeyboardButton(loc, callback_data=loc)] 
        for loc in LOCATIONS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌊 *Select a location for tide information:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    print("✅ Location buttons sent")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    location_name = query.data
    print(f"📥 Button clicked: {location_name}")
    
    # Update cache if needed
    cache = update_cache_if_needed()
    
    # Get today's message
    today = datetime.now().date().isoformat()
    
    if location_name in cache and "daily_messages" in cache[location_name]:
        message = cache[location_name]["daily_messages"].get(today)
        if message:
            await query.edit_message_text(text=message, parse_mode="Markdown")
            print(f"✅ Tide data sent for {location_name}")
        else:
            await query.edit_message_text(text=f"⚠️ No tide data available for today at {location_name}")
    else:
        await query.edit_message_text(text=f"⚠️ Cache error for {location_name}. Please try again.")

async def post_init(application: Application):
    """Called after bot initialization - delete webhook"""
    print("🔧 Removing any existing webhooks...")
    await application.bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook cleared - using polling mode")

def main():
    """Main function - Replit compatible"""
    print("\n" + "="*50)
    print("🌊 ASHOKA TIDE INDICATOR BOT")
    print("="*50)
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found in environment!")
        print("Add it in Replit Secrets: BOT_TOKEN")
        return
    
    if not TIDE_API_KEY:
        print("❌ tide_key not found in environment!")
        print("Add it in Replit Secrets: tide_key")
        return
    
    print(f"✅ BOT_TOKEN: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")
    print(f"✅ tide_key: {TIDE_API_KEY[:10]}...{TIDE_API_KEY[-10:]}")
    
    # Create event loop if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Build application
    print("\n🔨 Building bot application...")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Add handlers
    app.add_handler(CommandHandler("tide", tide))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("✅ Handlers registered")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("\n🟢 Bot is now RUNNING and listening for /tide commands...")
    print("="*50 + "\n")
    
    # Run bot with polling
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )

if __name__ == "__main__":
    main()