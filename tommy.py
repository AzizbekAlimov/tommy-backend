"""
TOMMY BOT — Single complete file
Bot asks user step-by-step (like WebApp)
Admin panel + Tashkent timezone
"""
import os, io, re, json, time, sqlite3, asyncio, logging, colorsys, threading
from io import BytesIO
from datetime import datetime, timezone, timedelta

from PIL import Image
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.request import HTTPXRequest

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ============================================================
# SETTINGS
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@TommyXcheat2")
OWNER_FIXED = "@Tommy_1727"
ADMIN_ID = 7383782449
PORT = int(os.getenv("PORT", 3000))

# ✅ TASHKENT TIMEZONE (UTC+5)
TZ_TASHKENT = timezone(timedelta(hours=5))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini AI connected")

# Conversation states
PHOTO, PLAYER_ID, CLASSIC, ULTIMATE, KILLS = range(5)

# ============================================================
# HTML (WebApp)
# ============================================================
INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>TOMMY BOT</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh;padding:16px;background:#0a0820;overflow-x:hidden}
.container{position:relative;z-index:1;max-width:500px;margin:0 auto}
.header{text-align:center;padding:55px 0 30px}
.header .logo{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#4CAF50,#2196F3);display:flex;align-items:center;justify-content:center;margin:0 auto 15px;font-size:40px}
.header h1{color:#4CAF50;font-size:26px;font-weight:800}
.header p{color:#aaa;font-size:13px}
.card{background:rgba(255,255,255,0.06);border-radius:18px;padding:18px;margin-bottom:14px;border:1px solid rgba(255,255,255,0.08)}
.card-title{color:#4CAF50;font-size:15px;font-weight:700;margin-bottom:14px;text-transform:uppercase}
.info-row{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid rgba(255,255,255,0.06)}
.info-row:last-child{border-bottom:none}
.info-label{color:#999;font-size:13px}
.info-value{color:#fff;font-weight:600;font-size:13px;text-align:right;max-width:60%}
.info-value.green{color:#4CAF50}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">🎮</div>
    <h1>TOMMY BOT</h1>
    <p>PUBG Mobile Statistics Panel</p>
  </div>
  <div class="card">
    <div class="card-title">👤 Your Information</div>
    <div class="info-row"><span class="info-label">Name:</span><span class="info-value" id="user-name">Loading...</span></div>
    <div class="info-row"><span class="info-label">Username:</span><span class="info-value green" id="user-username">-</span></div>
    <div class="info-row"><span class="info-label">Telegram ID:</span><span class="info-value" id="user-id">-</span></div>
  </div>
</div>
<script>
const tg=window.Telegram.WebApp;tg.expand();tg.ready();tg.setHeaderColor('#0a0820');tg.setBackgroundColor('#0a0820');
const user=tg.initDataUnsafe.user;
if(user){const fn=((user.first_name||'')+' '+(user.last_name||'')).trim();document.getElementById('user-name').innerText=fn||`User #${user.id}`;document.getElementById('user-username').innerText=user.username?'@'+user.username:'—';document.getElementById('user-id').innerText=user.id;}
</script>
</body>
</html>'''

# ============================================================
# SQLITE
# ============================================================
def init_db():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, player_id TEXT, classic_rank TEXT, ultimate_rank TEXT, kills TEXT, created_at TEXT)""")
    conn.commit(); conn.close()

def save_user(uid, username, first_name):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", 
        (uid, username or "", first_name or "", 
         datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def save_post(uid, pid, cr, ur, k):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT INTO posts (user_id,player_id,classic_rank,ultimate_rank,kills,created_at) VALUES (?,?,?,?,?,?)", 
        (uid, pid, cr, ur, k, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def get_users_count():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); n = c.fetchone()[0]; conn.close(); return n

def get_posts_count():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts"); n = c.fetchone()[0]; conn.close(); return n

def get_today_users_count():
    today = datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d")
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", (today + "%",))
    n = c.fetchone()[0]; conn.close(); return n

def get_all_users(limit=30):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, joined_at FROM users ORDER BY joined_at DESC LIMIT ?", (limit,))
    r = c.fetchall(); conn.close(); return r

def get_recent_posts(limit=10):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT user_id, player_id, classic_rank, ultimate_rank, kills, created_at FROM posts ORDER BY id DESC LIMIT ?", (limit,))
    r = c.fetchall(); conn.close(); return r

# ============================================================
# HELPERS
# ============================================================
def hide_id(pid):
    p = str(pid).strip()
    if len(p) <= 6: return p
    return p[:3] + "***" + p[-2:]

def is_valid_player_id(p):
    p = str(p).strip()
    if not p.isdigit() or len(p) != 11: return False
    if p[0] not in ("5","6"): return False
    if len(set(p)) == 1: return False
    return True

def validate_pubg_screenshot(image_bytes):
    try:
        img = Image.open(BytesIO(image_bytes)); img.load()
    except Exception:
        return False, "Could not read image."
    if img.format and img.format.upper() not in ("JPEG","PNG","WEBP","JPG"):
        return False, "Unsupported format."
    w, h = img.size
    if w < 640 or h < 360: return False, "Resolution too low."
    if w <= h: return False, "Landscape only."
    ratio = w/h
    allowed = [1.333,1.5,1.6,1.667,1.778,2.0,2.056,2.111,2.167,2.222,2.333,2.444]
    if not any(abs(ratio-r) <= 0.06 for r in allowed):
        return False, "Wrong screen ratio."
    return True, ""

# ============================================================
# SEND TO TELEGRAM
# ============================================================
def send_to_telegram(image_bytes, caption, mime_type='image/jpeg'):
    try:
        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {'photo': ('screenshot.jpg', image_bytes, mime_type)}
        data = {'chat_id': CHANNEL_ID, 'caption': caption}
        r = requests.post(url, files=files, data=data, timeout=60)
        return r.json()
    except Exception as e:
        return {'ok': False, 'description': str(e)}

# ============================================================
# FLASK
# ============================================================
flask_app = Flask(__name__)
CORS(flask_app, resources={r"/*": {"origins": "*"}})

@flask_app.route('/', methods=['GET'])
def index():
    return Response(INDEX_HTML, mimetype='text/html')

@flask_app.route('/send-feedback', methods=['POST'])
def send_feedback():
    try:
        if 'photo' not in request.files:
            return jsonify({'ok': False, 'description': 'Photo required!'}), 400
        photo = request.files['photo']
        if photo.filename == '': return jsonify({'ok': False, 'description': 'No file'}), 400
        photo_bytes = photo.read()
        if len(photo_bytes) > 5*1024*1024: return jsonify({'ok': False, 'description': 'Too large'}), 400
        caption = request.form.get('caption', '')
        if not caption: return jsonify({'ok': False, 'description': 'Caption required!'}), 400
        tg_res = send_to_telegram(photo_bytes, caption, photo.mimetype or 'image/jpeg')
        return jsonify({'ok': tg_res.get('ok', False), 'description': tg_res.get('description')}), 200 if tg_res.get('ok') else 500
    except Exception as e:
        logger.error(f"❌ Web error: {e}")
        return jsonify({'ok': False, 'description': str(e)}), 500

def run_flask():
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False, threaded=True)

# ============================================================
# TELEGRAM BOT
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    save_user(u.id, u.username, u.first_name)
    context.user_data.clear()
    kb = [
        [InlineKeyboardButton("🏆 RANK STATISTICA", callback_data="rank_start")],
        [InlineKeyboardButton("📞 Contact", callback_data="contact")],
    ]
    await update.message.reply_text(
        "🤖 TOMMY BOT\n\nSend your PUBG Mobile statistics.\nWe'll ask you step by step:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def rank_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.reply_text(
        "🆔 Step 1\n\nSend your PUBG Mobile ID:\n\n"
        "• 11 digits\n• Starts with 5 or 6\n• No identical digits\n\n"
        "Example: 52254689580"
    )
    return PLAYER_ID

async def handle_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.message.text.strip()
    if not is_valid_player_id(pid):
        await update.message.reply_text("❌ Invalid ID!\n\nMust be 11 digits, start with 5/6.\n\nTry again:")
        return PLAYER_ID
    context.user_data['player_id'] = pid
    ranks = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Crown", "Ace", "Ace Master", "Ace Dominator", "Conqueror"]
    kb = []
    for r in ranks:
        kb.append([InlineKeyboardButton(f"🏆 {r}", callback_data=f"classic_{r}")])
    await update.message.reply_text(
        f"✅ ID: {pid}\n\n👑 Step 2\n\nSelect your CLASSIC RANK:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CLASSIC

async def handle_classic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    rank = q.data.replace("classic_", "")
    context.user_data['classic_rank'] = rank
    await q.message.delete()
    ranks = ["Vanguard", "Exceed", "Supreme", "Peerless", "Legend"]
    kb = []
    for r in ranks:
        kb.append([InlineKeyboardButton(f"🏆 {r}", callback_data=f"ultimate_{r}")])
    await q.message.reply_text(
        f"✅ Classic: {rank}\n\n👑 Step 3\n\nSelect your ULTIMATE ROYALE RANK:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return ULTIMATE

async def handle_ultimate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    rank = q.data.replace("ultimate_", "")
    context.user_data['ultimate_rank'] = rank
    await q.message.delete()
    await q.message.reply_text(
        f"✅ Ultimate: {rank}\n\n💀 Step 4\n\nEnter KILLS (1-100):"
    )
    return KILLS

async def handle_kills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kills = update.message.text.strip()
    if not kills.isdigit() or not (1 <= int(kills) <= 100):
        await update.message.reply_text("❌ Enter a number between 1 and 100:")
        return KILLS
    context.user_data['kills'] = kills
    await update.message.reply_text(
        f"✅ Kills: {kills}\n\n📸 Step 5\n\nNow send your PUBG Mobile screenshot:"
    )
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    msg = await update.message.reply_text("⏳ Verifying...")
    try:
        f = await context.bot.get_file(photo.file_id)
        fb = bytes(await f.download_as_bytearray())
        ok, reason = validate_pubg_screenshot(fb)
        if not ok:
            await msg.delete()
            await update.message.reply_text(f"❌ {reason}\n\nPlease send again:")
            return PHOTO

        player_id = context.user_data.get('player_id', '')
        classic_rank = context.user_data.get('classic_rank', 'Unknown')
        ultimate_rank = context.user_data.get('ultimate_rank', 'Unknown')
        kills = context.user_data.get('kills', '0')
        hidden_id = hide_id(player_id)

        user = update.effective_user
        owner_d = f"@{user.username}" if user.username else user.full_name
        now = datetime.now(TZ_TASHKENT)
        time_str = now.strftime('%H:%M  %d.%m.%Y')

        caption = (
            f"👤 OWNER: {owner_d}\n"
            f"🎮 Player ID: {hidden_id}\n"
            f"🏆 CLASSIC RANK: {classic_rank}\n"
            f"🏆 ULTIMATE ROYALE RANK: {ultimate_rank}\n"
            f"🕒 TIME: {time_str}\n"
            f"💀 KILL: {kills}\n\n"
            f"👤 OWNER: {OWNER_FIXED} ✅"
        )

        kb = [
            [InlineKeyboardButton("✅ Send to channel", callback_data="confirm_send")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_post")]
        ]
        await msg.delete()
        context.user_data['photo_id'] = photo.file_id
        context.user_data['caption'] = caption
        await update.message.reply_photo(
            photo=photo.file_id,
            caption=f"🤖 Preview:\n\n{caption}",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Photo: {e}")
        await update.message.reply_text(f"❌ {e}")
        return PHOTO

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    photo_id = context.user_data.get('photo_id')
    caption = context.user_data.get('caption', '')
    if not photo_id:
        await q.message.reply_text("❌ Error: photo not found.")
        return
    try:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=caption)
        user = update.effective_user
        save_post(user.id, context.user_data.get('player_id',''), context.user_data.get('classic_rank',''), context.user_data.get('ultimate_rank',''), context.user_data.get('kills',''))
        await q.message.delete()
        await q.message.reply_text("✅ Sent to channel!")
    except Exception as e:
        await q.message.reply_text(f"❌ Error: {e}\n\nMake sure the bot is admin in the channel.")
    context.user_data.clear()

async def cancel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.delete()
    await q.message.reply_text("❌ Cancelled. Restart with /start.")

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text("Contact: @Tommy_1727")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# ============================================================
# ADMIN STATISTICS (Tashkent time)
# ============================================================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return

    total_users = get_users_count()
    total_posts = get_posts_count()
    today_users = get_today_users_count()

    text = (
        f"📊 <b>BOT STATISTICS</b>\n\n"
        f"👥 Total users: <b>{total_users}</b>\n"
        f"🆕 Today joined: <b>{today_users}</b>\n"
        f"📸 Total posts: <b>{total_posts}</b>\n"
        f"🕒 Time: {datetime.now(TZ_TASHKENT).strftime('%H:%M %d.%m.%Y')}\n\n"
    )

    users = get_all_users(limit=10)
    if users:
        text += f"<b>👤 Last 10 users:</b>\n"
        for uid, un, fn, ja in users:
            if un:
                name = f"@{un}"
            elif fn:
                name = fn
            else:
                name = f"User #{uid}"
            text += f"• {name} — {ja}\n"
    else:
        text += "No users yet.\n"

    posts = get_recent_posts(limit=5)
    if posts:
        text += f"\n<b>📸 Last 5 posts:</b>\n"
        for uid, pid, cr, ur, k, ca in posts:
            text += f"• {hide_id(pid)} — {cr} / {ur} — {k} kills — {ca}\n"

    await update.message.reply_text(text, parse_mode='HTML')

async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return

    users = get_all_users(limit=100)
    if not users:
        await update.message.reply_text("No users yet.")
        return

    text = f"👥 <b>USERS LIST ({len(users)})</b>\n\n"
    for i, (uid, un, fn, ja) in enumerate(users, 1):
        if un:
            name = f"@{un}"
        elif fn:
            name = fn
        else:
            name = f"User #{uid}"
        text += f"{i}. {name} — {ja}\n"

    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='HTML')
    else:
        await update.message.reply_text(text, parse_mode='HTML')

# ============================================================
# START BOT
# ============================================================
def start_bot():
    logger.info("🤖 Bot starting...")
    try:
        req = HTTPXRequest(connection_pool_size=8, connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
        application = Application.builder().token(BOT_TOKEN).request(req).build()

        conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(rank_start, pattern="^rank_start$")],
            states={
                PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_player_id)],
                CLASSIC: [CallbackQueryHandler(handle_classic, pattern="^classic_")],
                ULTIMATE: [CallbackQueryHandler(handle_ultimate, pattern="^ultimate_")],
                KILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_kills)],
                PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            per_message=False,
        )

        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv)
        application.add_handler(CallbackQueryHandler(confirm_send, pattern="^confirm_send$"))
        application.add_handler(CallbackQueryHandler(cancel_post, pattern="^cancel_post$"))
        application.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
        application.add_handler(CommandHandler("admin", admin_stats))
        application.add_handler(CommandHandler("stats", admin_stats))
        application.add_handler(CommandHandler("users", users_list))

        logger.info("🔑 BOT_TOKEN: present")
        logger.info("✅ Bot started (background thread)")

        application.run_polling(stop_signals=None, drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

def main():
    init_db()
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    logger.info(f"🌐 Flask server: port {PORT}")
    run_flask()

if __name__ == "__main__":
    main()
