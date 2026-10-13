"""
TOMMY BOT — Admin-only commands in groups
"""
import os, io, re, json, time, sqlite3, asyncio, logging, colorsys, threading
from io import BytesIO
from datetime import datetime, timezone, timedelta

from PIL import Image
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ChatPermissions, BotCommand, BotCommandScopeChatAdministrators,
    BotCommandScopeAllPrivateChats, BotCommandScopeDefault
)
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

TZ_TASHKENT = timezone(timedelta(hours=5))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini AI connected")

PHOTO, PLAYER_ID, CLASSIC, ULTIMATE, KILLS = range(5)

# ============================================================
# HTML (WebApp) — minimal
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
    c.execute("""CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at TEXT)""")
    conn.commit(); conn.close()

def save_user(uid, username, first_name):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", 
        (uid, username or "", first_name or "", datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
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

def ban_user(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO banned_users VALUES (?, ?)", 
        (uid, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def unban_user(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("DELETE FROM banned_users WHERE user_id = ?", (uid,))
    conn.commit(); conn.close()

def is_banned(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (uid,))
    r = c.fetchone(); conn.close()
    return r is not None

def get_banned_users():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT user_id, banned_at FROM banned_users ORDER BY banned_at DESC")
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

def parse_duration(s):
    s = str(s).strip().lower()
    if not s: return None
    try:
        num = int(s[:-1]); unit = s[-1]
    except (ValueError, IndexError):
        try:
            num = int(s); unit = 'm'
        except ValueError:
            return None
    if num <= 0: return None
    if unit == 's': return timedelta(seconds=num)
    if unit == 'm': return timedelta(minutes=num)
    if unit == 'h': return timedelta(hours=num)
    if unit == 'd': return timedelta(days=num)
    if unit == 'w': return timedelta(weeks=num)
    return None

def human_duration(td):
    total = int(td.total_seconds())
    if total < 60: return f"{total} seconds"
    if total < 3600: return f"{total // 60} minutes"
    if total < 86400: return f"{total // 3600} hours"
    if total < 604800: return f"{total // 86400} days"
    return f"{total // 604800} weeks"

# ============================================================
# ✅ ADMIN CHECK HELPER
# ============================================================
async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True if the user is admin/creator of the group."""
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ('group', 'supergroup'):
        return False
    try:
        member = await chat.get_member(user.id)
        return member.status in ('administrator', 'creator')
    except Exception:
        return False

async def check_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is admin. If not, send error message and return False."""
    if not await is_group_admin(update, context):
        await update.message.reply_text(
            "🚫 <b>This command is only for group admins.</b>\n\n"
            "You don't have permission to use this command.",
            parse_mode='HTML'
        )
        return False
    return True

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
# TELEGRAM BOT — USER COMMANDS
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if update.effective_chat.type == 'private' and is_banned(u.id):
        await update.message.reply_text(
            "🚫 <b>You have been banned from using this bot.</b>\n\n"
            "Contact: @Tommy_1727",
            parse_mode='HTML'
        )
        return
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
        await update.message.reply_text("❌ Invalid ID!\n\nTry again:")
        return PLAYER_ID
    context.user_data['player_id'] = pid
    ranks = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Crown", "Ace", "Ace Master", "Ace Dominator", "Conqueror"]
    kb = [[InlineKeyboardButton(f"🏆 {r}", callback_data=f"classic_{r}")] for r in ranks]
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
    kb = [[InlineKeyboardButton(f"🏆 {r}", callback_data=f"ultimate_{r}")] for r in ranks]
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
    await q.message.reply_text(f"✅ Ultimate: {rank}\n\n💀 Step 4\n\nEnter KILLS (1-100):")
    return KILLS

async def handle_kills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kills = update.message.text.strip()
    if not kills.isdigit() or not (1 <= int(kills) <= 100):
        await update.message.reply_text("❌ Enter a number between 1 and 100:")
        return KILLS
    context.user_data['kills'] = kills
    await update.message.reply_text(f"✅ Kills: {kills}\n\n📸 Step 5\n\nSend your PUBG Mobile screenshot:")
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
        await q.message.reply_text(f"❌ Error: {e}")
    context.user_data.clear()

async def cancel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.delete()
    await q.message.reply_text("❌ Cancelled.")

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text("Contact: @Tommy_1727")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['broadcast_mode'] = False
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# ============================================================
# ADMIN COMMANDS (only owner ID)
# ============================================================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return

    total_users = get_users_count()
    total_posts = get_posts_count()
    today_users = get_today_users_count()
    banned_count = len(get_banned_users())

    text = (
        f"📊 <b>BOT STATISTICS</b>\n\n"
        f"👥 Total users: <b>{total_users}</b>\n"
        f"🆕 Today joined: <b>{today_users}</b>\n"
        f"📸 Total posts: <b>{total_posts}</b>\n"
        f"🚫 Banned: <b>{banned_count}</b>\n"
        f"🕒 Time: {datetime.now(TZ_TASHKENT).strftime('%H:%M %d.%m.%Y')}\n\n"
    )

    users = get_all_users(limit=10)
    if users:
        text += f"<b>👤 Last 10 users:</b>\n"
        for uid, un, fn, ja in users:
            name = f"@{un}" if un else (fn if fn else "User")
            text += f"• {name} — {ja}\n"

    posts = get_recent_posts(limit=5)
    if posts:
        text += f"\n<b>📸 Last 5 posts:</b>\n"
        for uid, pid, cr, ur, k, ca in posts:
            text += f"• {hide_id(pid)} — {cr} / {ur} — {k} kills — {ca}\n"

    await update.message.reply_text(text, parse_mode='HTML')

async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return
    users = get_all_users(limit=100)
    if not users:
        await update.message.reply_text("No users yet.")
        return
    text = f"👥 <b>USERS LIST ({len(users)})</b>\n\n"
    for i, (uid, un, fn, ja) in enumerate(users, 1):
        name = f"@{un}" if un else (fn if fn else "User")
        text += f"{i}. {name} — {ja}\n    ID: <code>{uid}</code>\n"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        await update.message.reply_text(chunk, parse_mode='HTML')

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return
    context.user_data['broadcast_mode'] = True
    await update.message.reply_text(
        "📢 <b>BROADCAST MODE</b>\n\n"
        "Send the message you want to broadcast.\n"
        "Use /cancel to abort.",
        parse_mode='HTML'
    )

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('broadcast_mode'): return
    if update.effective_user.id != ADMIN_ID: return
    broadcast_text = update.message.text
    if not broadcast_text: return
    context.user_data['broadcast_mode'] = False
    users = get_all_users(limit=1000)
    total = len(users); sent = 0; failed = 0
    progress = await update.message.reply_text(f"📤 Sending... 0/{total}")
    for idx, (uid, _, _, _) in enumerate(users, 1):
        try:
            await context.bot.send_message(chat_id=uid, text=broadcast_text)
            sent += 1
        except Exception:
            failed += 1
        if idx % 10 == 0 or idx == total:
            try: await progress.edit_text(f"📤 Sending... {idx}/{total}")
            except Exception: pass
    await progress.edit_text(
        f"✅ <b>Broadcast complete!</b>\n\n✔️ Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
        parse_mode='HTML'
    )

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: <code>/ban USER_ID</code>", parse_mode='HTML')
        return
    try: uid = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
        return
    if uid == ADMIN_ID:
        await update.message.reply_text("❌ You cannot ban yourself!")
        return
    ban_user(uid)
    await update.message.reply_text(f"✅ User <code>{uid}</code> banned.", parse_mode='HTML')

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: <code>/unban USER_ID</code>", parse_mode='HTML')
        return
    try: uid = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
        return
    unban_user(uid)
    await update.message.reply_text(f"✅ User <code>{uid}</code> unbanned.", parse_mode='HTML')

async def banned_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return
    banned = get_banned_users()
    if not banned:
        await update.message.reply_text("✅ No banned users.")
        return
    text = f"🚫 <b>BANNED USERS ({len(banned)})</b>\n\n"
    for uid, when in banned:
        text += f"• <code>{uid}</code> — {when}\n"
    await update.message.reply_text(text, parse_mode='HTML')

# ============================================================
# ✅ GROUP ADMIN-ONLY COMMANDS
# ============================================================
async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check admin
    if not await check_group_admin(update, context):
        return

    chat = update.effective_chat
    user = update.effective_user

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "🔇 <b>MUTE COMMAND</b>\n\n"
            "Reply to a user's message with:\n"
            "<code>/mute 5m</code> — 5 minutes\n"
            "<code>/mute 2h</code> — 2 hours\n"
            "<code>/mute 1d</code> — 1 day\n"
            "<code>/mute 1w</code> — 1 week\n"
            "<code>/mute</code> — default 1 hour\n\n"
            "Units: s=sec, m=min, h=hour, d=day, w=week",
            parse_mode='HTML'
        )
        return

    target = update.message.reply_to_message.from_user

    if target.id == user.id:
        await update.message.reply_text("❌ You cannot mute yourself.")
        return
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I cannot mute myself.")
        return

    try:
        target_member = await chat.get_member(target.id)
        if target_member.status in ('administrator', 'creator'):
            await update.message.reply_text("❌ Cannot mute admins.")
            return
    except Exception:
        pass

    if context.args:
        duration = parse_duration(context.args[0])
        if not duration:
            await update.message.reply_text(
                "❌ Invalid duration.\nExamples: 30s, 5m, 2h, 1d, 1w",
                parse_mode='HTML'
            )
            return
    else:
        duration = timedelta(hours=1)

    if duration > timedelta(days=366):
        duration = timedelta(days=366)

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now(timezone.utc) + duration
        )
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(
            f"🔇 <b>{name}</b> muted for <b>{human_duration(duration)}</b>.\n\n"
            f"👮 By: {user.mention_html()}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: <code>{e}</code>\n\n"
            "Make sure I have <b>Restrict Members</b> permission.",
            parse_mode='HTML'
        )

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context):
        return

    chat = update.effective_chat
    user = update.effective_user

    if not update.message.reply_to_message:
        await update.message.reply_text("🔊 Reply to a user's message with <code>/unmute</code>", parse_mode='HTML')
        return

    target = update.message.reply_to_message.from_user

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_invite_users=True
            )
        )
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(
            f"🔊 <b>{name}</b> unmuted.\n\n👮 By: {user.mention_html()}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: <code>{e}</code>", parse_mode='HTML')

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context):
        return

    chat = update.effective_chat
    end_id = update.message.message_id
    if update.message.reply_to_message:
        start_id = update.message.reply_to_message.message_id
    else:
        start_id = max(1, end_id - 50)

    status = await update.message.reply_text(f"🗑️ Clearing messages...")
    deleted = 0; failed = 0
    for msg_id in range(start_id, end_id + 1):
        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=msg_id)
            deleted += 1
        except Exception:
            failed += 1

    try: await status.delete()
    except Exception: pass

    report = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            f"✅ <b>Clear complete!</b>\n\n"
            f"✔️ Deleted: <b>{deleted}</b>\n"
            f"❌ Failed: <b>{failed}</b>\n\n"
            f"<i>Note: Only messages less than 48 hours old can be deleted.</i>"
        ),
        parse_mode='HTML'
    )
    await asyncio.sleep(5)
    try: await report.delete()
    except Exception: pass

