"""
TOMMY BOT — Complete + Moderation
No Gemini — fast deploy
"""
import os, io, re, sqlite3, asyncio, logging, threading
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

# ============================================================
# SETTINGS
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@TommyXcheat2")
OWNER_FIXED = "@Tommy_1727"
ADMIN_ID = 7383782449
PORT = int(os.getenv("PORT", 3000))
TZ_TASHKENT = timezone(timedelta(hours=5))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

PHOTO, PLAYER_ID, CLASSIC, ULTIMATE, KILLS = range(5)

# ============================================================
# SO'KINISHLAR RO'YXATI (300+ so'z, ko'p tilda)
# ============================================================
BAD_WORDS = [
    # O'ZBEKCHA
    "ahmoq","tentak","qo'tir","harom","jinni","onang","otang","jalab","qang'ir",
    "sikin","sik","kot","jalap","qotoq","qo'toq","yaramas","pastkash","razil",
    "fohisha","qanjiq","it","itvachcha","eshak","cho'chqa","sassiq","badbaxt",
    "bevafo","siktir","gandon","jalapvachcha","haromzoda","haromi","sikib",
    "sikaman","sikasan","sikadi","am","ami","aming","amingni","kotni","koting",
    "kotingni","onangni","otangni","singlingni","opangni","yaramasvachcha",
    "najos","iflos","hayvon","mol","qanjiqvachcha","sharmanda","beodob",
    "tarbiyasiz","besharm","uyatsiz","badbo'y","ablah","tuban","qabih",
    "dalbayob","sikdiring","qotoqing","qotoqingni","beobob","beobobvachcha",
    "beodobvachcha","jallod","jallodvachcha","tentakvachcha","ahmoqvachcha",
    # RUSCHA
    "блядь","бля","блять","блядина","блядство","сука","суки","сучка","хуй","хуя",
    "хую","хуйня","пизда","пизды","пиздец","ебать","ебал","ебала","ебёт","ебут",
    "еби","ебанный","ебаный","ёбаный","ебало","мудак","мудаки","мудила","гандон",
    "пидор","пидорас","пидр","залупа","долбоёб","долбоеб","уёбок","уебок",
    "уёбище","нахуй","нахуя","нихуя","похуй","охуеть","охуел","охуенный",
    "говно","говна","дерьмо","дерьма","жопа","жопы","жопу","срать","срал",
    "ссать","ссал","мразь","мрази","тварь","твари","скотина","сволочь",
    "падла","шалава","проститутка","шлюха","шлюхи","ублюдок","выродок",
    "дебил","кретин","идиот","дурак","придурок","олух","педофил","насильник",
    "убийца","убийство","зоофил",
    # INGLIZCHA
    "fuck","fucking","fucked","fucker","fuckers","motherfucker","shit","shits",
    "shitty","bullshit","bitch","bitches","asshole","assholes","ass","arse",
    "dick","dicks","dickhead","pussy","cunt","cunts","bastard","slut","whore",
    "idiot","idiots","stupid","dumb","moron","retard","crap","damn","hell",
    "piss","cock","cocks","nigger","nigga","faggot","fag","sex","sexual",
    "porn","porno","nude","naked","orgy","rape","raped","pedophile","kill",
    "murder","suicide","terrorist","drug","cocaine","heroin","marijuana",
    "wanker","twat","tosser","bollocks","bellend","prick","scumbag","loser",
    # TURKCHA
    "orospu","sikerim","sikeyim","sikim","siktir","amcık","amına","göt","götü",
    "yarrak","piç","pezevenk","şerefsiz","hain","alçak","aptal","salak",
    "gerizekalı","ahmak","beyinsiz","kaltak","sürtük","fahişe","kahpe","gavat",
    "ibne","puşt","yavşak","bok","sıç","osuruk",
    # QOZOQCHA
    "қотақ","сік","ам","жезөкше","оңбаған","сұмырай","арсыз","ұятсыз","ақымақ",
    "ақылсыз","есалаң","жынды","диуана","ұры","қарақшы","қанішер","зұлым",
    "қатыгез",
    # TOJIKCHA
    "коток","сик","ам","фоҳиша","бешарм","беҳаё","аблаҳ","аҳмақ","девона",
    "ҷиннӣ","дузд","қотил","золим","бераҳм",
    # ARABCHA
    "كس","كسمك","زب","طيز","شرموط","قحبة","عرص","خول","منيوك","متناك","ديوث",
    "كلب","خنزير","حمار","غبي","أحمق","مجنون","حقير","سافل","وقح","زبالة","خرا",
    "جنس","عاهرة","بورنو","عاري",
    # FORSCHA
    "کیر","کس","کص","کون","جنده","فاحشه","حرومزاده","بی‌شرف","بی‌ناموس","احمق",
    "خنگ","دیوانه","مجنون","کونی","پدرسگ","مادرجنده","کیرخور","کصکش","گوه",
    "شاش","گوز","لعنتی","کثافت","آشغال","زباله","سکس","پورن","لخت","تجاوز",
    "قتل","قاتل","خودکشی",
    # HINDCHA
    "चूतिया","गांड","गांडू","भोसड़ी","मादरचोद","बहनचोद","लंड","लौड़ा","चोद",
    "रंडी","कुट्टी","छिनाल","कमीना","हरामी","साला","कुत्ता","सुअर","गधा",
    "पागल","बेवकूफ","मूर्ख","गंदा","बदबू","पेशाब","टट्टी","गोबर","सेक्स",
    "पोर्न","नंगा","बलात्कार","हत्या","आत्महत्या","आतंकवादी","नशा",
    # ISPANCHA
    "puta","mierda","coño","joder","polla","verga","cabrón","pendejo","culero",
    "marica","joto","gilipollas","imbécil","idiota","estúpido","tonto","animal",
    "bestia","bruto","salvaje","asqueroso","basura","escoria","sexo","porno",
    "desnudo","orgía","violación","pedófilo","matar","asesino","suicidio",
    "terrorista","droga","cocaína","heroína","marihuana",
    # FRANSUZCHA
    "putain","pute","merde","connard","conne","salaud","salope","enculé","bite",
    "couille","chatte","nique","foutre","bordel","pédé","tapette","nègre","bicot",
    "crétin","imbécile","idiot","stupide","débile","abruti","saleté","ordure",
    "pourriture","vermine","charogne","crapule","voyou","bandit","criminel",
    "meurtrier","assassin","tueur","suicide","terroriste","drogue","sexe","porno",
    "nu","orgie","viol","pédophile",
    # NEMISCHA
    "scheiße","fick","ficken","arsch","arschloch","hurensohn","hure","nutte",
    "schlampe","fotze","schwanz","pimmel","muschi","wichser","spast","idiot",
    "dummkopf","trottel","depp","vollidiot","kacke","dreck","mist","kot",
    "abfall","müll","sex","porno","nackt","orgie","vergewaltigung","pädophil",
    "mord","töten","selbstmord","terrorist","droge","kokain","heroin","marihuana",
    # ITALYANCHA
    "cazzo","merda","stronzo","figa","fica","culo","puttana","troia","mignotta",
    "zoccola","bastardo","cornuto","coglione","minchia","pirla","scemo",
    "imbecille","idiota","stupido","cretino","deficiente","ritardato","schifo",
    "porco","sporco","lurido","lercio","immondo","feccia","verme","sesso",
    "porno","nudo","orgia","stupro","pedofilo","omicidio","assassino","suicidio",
    "terrorista","droga","cocaina","eroina","marijuana",
    # PORTUGALCHA
    "porra","merda","caralho","foder","foda","puta","puto","cabrão","corno",
    "viado","bicha","boiola","paneleiro","pica","pinto","xoxota","boceta",
    "buceta","peito","bunda","cu","idiota","imbecil","estúpido","burro",
    "otário","babaca","trouxa","palhaço","escroto","safado","piranha",
    "vagabunda","vadia","galinha","prostituta","sexo","pornô","nu","orgia",
    "estupro","pedófilo","assassino","matar","suicídio","terrorista","droga",
    "cocaína","heroína","maconha",
    # XITOYCHA
    "caonima","biaozi","bichi","diao","jiba","lanbi","shabi","shazi","shagua",
    "hundan","wangbadan","gou","zhu","chusheng","xingjiao","seqing","luoti",
    "qiangjian","sharen","zisha","kongbu",
    # YAPONCHA
    "kuso","chikusho","kisama","temee","omae","shine","baka","aho","manuke",
    "unko","manko","chinpo","oppai","ketsu","sekkusu","poruno","zenra","reipu",
    "korosu","jisatsu","terorisuto",
    # KOREYSCHA
    "ssibal","jot","byeongsin","gaesaekki","gaejot","jiral","nyeon","seks",
    "ganggan","salhae",
    # REKLAMA SO'ZLARI
    "sotiladi","sotaman","sotmoqchiman","arzon","aksiya","chegirma","promokod",
    "sertifikat","cheat","hack","lua","skript","script","vipkanal","vip kanal",
    "obuna","obuna bo'ling","reklama","sponsor","kanalga","kanalimiz",
]

