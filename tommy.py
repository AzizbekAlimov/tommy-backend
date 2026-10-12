"""
TOMMY BOT — Single complete file
Bot asks user step-by-step (like WebApp)
"""
import os, io, re, json, time, sqlite3, asyncio, logging, colorsys, threading
from io import BytesIO
from datetime import datetime

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

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini AI connected")

# Conversation states
PHOTO, PLAYER_ID, CLASSIC, ULTIMATE, KILLS = range(5)

# ============================================================
# HTML (WebApp) — unchanged
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
body{color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh;padding:16px;padding-bottom:30px;background:#0a0820;overflow-x:hidden;position:relative}
.container{position:relative;z-index:1;max-width:500px;margin:0 auto}
.header{text-align:center;padding:55px 0 30px}
.header .logo{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#4CAF50,#2196F3);display:flex;align-items:center;justify-content:center;margin:0 auto 15px;font-size:40px;box-shadow:0 8px 24px rgba(76,175,80,0.4)}
.header h1{color:#4CAF50;font-size:26px;font-weight:800}
.header p{color:#aaa;font-size:13px}
.card{background:rgba(255,255,255,0.06);border-radius:18px;padding:18px;margin-bottom:14px;border:1px solid rgba(255,255,255,0.08)}
.card-title{color:#4CAF50;font-size:15px;font-weight:700;margin-bottom:14px;text-transform:uppercase}
.info-row{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid rgba(255,255,255,0.06)}
.info-row:last-child{border-bottom:none}
.info-label{color:#999;font-size:13px}
.info-value{color:#fff;font-weight:600;font-size:13px;text-align:right;max-width:60%}
.info-value.green{color:#4CAF50}
.input-group{margin-bottom:12px}
.input-group input{width:100%;padding:14px 16px;background:rgba(255,255,255,0.08);border:1.5px solid rgba(255,255,255,0.15);border-radius:12px;color:#fff;font-size:15px;outline:none}
.input-group input::placeholder{color:#666}
.input-group input.error{border-color:#f44336}
.input-group input.success{border-color:#4CAF50}
.photo-upload-box{width:100%;padding:30px 20px;background:rgba(255,255,255,0.06);border:2px dashed rgba(76,175,80,0.5);border-radius:14px;text-align:center;cursor:pointer;margin-bottom:12px}
.photo-upload-box .icon{font-size:42px;display:block;margin-bottom:10px}
.photo-upload-box .text{color:#4CAF50;font-size:14px;font-weight:600}
.photo-upload-box .subtext{color:#888;font-size:11px;margin-top:6px}
#photo-input{display:none}
.photo-preview{display:none;width:100%;max-height:220px;object-fit:cover;border-radius:14px;margin-bottom:12px;border:2px solid #4CAF50}
.photo-preview.show{display:block}
.rank-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:8px}
.rank-item{background:rgba(76,175,80,0.15);border:1px solid rgba(76,175,80,0.3);border-radius:10px;padding:12px;text-align:center;font-size:12px;color:#4CAF50;cursor:pointer}
.rank-item.selected{background:#4CAF50;color:#fff}
.rank-item.gold{background:rgba(255,193,7,0.15);color:#FFC107}
.rank-item.gold.selected{background:#FFC107;color:#000}
.rank-item.blue{background:rgba(33,150,243,0.15);color:#2196F3}
.rank-item.blue.selected{background:#2196F3;color:#fff}
.rank-item.purple{background:rgba(156,39,176,0.15);color:#CE93D8}
.rank-item.purple.selected{background:#9C27B0;color:#fff}
.btn{display:flex;align-items:center;justify-content:center;width:100%;padding:15px;border:none;border-radius:14px;font-size:15px;font-weight:700;cursor:pointer;margin-top:12px}
.btn-primary{background:linear-gradient(135deg,#4CAF50,#45a049);color:#fff}
.btn-secondary{background:linear-gradient(135deg,#2196F3,#1976D2);color:#fff}
.btn-warning{background:linear-gradient(135deg,#FF9800,#F57C00);color:#fff}
.btn-outline{background:transparent;border:1.5px solid rgba(255,255,255,0.2);color:#ccc}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700}
.badge-green{background:rgba(76,175,80,0.2);color:#4CAF50}
.badge-blue{background:rgba(33,150,243,0.2);color:#2196F3}
.status-overlay{position:fixed;inset:0;z-index:99999;display:none;align-items:center;justify-content:center;padding:24px;background:rgba(5,3,18,0.75)}
.status-overlay.show{display:flex}
.status-box{width:100%;max-width:360px;background:linear-gradient(160deg,rgba(28,22,60,0.98),rgba(14,10,34,0.98));border-radius:22px;padding:32px;text-align:center;border:1.5px solid rgba(255,255,255,0.1)}
.status-icon{font-size:56px;display:block;margin-bottom:18px}
.status-title{font-size:18px;font-weight:800;margin-bottom:8px}
.status-title.loading{color:#FFC107}
.status-title.success{color:#4CAF50}
.status-title.error{color:#f44336}
.status-desc{font-size:13px;color:#aaa;margin-bottom:20px;white-space:pre-line}
.status-btn{width:100%;padding:14px;border:none;border-radius:14px;font-size:14px;font-weight:700;cursor:pointer}
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
  <div class="card">
    <div class="card-title">🆔 PUBG Mobile ID</div>
    <div class="input-group"><input type="tel" id="player-id" placeholder="Enter 11-digit ID" maxlength="11" inputmode="numeric"></div>
  </div>
  <div class="card">
    <div class="card-title">📸 Screenshot</div>
    <div class="photo-upload-box" id="photo-box">
      <span class="icon">📤</span>
      <div class="text">Tap to upload</div>
      <div class="subtext">JPG, PNG • Max 5MB</div>
    </div>
    <input type="file" id="photo-input" accept="image/*">
    <img id="photo-preview" class="photo-preview" alt="Preview">
  </div>
  <div class="card">
    <div class="card-title">👑 CLASSIC RANKS</div>
    <div class="rank-grid" id="classic-ranks">
      <div class="rank-item" data-rank="Bronze">Bronze</div><div class="rank-item" data-rank="Silver">Silver</div>
      <div class="rank-item" data-rank="Gold">Gold</div><div class="rank-item" data-rank="Platinum">Platinum</div>
      <div class="rank-item blue" data-rank="Diamond">Diamond</div><div class="rank-item blue" data-rank="Crown">Crown</div>
      <div class="rank-item gold" data-rank="Ace">Ace</div><div class="rank-item gold" data-rank="Ace Master">Ace Master</div>
      <div class="rank-item purple" data-rank="Ace Dominator">Ace Dominator</div><div class="rank-item purple" data-rank="Conqueror">Conqueror</div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">👑 ULTIMATE ROYALE</div>
    <div class="rank-grid" id="ultimate-ranks">
      <div class="rank-item" data-rank="Vanguard">Vanguard</div><div class="rank-item" data-rank="Exceed">Exceed</div>
      <div class="rank-item blue" data-rank="Supreme">Supreme</div><div class="rank-item blue" data-rank="Peerless">Peerless</div>
      <div class="rank-item purple" data-rank="Legend">Legend</div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">💀 KILLS</div>
    <div class="input-group"><input type="tel" id="kills" placeholder="1-100" maxlength="3" inputmode="numeric"></div>
  </div>
  <button class="btn btn-primary" onclick="openStatistics()">📊 STATISTICS</button>
  <button class="btn btn-secondary" onclick="startNew()">📤 START NEW</button>
  <button class="btn btn-warning" onclick="openChannel()">📢 Go to Channel</button>
  <button class="btn btn-outline" onclick="closeApp()">❌ Close</button>
</div>
<div class="status-overlay" id="status-overlay">
  <div class="status-box">
    <div class="status-icon" id="status-icon">⏳</div>
    <div class="status-title" id="status-title">Sending...</div>
    <div class="status-desc" id="status-desc">Please wait...</div>
    <button class="status-btn" id="status-btn" onclick="closeStatus()">OK</button>
  </div>
</div>
<script>
const tg=window.Telegram.WebApp;tg.expand();tg.ready();tg.setHeaderColor('#0a0820');tg.setBackgroundColor('#0a0820');
const API_URL="/send-feedback";const CHANNEL_USERNAME="@TommyXcheat2";
const user=tg.initDataUnsafe.user;
if(user){const fn=((user.first_name||'')+' '+(user.last_name||'')).trim();document.getElementById('user-name').innerText=fn||`User #${user.id}`;document.getElementById('user-username').innerText=user.username?'@'+user.username:'—';document.getElementById('user-id').innerText=user.id;}
function buildOwnerInfo(){if(!user)return{plain:'Unknown'};if(user.username)return{plain:'@'+user.username};const fn=((user.first_name||'')+' '+(user.last_name||'')).trim();return{plain:fn?`${fn}`:`User #${user.id}`};}
let selectedClassic=null,selectedUltimate=null;
document.querySelectorAll('#classic-ranks .rank-item').forEach(item=>{item.addEventListener('click',()=>{document.querySelectorAll('#classic-ranks .rank-item').forEach(i=>i.classList.remove('selected'));item.classList.add('selected');selectedClassic=item.dataset.rank;});});
document.querySelectorAll('#ultimate-ranks .rank-item').forEach(item=>{item.addEventListener('click',()=>{document.querySelectorAll('#ultimate-ranks .rank-item').forEach(i=>i.classList.remove('selected'));item.classList.add('selected');selectedUltimate=item.dataset.rank;});});
const photoBox=document.getElementById('photo-box');const photoInput=document.getElementById('photo-input');const photoPreview=document.getElementById('photo-preview');
let photoValid=false;
photoBox.addEventListener('click',()=>photoInput.click());
photoInput.addEventListener('change',function(e){const file=e.target.files[0];if(!file)return;if(file.size>5*1024*1024){tg.showAlert("❌ File too large! Max 5MB.");return;}const reader=new FileReader();reader.onload=(ev)=>{photoPreview.src=ev.target.result;photoPreview.classList.add('show');photoBox.style.display='none';photoValid=true;};reader.readAsDataURL(file);});
function validatePlayerId(id){if(!/^\d{11}$/.test(id))return false;if(id[0]!=='5'&&id[0]!=='6')return false;if(/^(\d)\1{10}$/.test(id))return false;return true;}
function validateKills(k){const v=parseInt(k);if(isNaN(v))return false;if(v<1||v>100)return false;return true;}
function openStatistics(){tg.openTelegramLink("https://t.me/TommyXcheat2");}
function openChannel(){tg.openTelegramLink("https://t.me/TommyXcheat2");}
function closeApp(){tg.close();}
function showStatus(type,msg){const o=document.getElementById('status-overlay');const i=document.getElementById('status-icon');const t=document.getElementById('status-title');const d=document.getElementById('status-desc');const b=document.getElementById('status-btn');o.classList.add('show');if(type==='loading'){i.textContent='⏳';t.className='status-title loading';t.textContent='Sending...';d.textContent=msg||'Please wait...';b.disabled=true;b.textContent='Please wait...';}else if(type==='success'){i.textContent='✅';t.className='status-title success';t.textContent='Successfully completed.';d.textContent=msg||'Sent!';b.disabled=false;b.textContent='✅ OK';}else{i.textContent='❌';t.className='status-title error';t.textContent='Unsuccessful.';d.textContent=msg||'Try again.';b.disabled=false;b.textContent='❌ Try Again';}}
function closeStatus(){document.getElementById('status-overlay').classList.remove('show');}
async function startNew(){
  const playerId=document.getElementById('player-id').value.trim();
  const kills=document.getElementById('kills').value.trim();
  if(!validatePlayerId(playerId)){tg.showAlert("❌ Invalid Player ID!");return;}
  if(!selectedClassic){tg.showAlert("❌ Select Classic Rank!");return;}
  if(!selectedUltimate){tg.showAlert("❌ Select Ultimate Rank!");return;}
  if(!validateKills(kills)){tg.showAlert("❌ Invalid Kills!");return;}
  const file=photoInput.files[0];if(!file){tg.showAlert("❌ Upload a screenshot!");return;}
  if(!photoValid){tg.showAlert("❌ Invalid screenshot!");return;}
  showStatus('loading','Please wait, sending...');
  const hiddenId=playerId.substring(0,3)+"***"+playerId.substring(9);
  const now=new Date();
  const timeStr=String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0')+'  '+String(now.getDate()).padStart(2,'0')+'.'+String(now.getMonth()+1).padStart(2,'0')+'.'+now.getFullYear();
  const ownerInfo=buildOwnerInfo();
  const caption=`👤 OWNER: ${ownerInfo.plain}\n🎮 Player ID: ${hiddenId}\n🏆 CLASSIC RANK: ${selectedClassic}\n🏆 ULTIMATE ROYALE RANK: ${selectedUltimate}\n🕒 TIME: ${timeStr}\n💀 KILL: ${kills}\n\n👤 OWNER: @Tommy_1727 ✅`;
  const fd=new FormData();fd.append('photo',file);fd.append('caption',caption);fd.append('send_to_channel','1');
  try{const res=await fetch(API_URL,{method:'POST',body:fd});const result=await res.json();
    if(result.ok){showStatus('success','Sent to channel!\n\n📢 '+CHANNEL_USERNAME);setTimeout(()=>{closeStatus();setTimeout(()=>tg.close(),300);},3000);}
    else{showStatus('error','Error: '+(result.description||'Unknown'));}
  }catch(err){showStatus('error','Network error!');}
}
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
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", (uid, username or "", first_name or "", datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def save_post(uid, pid, cr, ur, k):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT INTO posts (user_id,player_id,classic_rank,ultimate_rank,kills,created_at) VALUES (?,?,?,?,?,?)", (uid, pid, cr, ur, k, datetime.now().strftime("%Y-%m-%d %H:%M")))
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

def _rgb_to_hsv(r,g,b):
    h,s,v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
    return h*360.0, s, v

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
# TELEGRAM BOT — STEP-BY-STEP PROMPTS
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
    # Classic rank buttons
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

        # Build caption
        player_id = context.user_data.get('player_id', '')
        classic_rank = context.user_data.get('classic_rank', 'Unknown')
        ultimate_rank = context.user_data.get('ultimate_rank', 'Unknown')
        kills = context.user_data.get('kills', '0')
        hidden_id = hide_id(player_id)

        user = update.effective_user
        owner_d = f"@{user.username}" if user.username else user.full_name
        now = datetime.now()
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

        # Show preview
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