# ============================================================
# ✅ COMMAND MENU SETUP — admin-only in groups
# ============================================================
async def post_init(application):
    """Bot ishga tushgach, buyruqlar menyusini o'rnatish"""
    try:
        # 1) Private chat — hamma uchun
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Start the bot"),
                BotCommand("cancel", "Cancel operation"),
                BotCommand("admin", "Bot statistics (admin)"),
                BotCommand("stats", "Bot statistics (admin)"),
                BotCommand("users", "Users list (admin)"),
                BotCommand("broadcast", "Broadcast (admin)"),
                BotCommand("ban", "Ban user (admin)"),
                BotCommand("unban", "Unban user (admin)"),
                BotCommand("banned", "Banned list (admin)"),
            ],
            scope=BotCommandScopeAllPrivateChats()
        )

        # 2) Groups — faqat adminlar uchun
        # Eslatma: setMyCommands turli chat_id uchun alohida chaqirilishi kerak,
        # lekin biz BotCommandScopeChatAdministrators ni ishlata olmaymiz har bir chat uchun.
        # Shuning uchun default group commands ni o'rnatmaymiz yoki faqat /start qo'yamiz.

        # Guruhda hamma uchun faqat /start ko'rinadi
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Start the bot"),
            ],
            scope=BotCommandScopeDefault()
        )

        logger.info("✅ Command menus set")
    except Exception as e:
        logger.error(f"❌ setMyCommands error: {e}")