# Taqiqlangan emojilar (stiker uchun)
BAD_EMOJIS = ["🍆","🍑","🔞","💦","👅","🍌","🥒","🌶️","💋","👙","🩲","🩱",
              "🔪","🩸","💉","🚬","💊","🔫","🗡️","☠️","💀","👺","🖕","🤬"]

# Reklama so'zlari
ADS_WORDS = ["sotiladi","sotaman","arzon","aksiya","chegirma","promokod","cheat",
             "hack","lua","skript","script","vipkanal","obuna","subscribe",
             "reklama","sponsor","instagram","youtube","tiktok","facebook"]

# ============================================================
# COMMANDS
# ============================================================
PRIVATE_COMMANDS = [
    BotCommand("start", "Start"), BotCommand("cancel", "Cancel"),
    BotCommand("admin", "Statistics"), BotCommand("stats", "Statistics"),
    BotCommand("users", "Users list"), BotCommand("broadcast", "Broadcast"),
    BotCommand("ban", "Ban user"), BotCommand("unban", "Unban user"),
    BotCommand("banned", "Banned list"),
]
GROUP_ADMIN_COMMANDS = [
    BotCommand("start", "Start"), BotCommand("setup", "Setup menu"),
    BotCommand("mute", "Mute (reply)"), BotCommand("unmute", "Unmute (reply)"),
    BotCommand("ban", "Ban (reply)"), BotCommand("unban", "Unban (reply)"),
    BotCommand("clear", "Clear messages"), BotCommand("warns", "Warnings (reply)"),
    BotCommand("resetwarns", "Reset warnings (reply)"),
]
GROUP_PUBLIC_COMMANDS = [BotCommand("start", "Start")]

