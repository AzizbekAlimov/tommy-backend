"""
TOMMY BOT — IDEAL STRONG VERSION
================================
- So'kinish (UZ/RU/EN) + anti-evasion (f*ck, f.u.c.k, kirill lookalike, fuuuck)
- Yomon emojilar (kengaytirilgan)
- AI media: photo, sticker (webp/webm/tgs), GIF, video note, video
- Username/ism tekshirish (cooldown bilan)
- Warn + mute + blacklist
- PostgreSQL VIP keys
- Concurrent updates + cache + confidence threshold
"""
import os, sqlite3, asyncio, logging, threading, base64, json, re, gzip, tempfile
import html as html_lib
import psycopg2
from io import BytesIO
from datetime import datetime, timezone, timedelta

from PIL import Image
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, BotCommand,
    BotCommandScopeChatAdministrators,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
    ChatMemberHandler
)
from telegram.request import HTTPXRequest

import httpx

# ============================================================
# SETTINGS
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@TommyXcheat2")
OWNER_FIXED = "@Tommy_1727"
ADMIN_ID = int(os.getenv("ADMIN_ID", "7383782449"))
PORT = int(os.getenv("PORT", "10000"))
DATABASE_URL = os.getenv("DATABASE_URL")

AI_MEDIA_CHECK = os.getenv("AI_MEDIA_CHECK", "true").lower() in ("1", "true", "yes", "on")

TZ_TASHKENT = timezone(timedelta(hours=5))

MAX_WARNINGS = 3
WARN_MUTE_DURATION = timedelta(hours=1)
NAME_WARN_COOLDOWN = timedelta(hours=2)
AI_CONFIDENCE_THRESHOLD = 0.55

# ============================================================
# BAD WORDS — KENGAYTIRILGAN
# ============================================================
BAD_WORDS = [
    # 🇺🇿 O'ZBEKCHA
    "jalab", "jalap", "jallob", "jalloblar", "qotoq", "qotoqlar",
    "am", "sika", "siki", "sikaman", "sikasan", "sikadi", "sikish",
    "siktir", "sikiltir", "sikingni", "siking", "sikking",
    "haromi", "haromzoda", "haromilar", "haromzodalar",
    "qanjiq", "qanjiqlar", "itvachcha", "itvachchalar",
    "onangni", "otangni", "onang", "otang",
    "onabachcha", "onabachchal", "jalablar",
    # 🇷🇺 РУССКИЙ МАТ
    "blyad", "blyadina", "blyadskiy", "blyadstvo",
    "huy", "huynya", "huyni", "huyak", "huyok", "huyli",
    "pizdec", "pizda", "pizdets", "pizdato", "pizdatyy",
    "suka", "suchka", "sukin", "nahuy", "nahui", "nahuya",
    "mudak", "mudila", "mudozvon", "mudaki", "mudach", "mudachok",
    "govno", "govnyuk", "govnyak",
    "ebat", "yebat", "yobanyy", "yebal", "yebanashka",
    "ebuchiy", "ebaniy", "ebuchka", "zaebal", "zaebis", "zaeb",
    "dolboyob", "pidar", "pidoras", "pidaraz", "pidor",
    "pidarchik", "pidrila", "pidrilo", "zalupa",
    "zhopa", "zhopu", "gandon", "gandoni",
    # 🇬🇧 ENGLISH (long forms)
    "fuck", "fucking", "fucker", "fucked", "fuckers", "fuckface",
    "fuckhead", "fucktard", "motherfucker", "motherfucking", "clusterfuck",
    "shit", "shitty", "bullshit", "shitshow", "shithead",
    "bitch", "bitches", "bitchy",
    "asshole", "assholes", "bastard", "bastards",
    "dick", "dickhead", "dickheads", "dickface",
    "pussy", "pussies", "cunt", "cunts",
    "slut", "sluts", "slutty", "whore", "whores",
    "cocksucker", "cocksuckers", "dumbass", "dumbasses",
    "faggot", "fagot", "retard", "retarded",
    "nigger", "nigga", "nigg",
    # 🇬🇧 SHORT / LEET / EVASION
    "fck", "fuk", "fkk", "fuq", "phuck",
    "fukin", "fuking", "fckin", "fcking",
    "shyt", "sh1t", "sht", "sh1t",
    "btch", "b1tch", "bich", "bish",
    "d1ck", "dik", "dicc", "dikk",
    "cnt", "kunt", "cun7",
    "slu7", "wh0re", "hoe",
    "n1ga", "n1gga",
]

BAD_WORDS_SET = frozenset(BAD_WORDS)

# ============================================================
# BAD EMOJIS
# ============================================================
BAD_EMOJIS = [
    "🖕", "🖕🏻", "🖕🏼", "🖕🏽", "🖕🏾", "🖕🏿",
    "🤬", "🤮", "🤢", "🤡",
    "💩", "🔞", "🍑", "🍆", "💦", "👅",
    "卐", "卍",
]

# ============================================================
# ANTI-EVASION NORMALIZATION
# ============================================================
ZERO_WIDTH_CHARS = '\u200b\u200c\u200d\u2060\ufeff\u180e'

LEET_MAP = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
    '6': 'g', '7': 't', '8': 'b', '9': 'g',
    '@': 'a', '$': 's', '!': 'i', '|': 'i', '€': 'e', '£': 'e',
}

CYR_LAT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
    'ё': 'e', 'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k',
    'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
    'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'x', 'ц': 'c',
    'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '', 'ы': 'i', 'ь': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya',
}

def _transform_base(text):
    """Cyr→Lat + leet konversiya (so'z chegaralari saqlanadi)."""
    t = text.lower()
    t = ''.join(c for c in t if c not in ZERO_WIDTH_CHARS)
    t = ''.join(CYR_LAT_MAP.get(c, c) for c in t)
    t = ''.join(LEET_MAP.get(c, c) for c in t)
    return t

def _normalize_words(text):
    """So'zlar ro'yxati (collapse 2+)."""
    t = _transform_base(text)
    t = re.sub(r'(.)\1+', r'\1', t)
    return re.findall(r'[a-z]+', t)

def _joined(text):
    """Barcha harflar biriktirilgan holda (f.u.c.k → fuck)."""
    t = _transform_base(text)
    t = re.sub(r'[^a-z]', '', t)
    t = re.sub(r'(.)\1+', r'\1', t)
    return t

def contains_bad_word(text):
    """3 bosqichli tekshiruv: raw → normalized → joined."""
    if not text:
        return None

    # 1) Raw so'zlar (to'g'ridan-to'g'ri)
    raw_words = re.findall(r"[a-zA-Zа-яА-ЯёЁ\u0400-\u04FF]+", text.lower())
    for w in raw_words:
        if w in BAD_WORDS_SET:
            return w

    # 2) Normalize qilingan so'zlar
    for w in _normalize_words(text):
        if w in BAD_WORDS_SET:
            return w

    # 3) Biriktirilgan matn (separator olib tashlangan)
    joined = _joined(text)
    if joined:
        for bad in BAD_WORDS_SET:
            if len(bad) < 4:
                continue
            if bad in joined and (len(joined) - len(bad)) <= 3:
                return bad

    return None

def contains_bad_emoji(text):
    if not text:
        return None
    for emoji in BAD_EMOJIS:
        if emoji in text:
            return emoji
    return None

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN yo'q!")
    raise SystemExit(1)

if GEMINI_API_KEY:
    logger.info("✅ Gemini API key loaded")
else:
    logger.warning("⚠️ GEMINI_API_KEY yo'q — AI media check ishlamaydi!")