# ============================================================
# START BOT
# ============================================================
def start_bot():
    logger.info("🤖 Bot starting...")
    try:
        req = HTTPXRequest(connection_pool_size=8, connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
        application = Application.builder()\
            .token(BOT_TOKEN)\
            .request(req)\
            .post_init(post_init)\
            .build()

        conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(rank_start, pattern="^rank_start$")],
            states={
                PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_player_id)],
                CLASSIC: [CallbackQueryHandler(handle_classic, pattern="^classic_")],
                ULTIMATE: [CallbackQueryHandler(handle_ultimate, pattern="^ultimate_")],
                KILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_kills)],
                PHOTO: [MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            per_message=False,
        )

        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv)
        application.add_handler(CallbackQueryHandler(confirm_send, pattern="^confirm_send$"))
        application.add_handler(CallbackQueryHandler(cancel_post, pattern="^cancel_post$"))
        application.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))

        # Owner-only commands
        application.add_handler(CommandHandler("admin", admin_stats))
        application.add_handler(CommandHandler("stats", admin_stats))
        application.add_handler(CommandHandler("users", users_list))
        application.add_handler(CommandHandler("broadcast", broadcast_cmd))
        application.add_handler(CommandHandler("ban", ban_cmd))
        application.add_handler(CommandHandler("unban", unban_cmd))
        application.add_handler(CommandHandler("banned", banned_list_cmd))

        # Group admin-only commands (check inside each handler)
        application.add_handler(CommandHandler("mute", mute_cmd))
        application.add_handler(CommandHandler("unmute", unmute_cmd))
        application.add_handler(CommandHandler("clear", clear_cmd))

        # Broadcast handler
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.ChatType.PRIVATE,
            handle_broadcast_message
        ))

        logger.info("✅ Bot started")
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