# ============================================================
# HTML
# ============================================================
INDEX_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TOMMY BOT</title><script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>body{color:#fff;font-family:sans-serif;background:#0a0820;padding:20px;text-align:center}
h1{color:#4CAF50}.card{background:rgba(255,255,255,.08);padding:20px;border-radius:16px;max-width:400px;margin:20px auto}</style>
</head><body><h1>🎮 TOMMY BOT</h1><div class="card"><p>PUBG Mobile Statistics Panel</p></div>
<script>const tg=window.Telegram.WebApp;tg.expand();tg.ready();</script></body></html>"""

# ============================================================
# SQLITE
# ============================================================
def init_db():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, player_id TEXT, classic_rank TEXT, ultimate_rank TEXT, kills TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, chat_id INTEGER, count INTEGER DEFAULT 0, last_warned TEXT, PRIMARY KEY (user_id, chat_id))")
    conn.commit(); conn.close()

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
    r = c.fetchone(); conn.close(); return r is not None

def get_banned_users():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT user_id, banned_at FROM banned_users ORDER BY banned_at DESC")
    r = c.fetchall(); conn.close(); return r

def add_warning(uid, chat_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT count FROM warnings WHERE user_id=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone()
    if row:
        new = row[0] + 1
        c.execute("UPDATE warnings SET count=?, last_warned=? WHERE user_id=? AND chat_id=?",
            (new, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M"), uid, chat_id))
    else:
        new = 1
        c.execute("INSERT INTO warnings VALUES (?,?,?,?)", (uid, chat_id, new, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close(); return new

def get_warnings(uid, chat_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT count FROM warnings WHERE user_id=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone(); conn.close(); return row[0] if row else 0

def reset_warnings(uid, chat_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id=? AND chat_id=?", (uid, chat_id))
    conn.commit(); conn.close()

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
    except Exception: return False, "Could not read image."
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

async def is_group_admin(update, context):
    chat = update.effective_chat; user = update.effective_user
    if chat.type not in ('group','supergroup'): return False
    try:
        m = await chat.get_member(user.id)
        return m.status in ('administrator','creator')
    except Exception: return False

async def check_group_admin(update, context):
    if not await is_group_admin(update, context):
        await update.message.reply_text("🚫 <b>Faqat guruh adminlari uchun.</b>", parse_mode='HTML')
        return False
    return True

# ============================================================
# MENU SETUP
# ============================================================
async def setup_private_commands(application):
    try:
        await application.bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    except Exception as e: logger.error(f"Private cmds: {e}")

async def setup_group_commands(application, chat_id):
    try:
        await application.bot.set_my_commands(GROUP_ADMIN_COMMANDS, scope=BotCommandScopeChatAdministrators(chat_id=chat_id))
        await application.bot.set_my_commands(GROUP_PUBLIC_COMMANDS, scope=BotCommandScopeChat(chat_id=chat_id))
    except Exception as e: logger.error(f"Group cmds: {e}")

async def post_init(application):
    await setup_private_commands(application)

# ============================================================
# SEND TO TELEGRAM
# ============================================================
def send_to_telegram(image_bytes, caption, mime_type='image/jpeg'):
    try:
        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {'photo': ('screenshot.jpg', image_bytes, mime_type)}
        data = {'chat_id': CHANNEL_ID, 'caption': caption}
        return requests.post(url, files=files, data=data, timeout=60).json()
    except Exception as e:
        return {'ok': False, 'description': str(e)}

# ============================================================
# FLASK
# ============================================================
flask_app = Flask(__name__)
CORS(flask_app, resources={r"/*": {"origins": "*"}})

@flask_app.route('/', methods=['GET'])
def index(): return Response(INDEX_HTML, mimetype='text/html')

@flask_app.route('/send-feedback', methods=['POST'])
def send_feedback():
    try:
        if 'photo' not in request.files: return jsonify({'ok': False, 'description': 'Photo required!'}), 400
        photo = request.files['photo']
        if photo.filename == '': return jsonify({'ok': False, 'description': 'No file'}), 400
        pb = photo.read()
        if len(pb) > 5*1024*1024: return jsonify({'ok': False, 'description': 'Too large'}), 400
        caption = request.form.get('caption', '')
        if not caption: return jsonify({'ok': False, 'description': 'Caption required!'}), 400
        r = send_to_telegram(pb, caption, photo.mimetype or 'image/jpeg')
        return jsonify({'ok': r.get('ok', False), 'description': r.get('description')}), 200 if r.get('ok') else 500
    except Exception as e:
        return jsonify({'ok': False, 'description': str(e)}), 500

def run_flask():
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False, threaded=True)

# ============================================================
# USER COMMANDS
# ============================================================
async def start(update, context):
    u = update.effective_user
    if update.effective_chat.type == 'private' and is_banned(u.id):
        await update.message.reply_text("🚫 Siz botdan bloklangansiz.\nContact: @Tommy_1727", parse_mode='HTML'); return
    save_user(u.id, u.username, u.first_name)
    context.user_data.clear()
    kb = [[InlineKeyboardButton("🏆 RANK STATISTICA", callback_data="rank_start")],
          [InlineKeyboardButton("📞 Contact", callback_data="contact")]]
    await update.message.reply_text("🤖 TOMMY BOT\n\nPUBG Mobile statistikangizni yuboring:", reply_markup=InlineKeyboardMarkup(kb))

async def rank_start(update, context):
    q = update.callback_query; await q.answer(); context.user_data.clear()
    await q.message.reply_text("🆔 Step 1\n\nPUBG Mobile ID:\n\n• 11 ta raqam\n• 5 yoki 6 bilan boshlanadi\n\nMisol: 52254689580")
    return PLAYER_ID

async def handle_player_id(update, context):
    pid = update.message.text.strip()
    if not is_valid_player_id(pid):
        await update.message.reply_text("❌ Noto'g'ri ID! Qayta yuboring:"); return PLAYER_ID
    context.user_data['player_id'] = pid
    ranks = ["Bronze","Silver","Gold","Platinum","Diamond","Crown","Ace","Ace Master","Ace Dominator","Conqueror"]
    kb = [[InlineKeyboardButton(f"🏆 {r}", callback_data=f"classic_{r}")] for r in ranks]
    await update.message.reply_text(f"✅ ID: {pid}\n\n👑 Step 2\n\nCLASSIC RANK:", reply_markup=InlineKeyboardMarkup(kb))
    return CLASSIC

async def handle_classic(update, context):
    q = update.callback_query; await q.answer()
    rank = q.data.replace("classic_", ""); context.user_data['classic_rank'] = rank
    await q.message.delete()
    ranks = ["Vanguard","Exceed","Supreme","Peerless","Legend"]
    kb = [[InlineKeyboardButton(f"🏆 {r}", callback_data=f"ultimate_{r}")] for r in ranks]
    await q.message.reply_text(f"✅ Classic: {rank}\n\n👑 Step 3\n\nULTIMATE ROYALE RANK:", reply_markup=InlineKeyboardMarkup(kb))
    return ULTIMATE

async def handle_ultimate(update, context):
    q = update.callback_query; await q.answer()
    rank = q.data.replace("ultimate_", ""); context.user_data['ultimate_rank'] = rank
    await q.message.delete()
    await q.message.reply_text(f"✅ Ultimate: {rank}\n\n💀 Step 4\n\nKILLS (1-100):")
    return KILLS

async def handle_kills(update, context):
    kills = update.message.text.strip()
    if not kills.isdigit() or not (1 <= int(kills) <= 100):
        await update.message.reply_text("❌ 1-100 orasida raqam:"); return KILLS
    context.user_data['kills'] = kills
    await update.message.reply_text(f"✅ Kills: {kills}\n\n📸 Step 5\n\nSkrinshot yuboring:")
    return PHOTO

async def handle_photo(update, context):
    photo = update.message.photo[-1]
    msg = await update.message.reply_text("⏳ Tekshirilmoqda...")
    try:
        f = await context.bot.get_file(photo.file_id)
        fb = bytes(await f.download_as_bytearray())
        ok, reason = validate_pubg_screenshot(fb)
        if not ok:
            await msg.delete(); await update.message.reply_text(f"❌ {reason}\nQayta yuboring:"); return PHOTO
        pid = context.user_data.get('player_id',''); cr = context.user_data.get('classic_rank','Unknown')
        ur = context.user_data.get('ultimate_rank','Unknown'); k = context.user_data.get('kills','0')
        user = update.effective_user
        owner_d = f"@{user.username}" if user.username else user.full_name
        ts = datetime.now(TZ_TASHKENT).strftime('%H:%M %d.%m.%Y')
        caption = (f"👤 OWNER: {owner_d}\n🎮 Player ID: {hide_id(pid)}\n🏆 CLASSIC: {cr}\n"
                   f"🏆 ULTIMATE: {ur}\n🕒 TIME: {ts}\n💀 KILL: {k}\n\n👤 OWNER: {OWNER_FIXED} ✅")
        kb = [[InlineKeyboardButton("✅ Yuborish", callback_data="confirm_send")],
              [InlineKeyboardButton("❌ Bekor", callback_data="cancel_post")]]
        await msg.delete()
        context.user_data['photo_id'] = photo.file_id
        context.user_data['caption'] = caption
        await update.message.reply_photo(photo=photo.file_id, caption=f"🤖 Preview:\n\n{caption}", reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Photo: {e}"); await update.message.reply_text(f"❌ {e}"); return PHOTO

async def confirm_send(update, context):
    q = update.callback_query; await q.answer()
    pid = context.user_data.get('photo_id'); cap = context.user_data.get('caption','')
    if not pid: await q.message.reply_text("❌ Rasm topilmadi."); return
    try:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=pid, caption=cap)
        user = update.effective_user
        save_post(user.id, context.user_data.get('player_id',''), context.user_data.get('classic_rank',''),
                  context.user_data.get('ultimate_rank',''), context.user_data.get('kills',''))
        await q.message.delete(); await q.message.reply_text("✅ Kanalga yuborildi!")
    except Exception as e: await q.message.reply_text(f"❌ {e}")
    context.user_data.clear()

async def cancel_post(update, context):
    q = update.callback_query; await q.answer(); context.user_data.clear()
    await q.message.delete(); await q.message.reply_text("❌ Bekor qilindi.")

async def contact(update, context):
    q = update.callback_query; await q.answer()
    await q.message.reply_text("Contact: @Tommy_1727")

async def cancel(update, context):
    context.user_data.clear(); context.user_data['broadcast_mode'] = False
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END

# ============================================================
# OWNER COMMANDS
# ============================================================
async def admin_stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    text = (f"📊 <b>STATISTIKA</b>\n\n👥 Users: <b>{get_users_count()}</b>\n"
            f"🆕 Bugun: <b>{get_today_users_count()}</b>\n📸 Postlar: <b>{get_posts_count()}</b>\n"
            f"🚫 Bloklangan: <b>{len(get_banned_users())}</b>\n")
    users = get_all_users(10)
    if users:
        text += "\n<b>Oxirgi 10 user:</b>\n"
        for uid, un, fn, ja in users:
            text += f"• {('@'+un) if un else fn} — {ja}\n"
    await update.message.reply_text(text, parse_mode='HTML')

async def users_list(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    users = get_all_users(100)
    if not users: await update.message.reply_text("Foydalanuvchi yo'q."); return
    text = f"👥 <b>USERS ({len(users)})</b>\n\n"
    for i, (uid, un, fn, ja) in enumerate(users, 1):
        text += f"{i}. {('@'+un) if un else fn} — {ja}\n    ID: <code>{uid}</code>\n"
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await update.message.reply_text(chunk, parse_mode='HTML')

async def broadcast_cmd(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    context.user_data['broadcast_mode'] = True
    await update.message.reply_text("📢 Broadcast rejimi. Xabar yuboring. /cancel — bekor qilish.")

async def handle_broadcast_message(update, context):
    if not context.user_data.get('broadcast_mode'): return
    if update.effective_user.id != ADMIN_ID: return
    t = update.message.text
    if not t: return
    context.user_data['broadcast_mode'] = False
    users = get_all_users(1000); total = len(users); sent = 0; failed = 0
    p = await update.message.reply_text(f"📤 0/{total}")
    for idx, (uid, _, _, _) in enumerate(users, 1):
        try: await context.bot.send_message(chat_id=uid, text=t); sent += 1
        except Exception: failed += 1
        if idx % 10 == 0 or idx == total:
            try: await p.edit_text(f"📤 {idx}/{total}")
            except Exception: pass
    await p.edit_text(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}")

async def ban_cmd(update, context):
    chat = update.effective_chat; user = update.effective_user
    if chat.type == 'private':
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Siz admin emassiz!"); return
    else:
        if not await check_group_admin(update, context): return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            uid = int(context.args[0]); target = await context.bot.get_chat(uid)
        except Exception:
            await update.message.reply_text("❌ Noto'g'ri ID."); return
    else:
        await update.message.reply_text("Javob qilib /ban yozing yoki /ban ID."); return
    if target.id == user.id:
        await update.message.reply_text("❌ O'zingizni bloklay olmaysiz."); return
    if chat.type in ('group','supergroup'):
        try:
            m = await chat.get_member(target.id)
            if m.status in ('administrator','creator'):
                await update.message.reply_text("❌ Adminni bloklab bo'lmaydi."); return
        except Exception: pass
    name = f"@{target.username}" if target.username else target.full_name
    try:
        if chat.type == 'private':
            ban_user(target.id)
            await update.message.reply_text(f"✅ {name} botdan bloklandi.", parse_mode='HTML')
        else:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=target.id)
            await update.message.reply_text(f"🔨 <b>{name}</b> guruhdan bloklandi.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", parse_mode='HTML')

async def unban_cmd(update, context):
    chat = update.effective_chat; user = update.effective_user
    if chat.type == 'private':
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Siz admin emassiz!"); return
    else:
        if not await check_group_admin(update, context): return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            uid = int(context.args[0]); target = await context.bot.get_chat(uid)
        except Exception:
            await update.message.reply_text("❌ Noto'g'ri ID."); return
    else:
        await update.message.reply_text("Javob qilib /unban yozing yoki /unban ID."); return
    name = f"@{target.username}" if target.username else target.full_name
    try:
        if chat.type == 'private':
            unban_user(target.id)
            await update.message.reply_text(f"✅ {name} blokdan chiqarildi.", parse_mode='HTML')
        else:
            await context.bot.unban_chat_member(chat_id=chat.id, user_id=target.id)
            await update.message.reply_text(f"🔊 <b>{name}</b> blokdan chiqarildi.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", parse_mode='HTML')

async def banned_list_cmd(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    b = get_banned_users()
    if not b: await update.message.reply_text("✅ Bloklangan yo'q."); return
    text = f"🚫 <b>BANNED ({len(b)})</b>\n\n"
    for uid, when in b:
        text += f"• <code>{uid}</code> — {when}\n"
    await update.message.reply_text(text, parse_mode='HTML')

# ============================================================
# GROUP ADMIN COMMANDS
# ============================================================
async def setup_cmd(update, context):
    chat = update.effective_chat
    if chat.type not in ('group','supergroup'):
        await update.message.reply_text("❌ Faqat guruhlarda."); return
    if not await check_group_admin(update, context): return
    await setup_group_commands(context.application, chat.id)
    await update.message.reply_text("✅ Menyu o'rnatildi!", parse_mode='HTML')

async def mute_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat; user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("Javob qilib /mute 1h yozing."); return
    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("❌ O'zingizni mute qila olmaysiz."); return
    try:
        m = await chat.get_member(target.id)
        if m.status in ('administrator','creator'):
            await update.message.reply_text("❌ Adminni mute qilib bo'lmaydi."); return
    except Exception: pass
    duration = parse_duration(context.args[0]) if context.args else timedelta(hours=1)
    if not duration:
        await update.message.reply_text("❌ Noto'g'ri vaqt. Misol: 30s, 5m, 2h, 1d, 1w"); return
    if duration > timedelta(days=366): duration = timedelta(days=366)
    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now(timezone.utc) + duration)
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(f"🔇 <b>{name}</b> mute qilindi — <b>{human_duration(duration)}</b>.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", parse_mode='HTML')

async def unmute_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat; user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("Javob qilib /unmute yozing."); return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True, can_invite_users=True))
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(f"🔊 <b>{name}</b> mute dan chiqarildi.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", parse_mode='HTML')

async def clear_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    end_id = update.message.message_id
    start_id = update.message.reply_to_message.message_id if update.message.reply_to_message else max(1, end_id-50)
    status = await update.message.reply_text("🗑️ Tozalanmoqda...")
    d = 0; f = 0
    for mid in range(start_id, end_id+1):
        try: await context.bot.delete_message(chat_id=chat.id, message_id=mid); d += 1
        except Exception: f += 1
    try: await status.delete()
    except Exception: pass
    r = await context.bot.send_message(chat_id=chat.id, text=f"✅ O'chirildi: {d}\n❌ Xato: {f}")
    await asyncio.sleep(5)
    try: await r.delete()
    except Exception: pass

async def warns_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    if not update.message.reply_to_message:
        await update.message.reply_text("Javob qilib /warns yozing."); return
    target = update.message.reply_to_message.from_user
    count = get_warnings(target.id, chat.id)
    name = f"@{target.username}" if target.username else target.full_name
    await update.message.reply_text(f"⚠️ <b>{name}</b>: <b>{count}/5</b> ogohlantirish.", parse_mode='HTML')

async def resetwarns_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    if not update.message.reply_to_message:
        await update.message.reply_text("Javob qilib /resetwarns yozing."); return
    target = update.message.reply_to_message.from_user
    reset_warnings(target.id, chat.id)
    name = f"@{target.username}" if target.username else target.full_name
    await update.message.reply_text(f"✅ <b>{name}</b> ogohlantirishlari tozalandi.", parse_mode='HTML')

# ============================================================
# MODERATSIYA
# ============================================================
async def process_violation(update, context, reason: str):
    chat = update.effective_chat; user = update.effective_user
    name = f"@{user.username}" if user.username else user.full_name
    try:
        if update.message: await update.message.delete()
    except Exception as e:
        logger.error(f"Delete error: {e}")
    count = add_warning(user.id, chat.id)
    if count >= 5:
        try:
            await context.bot.restrict_chat_member(chat_id=chat.id, user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now(timezone.utc) + timedelta(hours=1))
            reset_warnings(user.id, chat.id)
            w = await context.bot.send_message(chat_id=chat.id,
                text=f"🚫 <b>{name}</b> 5 marta qoidabuzarlik qildi. <b>1 soatga mute</b>!\nSabab: <b>{reason}</b>",
                parse_mode='HTML')
        except Exception as e:
            logger.error(f"Mute error: {e}"); return
    else:
        w = await context.bot.send_message(chat_id=chat.id,
            text=f"⚠️ <b>{name}</b>\nSabab: <b>{reason}</b>\nOgohlantirish: <b>{count}/5</b>\n<i>5 tadan ko'p bo'lsa 1 soatga mute qilinasiz!</i>",
            parse_mode='HTML')
    await asyncio.sleep(10)
    try: await w.delete()
    except Exception: pass

async def text_filter(update, context):
    if not update.message or not update.message.text: return
    if await is_group_admin(update, context): return
    text = update.message.text; low = text.lower()
    words = re.findall(r'\b\w+\b', low, flags=re.UNICODE)
    found_bad = [w for w in words if w in BAD_WORDS]
    if not found_bad:
        for bw in BAD_WORDS:
            if len(bw) >= 5 and bw in low:
                found_bad.append(bw); break
    links = re.findall(r'(https?://\S+|t\.me/\S+|www\.\S+)', low)
    usernames = re.findall(r'@[a-zA-Z0-9_]{4,}', text)
    phones = re.findall(r'(\+?\d[\d\s\-\(\)]{8,}\d)', text)
    ads = [w for w in words if w in ADS_WORDS]
    fwd = update.message.forward_from_chat is not None or update.message.forward_from is not None
    emoji_count = len(re.findall(r'[\U0001F300-\U0001FAFF\u2600-\u27BF]', text))
    reason = None
    if found_bad: reason = f"so'kinish ({', '.join(set(found_bad))[:30]})"
    elif links: reason = "havola"
    elif usernames: reason = "reklama (@username)"
    elif phones: reason = "telefon raqam"
    elif ads: reason = f"reklama ({', '.join(set(ads))[:30]})"
    elif fwd: reason = "kanaldan forward"
    elif emoji_count >= 6: reason = "emoji spam"
    if reason: await process_violation(update, context, reason)

async def sticker_filter(update, context):
    if not update.message or not update.message.sticker: return
    if await is_group_admin(update, context): return
    sticker = update.message.sticker
    emoji = sticker.emoji or ""
    if any(e in emoji for e in BAD_EMOJIS):
        await process_violation(update, context, f"taqiqlangan stiker {emoji}")
        return
    # Barcha stikerlar o'chiriladi (adminlar bundan mustasno)
    await process_violation(update, context, f"stiker {emoji}")

async def media_filter(update, context):
    if not update.message: return
    if await is_group_admin(update, context): return
    reason = None
    if update.message.animation: reason = "GIF/animatsiya"
    elif update.message.video: reason = "video"
    elif update.message.video_note: reason = "video xabar"
    elif update.message.photo: reason = "rasm"
    elif update.message.voice: reason = "ovozli xabar"
    elif update.message.audio: reason = "audio fayl"
    elif update.message.document: reason = "dokument"
    elif update.message.location: reason = "joylashuv"
    elif update.message.contact: reason = "kontakt"
    if reason: await process_violation(update, context, reason)

# ============================================================
# BOT ADDED
# ============================================================
async def on_bot_added_to_group(update, context):
    mcm = update.my_chat_member
    if not mcm: return
    chat = mcm.chat; ns = mcm.new_chat_member.status
    if chat.type in ('group','supergroup'):
        if ns in ('member','administrator'):
            await setup_group_commands(context.application, chat.id)

# ============================================================
# START
# ============================================================
def start_bot():
    logger.info("🤖 Bot starting...")
    try:
        req = HTTPXRequest(connection_pool_size=8, connect_timeout=30.0,
                           read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
        application = Application.builder().token(BOT_TOKEN).request(req).post_init(post_init).build()
        conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(rank_start, pattern="^rank_start$")],
            states={
                PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_player_id)],
                CLASSIC: [CallbackQueryHandler(handle_classic, pattern="^classic_")],
                ULTIMATE: [CallbackQueryHandler(handle_ultimate, pattern="^ultimate_")],
                KILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_kills)],
                PHOTO: [MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo)],
            },
            fallbacks=[CommandHandler("cancel", cancel)], per_message=False)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv)
        application.add_handler(CallbackQueryHandler(confirm_send, pattern="^confirm_send$"))
        application.add_handler(CallbackQueryHandler(cancel_post, pattern="^cancel_post$"))
        application.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
        # Owner
        application.add_handler(CommandHandler("admin", admin_stats))
        application.add_handler(CommandHandler("stats", admin_stats))
        application.add_handler(CommandHandler("users", users_list))
        application.add_handler(CommandHandler("broadcast", broadcast_cmd))
        application.add_handler(CommandHandler("ban", ban_cmd))
        application.add_handler(CommandHandler("unban", unban_cmd))
        application.add_handler(CommandHandler("banned", banned_list_cmd))
        # Group admin
        application.add_handler(CommandHandler("setup", setup_cmd))
        application.add_handler(CommandHandler("mute", mute_cmd))
        application.add_handler(CommandHandler("unmute", unmute_cmd))
        application.add_handler(CommandHandler("clear", clear_cmd))
        application.add_handler(CommandHandler("warns", warns_cmd))
        application.add_handler(CommandHandler("resetwarns", resetwarns_cmd))
        # Moderatsiya
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, text_filter))
        application.add_handler(MessageHandler(filters.Sticker & filters.ChatType.GROUPS, sticker_filter))
        application.add_handler(MessageHandler(
            (filters.ANIMATION | filters.VIDEO | filters.VIDEO_NOTE | filters.VOICE |
             filters.AUDIO | filters.Document | filters.PHOTO | filters.LOCATION | filters.CONTACT)
            & filters.ChatType.GROUPS, media_filter))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.ChatType.PRIVATE,
            handle_broadcast_message))
        application.add_handler(ChatMemberHandler(on_bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))
        logger.info("✅ Bot started")
        application.run_polling(stop_signals=None, drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

def main():
    init_db()
    threading.Thread(target=start_bot, daemon=True).start()
    logger.info(f"🌐 Flask port: {PORT}")
    run_flask()

if __name__ == "__main__":
    main()