# ============================================================
# OPTIONAL: rlottie
# ============================================================
try:
    from rlottie_python import LottieAnimation
    RLOTTIE_AVAILABLE = True
    logger.info("✅ rlottie-python yuklandi — .tgs AI tekshiriladi")
except Exception as e:
    LottieAnimation = None
    RLOTTIE_AVAILABLE = False
    logger.warning(f"⚠️ rlottie-python yo'q — .tgs faqat qora ro'yxat ({e})")

# ============================================================
# CONVERSATION STATES
# ============================================================
PHOTO, PLAYER_ID, CLASSIC, ULTIMATE, KILLS = range(5)

# ============================================================
# COMMANDS
# ============================================================
PRIVATE_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("cancel", "Cancel operation"),
    BotCommand("admin", "Bot statistics"),
    BotCommand("users", "Users list"),
    BotCommand("broadcast", "Broadcast message"),
    BotCommand("ban", "Ban user"),
    BotCommand("unban", "Unban user"),
    BotCommand("banned", "Banned users list"),
]
GROUP_ADMIN_COMMANDS = [
    BotCommand("start", "Start the bot"), BotCommand("setup", "Setup command menu"),
    BotCommand("mute", "Mute user (reply)"), BotCommand("unmute", "Unmute user (reply)"),
    BotCommand("mutesticker", "Mute stickers/GIFs"), BotCommand("warn", "Warn user (reply)"),
    BotCommand("unwarn", "Clear user warnings"), BotCommand("warns", "Show user warnings"),
    BotCommand("addbadsticker", "Mark sticker/GIF as bad"), BotCommand("delbadsticker", "Unmark sticker/GIF"),
    BotCommand("listbadstickers", "List bad stickers"), BotCommand("clear", "Clear recent messages"),
]
GROUP_PUBLIC_COMMANDS = [BotCommand("start", "Start the bot")]

# ============================================================
# WEBAPP HTML (o'zgarmagan)
# ============================================================
INDEX_HTML = r'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>TOMMY BOT</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh;padding:16px;background:#0a0820;overflow-x:hidden}
.container{max-width:500px;margin:0 auto}
.header{text-align:center;padding:40px 0 25px}
.header .logo{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#4CAF50,#2196F3);display:flex;align-items:center;justify-content:center;margin:0 auto 15px;font-size:40px;box-shadow:0 8px 30px rgba(76,175,80,.5);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
.header h1{color:#4CAF50;font-size:24px;font-weight:800}
.header p{color:#888;font-size:12px}
.card{background:rgba(255,255,255,.06);border-radius:16px;padding:16px;margin-bottom:12px;border:1px solid rgba(255,255,255,.08)}
.card-title{color:#4CAF50;font-size:14px;font-weight:700;margin-bottom:12px;text-transform:uppercase}
.info-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05)}
.info-row:last-child{border-bottom:none}
.info-label{color:#999;font-size:12px}
.info-value{color:#fff;font-weight:600;font-size:13px;text-align:right;max-width:60%}
.info-value.green{color:#4CAF50}
.rank-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
.rank-item{background:rgba(76,175,80,.15);border:1px solid rgba(76,175,80,.3);border-radius:10px;padding:12px;text-align:center;font-size:12px;font-weight:600;color:#4CAF50;cursor:pointer}
.rank-item.selected{background:#4CAF50;color:#fff}
.rank-item.gold{background:rgba(255,193,7,.15);border-color:rgba(255,193,7,.3);color:#FFC107}
.rank-item.gold.selected{background:#FFC107;color:#000}
.rank-item.blue{background:rgba(33,150,243,.15);border-color:rgba(33,150,243,.3);color:#2196F3}
.rank-item.blue.selected{background:#2196F3;color:#fff}
.rank-item.purple{background:rgba(156,39,176,.15);border-color:rgba(156,39,176,.3);color:#CE93D8}
.rank-item.purple.selected{background:#9C27B0;color:#fff}
.input-group input{width:100%;padding:14px;background:rgba(255,255,255,.08);border:1.5px solid rgba(255,255,255,.15);border-radius:12px;color:#fff;font-size:15px;outline:none}
.input-group input:focus{border-color:#4CAF50}
.btn{width:100%;padding:15px;border:none;border-radius:14px;font-size:15px;font-weight:700;cursor:pointer;margin-top:12px;font-family:inherit}
.btn-primary{background:linear-gradient(135deg,#4CAF50,#45a049);color:#fff}
.btn-secondary{background:linear-gradient(135deg,#2196F3,#1976D2);color:#fff}
.btn-warning{background:linear-gradient(135deg,#FF9800,#F57C00);color:#fff}
.btn-outline{background:transparent;border:1.5px solid rgba(255,255,255,.2);color:#ccc}
.photo-upload-box{padding:25px;background:rgba(255,255,255,.06);border:2px dashed rgba(76,175,80,.5);border-radius:14px;text-align:center;cursor:pointer;margin-bottom:12px}
.photo-upload-box .icon{font-size:36px;display:block;margin-bottom:8px}
.photo-upload-box .text{color:#4CAF50;font-size:13px;font-weight:600}
.photo-upload-box .subtext{color:#888;font-size:11px;margin-top:6px}
#photo-input{display:none}
.photo-preview{display:none;width:100%;max-height:200px;object-fit:cover;border-radius:14px;margin-bottom:12px;border:2px solid #4CAF50}
.photo-preview.show{display:block}
.footer{text-align:center;padding:20px 0;color:#555;font-size:11px}
</style></head>
<body><div class="container">
<div class="header"><div class="logo">🎮</div><h1>TOMMY BOT</h1><p>PUBG Mobile Statistics Panel</p></div>
<div class="card"><div class="card-title">👤 Your Information</div>
<div class="info-row"><span class="info-label">Name:</span><span class="info-value" id="user-name">Loading...</span></div>
<div class="info-row"><span class="info-label">Username:</span><span class="info-value green" id="user-username">-</span></div>
<div class="info-row"><span class="info-label">Telegram ID:</span><span class="info-value" id="user-id">-</span></div>
</div>
<div class="card"><div class="card-title">🆔 PUBG Mobile ID</div>
<div class="input-group"><input type="tel" id="player-id" placeholder="Enter 11-digit ID" maxlength="11" inputmode="numeric"></div></div>
<div class="card"><div class="card-title">📸 Screenshot</div>
<div class="photo-upload-box" id="photo-box"><span class="icon">📤</span><div class="text">Tap to upload screenshot</div><div class="subtext">JPG, PNG • Max 5MB</div></div>
<input type="file" id="photo-input" accept="image/*">
<img id="photo-preview" class="photo-preview"></div>
<div class="card"><div class="card-title">👑 CLASSIC RANKS</div>
<div class="rank-grid" id="classic-ranks">
<div class="rank-item" data-rank="Bronze">Bronze</div><div class="rank-item" data-rank="Silver">Silver</div>
<div class="rank-item" data-rank="Gold">Gold</div><div class="rank-item" data-rank="Platinum">Platinum</div>
<div class="rank-item blue" data-rank="Diamond">Diamond</div><div class="rank-item blue" data-rank="Crown">Crown</div>
<div class="rank-item gold" data-rank="Ace">Ace</div><div class="rank-item gold" data-rank="Ace Master">Ace Master</div>
<div class="rank-item purple" data-rank="Ace Dominator">Ace Dominator</div><div class="rank-item purple" data-rank="Conqueror">Conqueror</div>
</div></div>
<div class="card"><div class="card-title">👑 ULTIMATE ROYALE</div>
<div class="rank-grid" id="ultimate-ranks">
<div class="rank-item" data-rank="Vanguard">Vanguard</div><div class="rank-item" data-rank="Exceed">Exceed</div>
<div class="rank-item blue" data-rank="Supreme">Supreme</div><div class="rank-item blue" data-rank="Peerless">Peerless</div>
<div class="rank-item purple" data-rank="Legend">Legend</div>
</div></div>
<div class="card"><div class="card-title">💀 Kills in 1 Match</div>
<div class="input-group"><input type="tel" id="kills" placeholder="Enter kills (1-100)" maxlength="3" inputmode="numeric"></div></div>
<div class="card"><div class="card-title">👤 FOR INQUIRIES</div>
<div class="info-row"><span class="info-label">Bot:</span><span class="info-value">TOMMY BOT</span></div>
<div class="info-row"><span class="info-label">Channel:</span><span class="info-value green">@TommyXcheat2</span></div>
<div class="info-row"><span class="info-label">Owner:</span><span class="info-value" style="color:#FFC107">@Tommy_1727</span></div>
<div class="info-row"><span class="info-label">Version:</span><span class="info-value">v4.0</span></div>
</div>
<button class="btn btn-primary" onclick="openChannel()">📊 STATISTICS</button>
<button class="btn btn-secondary" onclick="startNew()">📤 START NEW</button>
<button class="btn btn-warning" onclick="openChannel()">📢 Go to Channel</button>
<button class="btn btn-outline" onclick="closeApp()">❌ Close</button>
<div class="footer">© 2026 @Tommy_1727</div>
</div>
<script>
const tg=window.Telegram.WebApp;tg.expand();tg.ready();tg.setHeaderColor('#0a0820');tg.setBackgroundColor('#0a0820');
const API_URL="https://tommy-backend.onrender.com/send-feedback";
const user=tg.initDataUnsafe.user;
if(user){const fn=((user.first_name||'')+' '+(user.last_name||'')).trim();document.getElementById('user-name').innerText=fn||('User #'+user.id);document.getElementById('user-username').innerText=user.username?'@'+user.username:'—';document.getElementById('user-id').innerText=user.id;}
let selClassic=null,selUltimate=null,photoValid=false;
document.querySelectorAll('#classic-ranks .rank-item').forEach(i=>i.onclick=()=>{document.querySelectorAll('#classic-ranks .rank-item').forEach(x=>x.classList.remove('selected'));i.classList.add('selected');selClassic=i.dataset.rank});
document.querySelectorAll('#ultimate-ranks .rank-item').forEach(i=>i.onclick=()=>{document.querySelectorAll('#ultimate-ranks .rank-item').forEach(x=>x.classList.remove('selected'));i.classList.add('selected');selUltimate=i.dataset.rank});
const pi=document.getElementById('photo-input'),pp=document.getElementById('photo-preview'),pb=document.getElementById('photo-box');
pb.onclick=()=>pi.click();
pi.onchange=e=>{const f=e.target.files[0];if(!f)return;if(f.size>5*1024*1024){tg.showAlert('File too large');return}
const r=new FileReader();r.onload=ev=>{pp.src=ev.target.result;pp.classList.add('show');pb.style.display='none';photoValid=true};r.readAsDataURL(f)};
function vid(id){if(!/^\d{11}$/.test(id))return false;if(id[0]!=='5'&&id[0]!=='6')return false;if(/^(\d)\1{10}$/.test(id))return false;return true}
async function startNew(){
const pid=document.getElementById('player-id').value.trim();
const k=document.getElementById('kills').value.trim();
if(!vid(pid)){tg.showAlert('Invalid ID! Must be 11 digits starting with 5 or 6');return}
if(!selClassic){tg.showAlert('Select Classic Rank');return}
if(!selUltimate){tg.showAlert('Select Ultimate Rank');return}
const kn=parseInt(k);if(isNaN(kn)||kn<1||kn>100){tg.showAlert('Kills must be 1-100');return}
const f=pi.files[0];if(!f||!photoValid){tg.showAlert('Upload screenshot');return}
tg.showPopup({title:'Sending...',message:'Please wait'});
const hid=pid.substring(0,3)+'***'+pid.substring(9);
const now=new Date(),ts=String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0')+'  '+String(now.getDate()).padStart(2,'0')+'.'+String(now.getMonth()+1).padStart(2,'0')+'.'+now.getFullYear();
const owner=user?(user.username?'@'+user.username:user.first_name+' (ID: '+user.id+')'):'Unknown';
const cap='👤 OWNER: '+owner+'\n🎮 Player ID: '+hid+'\n🏆 CLASSIC RANK: '+selClassic+'\n🏆 ULTIMATE ROYALE RANK: '+selUltimate+'\n🕒 TIME: '+ts+'\n💀 KILL: '+k+'\n\n👤 OWNER: @Tommy_1727 ✅';
const fd=new FormData();fd.append('photo',f);fd.append('caption',cap);
try{const res=await fetch(API_URL,{method:'POST',body:fd});const data=await res.json();
if(data.ok){tg.showAlert('✅ Sent to channel!');setTimeout(()=>tg.close(),1500)}else{tg.showAlert('❌ Error: '+(data.description||'Unknown'))}}
catch(e){tg.showAlert('❌ Network error')}}
function openChannel(){tg.openTelegramLink('https://t.me/TommyXcheat2')}
function closeApp(){tg.close()}
tg.BackButton.show();tg.BackButton.onClick(()=>tg.close());
</script></body></html>'''

# ============================================================
# SQLITE
# ============================================================
def init_db():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, player_id TEXT, classic_rank TEXT, ultimate_rank TEXT, kills TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS warnings
                 (chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0,
                  PRIMARY KEY (chat_id, user_id))""")
    c.execute("CREATE TABLE IF NOT EXISTS bad_stickers (file_id TEXT PRIMARY KEY, added_at TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS media_verdicts
                 (file_unique_id TEXT PRIMARY KEY, is_bad INTEGER,
                  reason TEXT, checked_at TEXT)""")
    conn.commit(); conn.close()

# ============================================================
# POSTGRESQL
# ============================================================
def init_pg_db():
    if not DATABASE_URL:
        logger.warning("⚠️ DATABASE_URL topilmadi! Key tizimi ishlamaydi.")
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vip_keys (
                id SERIAL PRIMARY KEY,
                key_code VARCHAR(100) UNIQUE NOT NULL,
                key_type VARCHAR(20) NOT NULL,
                expire_date TIMESTAMP NOT NULL
            );
        """)
        conn.commit(); cur.close(); conn.close()
        logger.info("✅ PostgreSQL (vip_keys) jadvali tekshirildi!")
    except Exception as e:
        logger.error(f"❌ PostgreSQL ulanish xatosi: {e}")

# ============================================================
# USER DB HELPERS
# ============================================================
def save_user(uid, un, fn):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)",
              (uid, un or "", fn or "", datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
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

def ban_user(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO banned_users VALUES (?,?)",
              (uid, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def unban_user(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("DELETE FROM banned_users WHERE user_id=?", (uid,)); conn.commit(); conn.close()

def is_banned(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT 1 FROM banned_users WHERE user_id=?", (uid,))
    r = c.fetchone(); conn.close(); return r is not None

def get_banned_users():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT user_id, banned_at FROM banned_users ORDER BY banned_at DESC")
    r = c.fetchall(); conn.close(); return r

# ============================================================
# WARN + BAD STICKERS
# ============================================================
def get_warn_count(chat_id, user_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    r = c.fetchone(); conn.close()
    return r[0] if r else 0

def set_warn_count(chat_id, user_id, count):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO warnings VALUES (?,?,?)", (chat_id, user_id, count))
    conn.commit(); conn.close()

def clear_warn(chat_id, user_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit(); conn.close()

def get_bad_stickers():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT file_id FROM bad_stickers")
    r = [x[0] for x in c.fetchall()]; conn.close(); return r

def add_bad_sticker(file_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO bad_stickers VALUES (?,?)",
              (file_id, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def remove_bad_sticker(file_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("DELETE FROM bad_stickers WHERE file_id=?", (file_id,))
    conn.commit(); conn.close()

# ============================================================
# MEDIA CACHE
# ============================================================
def get_media_verdict(fuid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT is_bad, reason FROM media_verdicts WHERE file_unique_id=?", (fuid,))
    r = c.fetchone(); conn.close()
    return (bool(r[0]), r[1]) if r else None

def set_media_verdict(fuid, is_bad, reason):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO media_verdicts VALUES (?,?,?,?)",
              (fuid, 1 if is_bad else 0, reason or "",
               datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def delete_media_verdict(fuid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("DELETE FROM media_verdicts WHERE file_unique_id=?", (fuid,))
    conn.commit(); conn.close()

def get_bad_media_count():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM media_verdicts WHERE is_bad=1")
    n = c.fetchone()[0]; conn.close(); return n

# ============================================================
# TGS → PNG FRAMES
# ============================================================
def tgs_to_png_frames(tgs_bytes, num_frames=3, size=512):
    if not RLOTTIE_AVAILABLE or not tgs_bytes:
        return []
    tmp_path = None
    anim = None
    try:
        json_data = gzip.decompress(tgs_bytes)
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='wb') as f:
            f.write(json_data)
            tmp_path = f.name
        anim = LottieAnimation.from_file(tmp_path)
        total = anim.lottie_animation_get_totalframes()
        if not total or total <= 0:
            return []
        frames = []
        for i in range(num_frames):
            idx = int(total * (i + 0.5) / num_frames)
            if idx >= total:
                idx = total - 1
            try:
                pil_img = anim.lottie_animation_render(idx, size, size)
            except Exception as fe:
                logger.warning(f"Frame {idx} render error: {fe}")
                continue
            if pil_img is None:
                continue
            buf = BytesIO()
            try:
                if hasattr(pil_img, 'save'):
                    pil_img.save(buf, format='PNG')
                else:
                    Image.fromarray(pil_img).save(buf, format='PNG')
                frames.append(buf.getvalue())
            except Exception as se:
                logger.warning(f"PNG save error: {se}")
        return frames
    except Exception as e:
        logger.error(f"TGS render error: {e}")
        return []
    finally:
        if anim is not None:
            try: anim.lottie_animation_destroy()
            except: pass
        if tmp_path:
            try: os.unlink(tmp_path)
            except: pass

# ============================================================
# AI MEDIA ANALYSIS (strict + confidence)
# ============================================================
async def analyze_media_content_with_ai(media_frames, mime_types=None):
    if not GEMINI_API_KEY or not AI_MEDIA_CHECK:
        return None, None
    try:
        if not isinstance(media_frames, list):
            media_frames = [media_frames]
        if mime_types is None:
            mime_types = ['image/jpeg'] * len(media_frames)
        elif not isinstance(mime_types, list):
            mime_types = [mime_types] * len(media_frames)
        if len(media_frames) != len(mime_types) or not media_frames:
            return None, None

        prompt = (
            "You are an EXTREMELY STRICT content moderator for a Telegram group.\n"
            "Analyze the provided media and decide if it contains BAD content.\n\n"

            "FLAG AS BAD (bad=true) if ANY of these appear:\n"
            "• Nudity, partial nudity, exposed genitals/breasts/buttocks\n"
            "• Sexual content, pornography, suggestive poses, sexual acts\n"
            "• Extreme violence, gore, open wounds, blood, corpses, dead bodies\n"
            "• Weapons pointed at people (guns, knives, swords)\n"
            "• Drugs, drug use, syringes, cocaine, marijuana as main subject\n"
            "• Middle finger 🖕 gesture shown by a hand\n"
            "• Offensive hand gestures (not thumbs up/down)\n"
            "• Swastika, Nazi symbols, ISIS/terrorist flags, hate symbols\n"
            "• Feces, poop, urine, vomit as main subject\n"
            "• Self-harm, cutting, graphic injury\n"
            "• Visible profanity or obscene words in any language\n"
            "• Child in ANY sexual or exploitative context (always bad)\n"
            "• Bestiality\n\n"

            "DO NOT FLAG (bad=false):\n"
            "• Normal selfies, portraits, family photos\n"
            "• Normal memes, jokes (without explicit content)\n"
            "• Food, animals, nature, sports\n"
            "• Cartoons/anime (unless sexual/lewd)\n"
            "• Weapons in safe context (museum, toy, game)\n"
            "• Minor blood in medical/sports context\n"
            "• Text messages, chat screenshots\n"
            "• Innocent stickers, emojis, funny animations\n"
            "• ANYTHING ambiguous — mark safe\n\n"

            "If multiple frames provided, treat as ONE animation. "
            "If ANY frame is bad, whole is bad.\n\n"

            "Return ONLY valid JSON (no markdown, no extra text):\n"
            '{"bad": true|false, "confidence": 0.0-1.0, '
            '"reason": "max 60 chars in English or null"}'
        )

        parts = [{"text": prompt}]
        for fb, mt in zip(media_frames, mime_types):
            b64 = base64.b64encode(fb).decode("utf-8")
            parts.append({"inline_data": {"mime_type": mt, "data": b64}})

        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}")
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(url, json=payload)
            result = r.json()
        if "candidates" not in result or not result["candidates"]:
            logger.warning(f"AI media: no candidates. Resp: {str(result)[:200]}")
            return None, None
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        s, e = text.find("{"), text.rfind("}")
        if s == -1 or e == -1:
            return None, None
        data = json.loads(text[s:e + 1])
        bad = bool(data.get("bad"))
        try:
            conf = float(data.get("confidence", 0.9))
        except (ValueError, TypeError):
            conf = 0.9
        reason = data.get("reason")
        if bad and conf < AI_CONFIDENCE_THRESHOLD:
            logger.info(f"AI flag rejected (low conf {conf}): {reason}")
            return False, None
        return bad, reason
    except Exception as e:
        logger.error(f"Media AI error: {e}")
        return None, None

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
    if p[0] not in ("5", "6"): return False
    if len(set(p)) == 1: return False
    return True

def validate_pubg_screenshot(image_bytes):
    try:
        img = Image.open(BytesIO(image_bytes)); img.load()
    except Exception:
        return False, "Could not read image."
    if img.format and img.format.upper() not in ("JPEG", "PNG", "WEBP", "JPG"):
        return False, "Unsupported format."
    w, h = img.size
    if w < 640 or h < 360: return False, "Resolution too low."
    if w <= h: return False, "Landscape only."
    return True, ""

def parse_duration(s):
    s = str(s).strip().lower()
    if not s: return None
    try:
        num = int(s[:-1]); unit = s[-1]
    except (ValueError, IndexError):
        try: num = int(s); unit = 'm'
        except ValueError: return None
    if num <= 0: return None
    units = {'s': timedelta(seconds=num), 'm': timedelta(minutes=num),
             'h': timedelta(hours=num), 'd': timedelta(days=num), 'w': timedelta(weeks=num)}
    return units.get(unit)

def human_duration(td):
    t = int(td.total_seconds())
    if t < 60: return f"{t} seconds"
    if t < 3600: return f"{t // 60} minutes"
    if t < 86400: return f"{t // 3600} hours"
    if t < 604800: return f"{t // 86400} days"
    return f"{t // 604800} weeks"

# ============================================================
# GEMINI (PUBG screenshot)
# ============================================================
def analyze_with_ai(image_bytes, mime_type="image/jpeg"):
    if not GEMINI_API_KEY: return None
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = 'Return ONLY JSON: {"player_id":"11-digit or null","classic_rank":"... or null","ultimate_rank":"... or null","kills":"number or null"}'
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": b64}}]}],
                   "generationConfig": {"temperature": 0.1, "maxOutputTokens": 500}}
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload); result = r.json()
        if "candidates" not in result or not result["candidates"]: return None
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip().replace("```json", "").replace("```", "").strip()
        s, e = text.find("{"), text.rfind("}")
        if s == -1 or e == -1: return None
        return json.loads(text[s:e+1])
    except Exception as e:
        logger.error(f"AI error: {e}"); return None

def send_to_telegram(image_bytes, caption, mime_type='image/jpeg'):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {'photo': ('screenshot.jpg', image_bytes, mime_type)}
        data = {'chat_id': CHANNEL_ID, 'caption': caption}
        with httpx.Client(timeout=60.0) as client:
            r = client.post(url, files=files, data=data)
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

@flask_app.route('/ping', methods=['GET', 'HEAD'])
def ping():
    return "OK", 200

@flask_app.route('/send-feedback', methods=['POST'])
def send_feedback():
    try:
        if 'photo' not in request.files:
            return jsonify({'ok': False, 'description': 'Photo required!'}), 400
        photo = request.files['photo']
        if photo.filename == '':
            return jsonify({'ok': False, 'description': 'No file'}), 400
        pb = photo.read()
        if len(pb) > 5 * 1024 * 1024:
            return jsonify({'ok': False, 'description': 'Too large'}), 400
        fc = request.form.get('caption', '')
        ai = analyze_with_ai(pb, photo.mimetype or 'image/jpeg')
        if ai:
            pid = str(ai.get('player_id') or '')
            hidden = hide_id(pid) if pid else 'Unknown'
            owner_line = fc.split('\n')[0] or '👤 OWNER: Unknown'
            owner = owner_line.replace('👤 OWNER: ', '').strip()
            now = datetime.now(TZ_TASHKENT)
            final = (f"👤 OWNER: {owner}\n🎮 Player ID: {hidden}\n"
                     f"🏆 CLASSIC RANK: {ai.get('classic_rank') or 'Unknown'}\n"
                     f"🏆 ULTIMATE ROYALE RANK: {ai.get('ultimate_rank') or 'Unknown'}\n"
                     f"🕒 TIME: {now.strftime('%H:%M  %d.%m.%Y')}\n"
                     f"💀 KILL: {ai.get('kills') or '0'}\n\n👤 OWNER: {OWNER_FIXED} ✅")
        else:
            if not fc:
                return jsonify({'ok': False, 'description': 'Caption required!'}), 400
            final = fc
        res = send_to_telegram(pb, final, photo.mimetype or 'image/jpeg')
        return jsonify({'ok': res.get('ok', False), 'description': res.get('description'), 'ai_data': ai}), 200 if res.get('ok') else 500
    except Exception as e:
        logger.error(f"Web error: {e}")
        return jsonify({'ok': False, 'description': str(e)}), 500

@flask_app.route('/verify_key', methods=['POST'])
def verify_key():
    data = request.get_json()
    if not data or 'key' not in data:
        return jsonify({"status": False, "message": "KEY BO'SH"}), 400
    key = data['key']
    if not DATABASE_URL:
        return jsonify({"status": False, "message": "BAZA ULANMAGAN"}), 500
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT expire_date FROM vip_keys WHERE key_code = %s", (key,))
        result = cur.fetchone()
        cur.close(); conn.close()
        if not result:
            return jsonify({"status": False, "message": "BUNDAY KEY YO'Q"}), 404
        expire_date = result[0]
        now = datetime.now()
        if now > expire_date:
            return jsonify({"status": False, "message": "MUDDATI TUGAGAN"}), 403
        kalan_gun = (expire_date - now).days
        return jsonify({"status": True, "message": f"QOLGAN: {kalan_gun} kun"}), 200
    except Exception as e:
        logger.error(f"Verify key error: {e}")
        return jsonify({"status": False, "message": "SERVER XATOLIGI"}), 500

def run_flask():
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False, threaded=True)

# ============================================================
# BOT HANDLERS
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if update.effective_chat.type == 'private' and is_banned(u.id):
        await update.message.reply_text(f"🚫 Banned. Contact: {OWNER_FIXED}"); return
    save_user(u.id, u.username, u.first_name)
    context.user_data.clear()
    kb = [[InlineKeyboardButton("🏆 RANK STATISTICA", callback_data="rank_start")],
          [InlineKeyboardButton("📞 Contact", callback_data="contact")]]
    await update.message.reply_text("🤖 TOMMY BOT\n\nSend your PUBG Mobile statistics:", reply_markup=InlineKeyboardMarkup(kb))

async def rank_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); context.user_data.clear()
    await q.message.reply_text("🆔 Step 1\n\nSend your PUBG Mobile ID:\n\n• 11 digits\n• Starts with 5 or 6")
    return PLAYER_ID

async def handle_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.message.text.strip()
    if not is_valid_player_id(pid):
        await update.message.reply_text("❌ Invalid ID!\n\nTry again:"); return PLAYER_ID
    context.user_data['player_id'] = pid
    ranks = ["Bronze","Silver","Gold","Platinum","Diamond","Crown","Ace","Ace Master","Ace Dominator","Conqueror"]
    kb = [[InlineKeyboardButton(f"🏆 {r}", callback_data=f"classic_{r}")] for r in ranks]
    await update.message.reply_text(f"✅ ID: {pid}\n\n👑 Step 2\n\nSelect CLASSIC RANK:", reply_markup=InlineKeyboardMarkup(kb))
    return CLASSIC

async def handle_classic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    rank = q.data.replace("classic_", "")
    context.user_data['classic_rank'] = rank
    await q.message.delete()
    ranks = ["Vanguard","Exceed","Supreme","Peerless","Legend"]
    kb = [[InlineKeyboardButton(f"🏆 {r}", callback_data=f"ultimate_{r}")] for r in ranks]
    await q.message.reply_text(f"✅ Classic: {rank}\n\n👑 Step 3\n\nSelect ULTIMATE ROYALE:", reply_markup=InlineKeyboardMarkup(kb))
    return ULTIMATE

async def handle_ultimate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    rank = q.data.replace("ultimate_", "")
    context.user_data['ultimate_rank'] = rank
    await q.message.delete()
    await q.message.reply_text(f"✅ Ultimate: {rank}\n\n💀 Step 4\n\nEnter KILLS (1-100):")
    return KILLS

async def handle_kills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kills = update.message.text.strip()
    if not kills.isdigit() or not (1 <= int(kills) <= 100):
        await update.message.reply_text("❌ Enter 1-100:"); return KILLS
    context.user_data['kills'] = kills
    await update.message.reply_text(f"✅ Kills: {kills}\n\n📸 Step 5\n\nSend screenshot:")
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    msg = await update.message.reply_text("⏳ Verifying...")
    try:
        f = await context.bot.get_file(photo.file_id)
        fb = bytes(await f.download_as_bytearray())
        ok, reason = validate_pubg_screenshot(fb)
        if not ok:
            await msg.delete(); await update.message.reply_text(f"❌ {reason}\n\nTry again:"); return PHOTO
        u = update.effective_user
        now = datetime.now(TZ_TASHKENT)
        cap = (f"👤 OWNER: {'@'+u.username if u.username else u.full_name}\n"
               f"🎮 Player ID: {hide_id(context.user_data.get('player_id',''))}\n"
               f"🏆 CLASSIC RANK: {context.user_data.get('classic_rank','Unknown')}\n"
               f"🏆 ULTIMATE ROYALE RANK: {context.user_data.get('ultimate_rank','Unknown')}\n"
               f"🕒 TIME: {now.strftime('%H:%M  %d.%m.%Y')}\n"
               f"💀 KILL: {context.user_data.get('kills','0')}\n\n👤 OWNER: {OWNER_FIXED} ✅")
        kb = [[InlineKeyboardButton("✅ Send", callback_data="confirm_send")],
              [InlineKeyboardButton("❌ Cancel", callback_data="cancel_post")]]
        await msg.delete()
        context.user_data['photo_id'] = photo.file_id
        context.user_data['caption'] = cap
        await update.message.reply_photo(photo=photo.file_id, caption=f"🤖 Preview:\n\n{cap}", reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Photo: {e}"); await update.message.reply_text(f"❌ {e}"); return PHOTO

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    pid = context.user_data.get('photo_id')
    cap = context.user_data.get('caption', '')
    if not pid: await q.message.reply_text("❌ Photo lost"); return
    try:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=pid, caption=cap)
        u = update.effective_user
        save_post(u.id, context.user_data.get('player_id',''), context.user_data.get('classic_rank',''), context.user_data.get('ultimate_rank',''), context.user_data.get('kills',''))
        await q.message.delete(); await q.message.reply_text("✅ Sent!")
    except Exception as e:
        await q.message.reply_text(f"❌ Error: {e}")
    context.user_data.clear()

async def cancel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data.clear(); await q.message.delete()
    await q.message.reply_text("❌ Cancelled")

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.message.reply_text(f"Contact: {OWNER_FIXED}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear(); context.user_data['broadcast_mode'] = False
    await update.message.reply_text("Cancelled."); return ConversationHandler.END

# ADMIN
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not admin"); return
    ai_status = "✅ ON" if (AI_MEDIA_CHECK and GEMINI_API_KEY) else "❌ OFF"
    tgs_status = "✅ ON" if RLOTTIE_AVAILABLE else "❌ OFF"
    text = (f"📊 <b>STATS (v4.0)</b>\n\n"
            f"👥 Users: <b>{get_users_count()}</b>\n"
            f"🆕 Today: <b>{get_today_users_count()}</b>\n"
            f"📸 Posts: <b>{get_posts_count()}</b>\n"
            f"🚫 Banned: <b>{len(get_banned_users())}</b>\n"
            f"⚠️ Bad stickers (manual): <b>{len(get_bad_stickers())}</b>\n"
            f"🤖 AI media check: <b>{ai_status}</b>\n"
            f"🎞 Animatsion sticker (.tgs): <b>{tgs_status}</b>\n"
            f"🎯 Bad media (AI detected): <b>{get_bad_media_count()}</b>")
    await update.message.reply_text(text, parse_mode='HTML')

async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    users = get_all_users(100)
    if not users: await update.message.reply_text("No users"); return
    text = f"👥 <b>USERS ({len(users)})</b>\n\n"
    for i, (uid, un, fn, ja) in enumerate(users, 1):
        n = f"@{un}" if un else (fn or "User")
        text += f"{i}. {html_lib.escape(n)} — {ja}\n    <code>{uid}</code>\n"
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000], parse_mode='HTML')

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    context.user_data['broadcast_mode'] = True
    await update.message.reply_text("📢 Send message. /cancel to abort.")

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('broadcast_mode') or update.effective_user.id != ADMIN_ID: return
    t = update.message.text
    if not t: return
    context.user_data['broadcast_mode'] = False
    users = get_all_users(1000); total = len(users); sent = 0; failed = 0
    p = await update.message.reply_text(f"📤 0/{total}")
    for i, (uid, _, _, _) in enumerate(users, 1):
        try: await context.bot.send_message(uid, t); sent += 1
        except: failed += 1
        if i % 10 == 0 or i == total:
            try: await p.edit_text(f"📤 {i}/{total}")
            except: pass
    await p.edit_text(f"✅ Sent: {sent} | Failed: {failed}")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: await update.message.reply_text("Usage: /ban ID"); return
    try: uid = int(context.args[0])
    except: await update.message.reply_text("Invalid"); return
    ban_user(uid); await update.message.reply_text(f"✅ {uid} banned")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    try: uid = int(context.args[0])
    except: return
    unban_user(uid); await update.message.reply_text(f"✅ {uid} unbanned")

async def banned_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    b = get_banned_users()
    if not b: await update.message.reply_text("No banned"); return
    text = f"🚫 <b>BANNED ({len(b)})</b>\n\n"
    for uid, w in b: text += f"• <code>{uid}</code> — {w}\n"
    await update.message.reply_text(text, parse_mode='HTML')

# GROUP HELPERS
async def is_group_admin(update, context):
    if update.effective_chat.type not in ('group','supergroup'): return False
    try:
        m = await update.effective_chat.get_member(update.effective_user.id)
        return m.status in ('administrator','creator')
    except: return False

async def check_group_admin(update, context):
    if not await is_group_admin(update, context):
        await update.message.reply_text("🚫 Only for admins"); return False
    return True

async def setup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ('group','supergroup'): return
    if not await check_group_admin(update, context): return
    await setup_group_commands(context.application, update.effective_chat.id)
    await update.message.reply_text("✅ Setup done!")

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message with /mute"); return
    target = update.message.reply_to_message.from_user
    if target.id == update.effective_user.id:
        await update.message.reply_text("Can't mute self"); return
    dur = parse_duration(context.args[0]) if context.args else timedelta(hours=1)
    if not dur: dur = timedelta(hours=1)
    if dur > timedelta(days=366): dur = timedelta(days=366)
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id, user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now(timezone.utc) + dur
        )
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(f"🔇 <b>{html_lib.escape(name)}</b> muted for {human_duration(dur)}", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("🔊 Reply to a user's message with /unmute"); return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id, user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True, can_invite_users=True
            )
        )
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(f"🔊 <b>{html_lib.escape(name)}</b> unmuted.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: <code>{e}</code>", parse_mode='HTML')

async def mute_sticker_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("🎭 Reply to a user's message with /mutesticker"); return
    target = update.message.reply_to_message.from_user
    if target.id == update.effective_user.id:
        await update.message.reply_text("Can't mute yourself"); return
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id, user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=False,
                can_add_web_page_previews=True
            )
        )
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(f"🎭 <b>{html_lib.escape(name)}</b> — sticker va GIF yuborishi taqiqlandi.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a user's message with /warn"); return
    target = update.message.reply_to_message.from_user
    if target.id == update.effective_user.id:
        await update.message.reply_text("Can't warn yourself"); return
    try:
        m = await update.effective_chat.get_member(target.id)
        if m.status in ('administrator', 'creator'):
            await update.message.reply_text("❌ Can't warn admins"); return
    except: pass
    chat_id = update.effective_chat.id
    count = get_warn_count(chat_id, target.id) + 1
    set_warn_count(chat_id, target.id, count)
    name = f"@{target.username}" if target.username else target.full_name
    if count >= MAX_WARNINGS:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id, user_id=target.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now(timezone.utc) + WARN_MUTE_DURATION
            )
            await update.message.reply_text(f"🔇 <b>{html_lib.escape(name)}</b> — {MAX_WARNINGS} ta ogohlantirish!\nJazo: <b>1 soat mute</b>", parse_mode='HTML')
            clear_warn(chat_id, target.id)
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
    else:
        await update.message.reply_text(f"⚠️ <b>{html_lib.escape(name)}</b> ogohlantirildi!\nOgohlantirish: <b>{count}/{MAX_WARNINGS}</b>", parse_mode='HTML')

async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message with /unwarn"); return
    target = update.message.reply_to_message.from_user
    clear_warn(update.effective_chat.id, target.id)
    name = f"@{target.username}" if target.username else target.full_name
    await update.message.reply_text(f"✅ <b>{html_lib.escape(name)}</b> — ogohlantirishlar tozalandi.", parse_mode='HTML')

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message with /warns"); return
    target = update.message.reply_to_message.from_user
    count = get_warn_count(update.effective_chat.id, target.id)
    name = f"@{target.username}" if target.username else target.full_name
    await update.message.reply_text(f"⚠️ <b>{html_lib.escape(name)}</b> — ogohlantirishlar: <b>{count}/{MAX_WARNINGS}</b>", parse_mode='HTML')

async def add_bad_sticker_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("🎭 Reply to a sticker or GIF with /addbadsticker"); return
    rm = update.message.reply_to_message
    if not (rm.sticker or rm.animation):
        await update.message.reply_text("❌ Reply to a sticker or GIF only!"); return
    file_id = rm.sticker.file_unique_id if rm.sticker else rm.animation.file_unique_id
    add_bad_sticker(file_id)
    delete_media_verdict(file_id)
    await update.message.reply_text(f"✅ Sticker/GIF belgilandi!\nEndi uni kim yuborsa — <b>ogohlantirish</b> oladi.", parse_mode='HTML')

async def del_bad_sticker_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("🎭 Reply to a sticker or GIF with /delbadsticker"); return
    rm = update.message.reply_to_message
    if not (rm.sticker or rm.animation):
        await update.message.reply_text("❌ Reply to a sticker or GIF only!"); return
    file_id = rm.sticker.file_unique_id if rm.sticker else rm.animation.file_unique_id
    remove_bad_sticker(file_id)
    delete_media_verdict(file_id)
    await update.message.reply_text("✅ Sticker/GIF ro'yxatdan olib tashlandi.")

async def list_bad_stickers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    stickers = get_bad_stickers()
    if not stickers:
        await update.message.reply_text("📭 Taqiqlangan sticker/GIF yo'q."); return
    await update.message.reply_text(f"🎭 <b>Taqiqlangan sticker/GIF: {len(stickers)} ta</b>", parse_mode='HTML')

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    end = update.message.message_id
    start = update.message.reply_to_message.message_id if update.message.reply_to_message else max(1, end-50)
    s = await update.message.reply_text("🗑️ Clearing...")
    d = 0
    for mid in range(start, end+1):
        try: await context.bot.delete_message(update.effective_chat.id, mid); d += 1
        except: pass
    try: await s.delete()
    except: pass
    r = await context.bot.send_message(update.effective_chat.id, f"✅ Deleted: {d}")
    await asyncio.sleep(5)
    try: await r.delete()
    except: pass

async def on_bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.my_chat_member
    if not m: return
    if m.chat.type in ('group','supergroup') and m.new_chat_member.status in ('member','administrator'):
        try: await setup_group_commands(context.application, m.chat.id)
        except: pass

# ============================================================
# USERNAME / NAME CHECK
# ============================================================
_name_warn_cooldown = {}  # (chat_id, user_id) -> datetime

def check_user_name(update: Update):
    """(bad_word, label) yoki None. Cooldown bilan."""
    u = update.effective_user
    if not u:
        return None
    chat_id = update.effective_chat.id
    key = (chat_id, u.id)
    now_utc = datetime.now(timezone.utc)
    last = _name_warn_cooldown.get(key)
    if last and (now_utc - last) < NAME_WARN_COOLDOWN:
        return None

    for text, label in ((u.first_name or "", "ism"),
                        (u.last_name or "", "familiya"),
                        (u.username or "", "username")):
        if not text:
            continue
        bad = contains_bad_word(text)
        if bad:
            _name_warn_cooldown[key] = now_utc
            return bad, label
    return None

# ============================================================
# AUTO-MODERATION
# ============================================================
async def auto_moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return
    if update.effective_chat.type not in ('group', 'supergroup'): return
    if update.effective_user is None: return
    if await is_group_admin(update, context): return

    user = update.effective_user
    chat_id = update.effective_chat.id

    # --- 0) USERNAME / ISM ---
    name_check = check_user_name(update)
    if name_check:
        bad_word, label = name_check
        name = f"@{user.username}" if user.username else user.full_name
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(f"⚠️ <b>{html_lib.escape(name)}</b>\n\n"
                      f"Ism/{label}'da taqiqlangan so'z aniqlandi: <code>{html_lib.escape(bad_word)}</code>\n\n"
                      f"Iltimos, Telegram sozlamalaridan ismni o'zgartiring."),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Name warn error: {e}")
        # Xabarni o'chirmaymiz — ism uchun faqat ogohlantiramiz
        return

    violation_reason = None

    # --- 1) TEXT / CAPTION ---
    text_to_check = msg.text or msg.caption
    if text_to_check:
        bad_word = contains_bad_word(text_to_check)
        if bad_word:
            violation_reason = f"so'kinish: <code>{html_lib.escape(bad_word)}</code>"
        else:
            bad_emoji = contains_bad_emoji(text_to_check)
            if bad_emoji:
                violation_reason = f"yomon emoji: {bad_emoji}"

    # --- 2) MEDIA ---
    if not violation_reason and (msg.photo or msg.sticker or msg.animation or msg.video_note or msg.video):
        file_id = None
        file_unique_id = None
        mime_hint = None

        if msg.photo:
            best = msg.photo[-1]
            file_id = best.file_id
            file_unique_id = best.file_unique_id
            mime_hint = "image/jpeg"
        elif msg.sticker:
            file_id = msg.sticker.file_id
            file_unique_id = msg.sticker.file_unique_id
            if msg.sticker.is_video:
                mime_hint = "video/webm"
            elif msg.sticker.is_animated:
                mime_hint = "tgs"
            else:
                mime_hint = "image/webp"
        elif msg.animation:
            file_id = msg.animation.file_id
            file_unique_id = msg.animation.file_unique_id
            mime_hint = "video/mp4"
        elif msg.video_note:
            file_id = msg.video_note.file_id
            file_unique_id = msg.video_note.file_unique_id
            mime_hint = "video/mp4"
        elif msg.video:
            file_id = msg.video.file_id
            file_unique_id = msg.video.file_unique_id
            mime_hint = "video/mp4"

        if file_unique_id:
            # A) Qo'lda qora ro'yxat
            if file_unique_id in get_bad_stickers():
                violation_reason = "taqiqlangan sticker/GIF (qo'lda belgilangan)"
            # B) AI tekshiruvi
            elif AI_MEDIA_CHECK and GEMINI_API_KEY and mime_hint:
                cached = get_media_verdict(file_unique_id)
                if cached is not None:
                    is_bad, ai_reason = cached
                    if is_bad:
                        violation_reason = f"taqiqlangan media: {html_lib.escape(ai_reason or 'AI aniqladi')}"
                else:
                    try:
                        f = await context.bot.get_file(file_id)
                        fsize = getattr(f, 'file_size', 0) or 0
                        if fsize and fsize > 15 * 1024 * 1024:
                            logger.info(f"Media too large to analyze: {fsize} bytes — skip")
                        else:
                            fb = bytes(await f.download_as_bytearray())
                            is_bad, ai_reason = None, None

                            if mime_hint == "tgs":
                                try:
                                    frames = await asyncio.to_thread(tgs_to_png_frames, fb, 3, 512)
                                except AttributeError:
                                    frames = tgs_to_png_frames(fb, 3, 512)
                                if frames:
                                    is_bad, ai_reason = await analyze_media_content_with_ai(
                                        frames, ["image/png"] * len(frames)
                                    )
                                else:
                                    logger.warning(f"TGS render bo'lmadi: {file_unique_id}")
                            else:
                                is_bad, ai_reason = await analyze_media_content_with_ai(fb, mime_hint)

                            if is_bad is not None:
                                set_media_verdict(file_unique_id, is_bad, ai_reason)
                            if is_bad:
                                violation_reason = f"taqiqlangan media: {html_lib.escape(ai_reason or 'AI aniqladi')}"
                    except Exception as e:
                        logger.error(f"Media download error: {e}")

    if not violation_reason:
        return

    # --- 3) O'chirish ---
    try:
        await msg.delete()
    except Exception:
        pass

    # --- 4) Ogohlantirish ---
    count = get_warn_count(chat_id, user.id) + 1
    set_warn_count(chat_id, user.id, count)
    name = f"@{user.username}" if user.username else user.full_name

    if count >= MAX_WARNINGS:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id, user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now(timezone.utc) + WARN_MUTE_DURATION
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=(f"🔇 <b>{html_lib.escape(name)}</b> — {MAX_WARNINGS} ta ogohlantirish!\n\n"
                      f"Sabab: {violation_reason}\n"
                      f"Jazo: <b>1 soat mute</b>"),
                parse_mode='HTML'
            )
            clear_warn(chat_id, user.id)
        except Exception as e:
            logger.error(f"Auto-mute error: {e}")
    else:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(f"⚠️ <b>{html_lib.escape(name)}</b> ogohlantirildi!\n\n"
                      f"Sabab: {violation_reason}\n"
                      f"Ogohlantirish: <b>{count}/{MAX_WARNINGS}</b>\n\n"
                      f"<i>{MAX_WARNINGS - count} marta qoldi — keyin 1 soat mute.</i>"),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Warn msg error: {e}")

# ============================================================
# MENU SETUP
# ============================================================
async def setup_private_commands(app):
    try:
        await app.bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        logger.info("✅ Private cmds")
    except Exception as e:
        logger.error(f"Private cmd err: {e}")

async def setup_group_commands(app, cid):
    try:
        await app.bot.set_my_commands(GROUP_ADMIN_COMMANDS, scope=BotCommandScopeChatAdministrators(chat_id=cid))
        await app.bot.set_my_commands(GROUP_PUBLIC_COMMANDS, scope=BotCommandScopeChat(chat_id=cid))
    except Exception as e:
        logger.error(f"Group cmd err: {e}")

async def post_init(app):
    await setup_private_commands(app)
    logger.info("✅ post_init done")

# ============================================================
# BOT THREAD
# ============================================================
def run_bot_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def bot_main():
        req = HTTPXRequest(connection_pool_size=8, connect_timeout=30.0,
                           read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
        app = (Application.builder()
               .token(BOT_TOKEN)
               .request(req)
               .post_init(post_init)
               .concurrent_updates(True)
               .build())

        conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(rank_start, pattern="^rank_start$")],
            states={
                PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_player_id)],
                CLASSIC: [CallbackQueryHandler(handle_classic, pattern="^classic_")],
                ULTIMATE: [CallbackQueryHandler(handle_ultimate, pattern="^ultimate_")],
                KILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_kills)],
                PHOTO: [MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo)],
            },
            fallbacks=[CommandHandler("cancel", cancel)], per_message=False,
        )
        app.add_handler(CommandHandler("start", start))
        app.add_handler(conv)
        app.add_handler(CallbackQueryHandler(confirm_send, pattern="^confirm_send$"))
        app.add_handler(CallbackQueryHandler(cancel_post, pattern="^cancel_post$"))
        app.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
        app.add_handler(CommandHandler("admin", admin_stats))
        app.add_handler(CommandHandler("stats", admin_stats))
        app.add_handler(CommandHandler("users", users_list))
        app.add_handler(CommandHandler("broadcast", broadcast_cmd))
        app.add_handler(CommandHandler("ban", ban_cmd))
        app.add_handler(CommandHandler("unban", unban_cmd))
        app.add_handler(CommandHandler("banned", banned_list_cmd))
        app.add_handler(CommandHandler("setup", setup_cmd))
        app.add_handler(CommandHandler("mute", mute_cmd))
        app.add_handler(CommandHandler("unmute", unmute_cmd))
        app.add_handler(CommandHandler("mutesticker", mute_sticker_cmd))
        app.add_handler(CommandHandler("warn", warn_cmd))
        app.add_handler(CommandHandler("unwarn", unwarn_cmd))
        app.add_handler(CommandHandler("warns", warns_cmd))
        app.add_handler(CommandHandler("addbadsticker", add_bad_sticker_cmd))
        app.add_handler(CommandHandler("delbadsticker", del_bad_sticker_cmd))
        app.add_handler(CommandHandler("listbadstickers", list_bad_stickers_cmd))
        app.add_handler(CommandHandler("clear", clear_cmd))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.ChatType.PRIVATE, handle_broadcast_message))
        app.add_handler(ChatMemberHandler(on_bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))

        # AUTO-MODERATION — barcha media turlari + text
        app.add_handler(
            MessageHandler(
                (filters.TEXT | filters.CAPTION | filters.Sticker.ALL
                 | filters.ANIMATION | filters.PHOTO
                 | filters.VIDEO | filters.VIDEO_NOTE) &
                (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
                auto_moderate
            ),
            group=1
        )

        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        logger.info("✅ Bot polling started")

        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass

    try:
        loop.run_until_complete(bot_main())
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
    finally:
        try: loop.close()
        except: pass

# ============================================================
# MAIN
# ============================================================
def main():
    init_db()
    init_pg_db()
    logger.info("=" * 50)
    logger.info("🚀 TOMMY BOT v4.0 — IDEAL STRONG")
    logger.info("=" * 50)
    logger.info(f"🌐 Flask: port {PORT}")
    logger.info(f"📢 Channel: {CHANNEL_ID}")
    logger.info(f"⚠️ Bad words: {len(BAD_WORDS)}")
    logger.info(f"⚠️ Bad emojis: {len(BAD_EMOJIS)}")
    logger.info(f"🤖 AI media check: {'ON' if (AI_MEDIA_CHECK and GEMINI_API_KEY) else 'OFF'}")
    logger.info(f"🎞 Animatsion sticker (.tgs): {'ON' if RLOTTIE_AVAILABLE else 'OFF'}")
    logger.info(f"🎯 AI confidence threshold: {AI_CONFIDENCE_THRESHOLD}")
    logger.info(f"⚠️ Max warnings: {MAX_WARNINGS} → 1 soat mute")
    logger.info(f"👤 Name check cooldown: {NAME_WARN_COOLDOWN}")

    bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()

    logger.info("✅ All systems go!")
    run_flask()

if __name__ == "__main__":
    main()
