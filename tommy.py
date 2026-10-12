"""
TOMMY BOT — To'liq yagona fayl (AI ishlaydi)
Bot main thread'da, Flask background'da
"""
import os, io, re, json, time, sqlite3, asyncio, logging, colorsys, threading
from io import BytesIO
from datetime import datetime
from urllib.parse import unquote

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
    print("⚠️ google-generativeai o'rnatilmagan")

# ============================================================
# SOZLAMALAR
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@TommyXcheat2")
OWNER_FIXED = "@Tommy_1727"
ADMIN_ID = 7383782449
PORT = int(os.getenv("PORT", 3000))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini AI ulandi")

PHOTO = range(1)

# ============================================================
# HTML — TO'LIQ UI
# ============================================================
INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>TOMMY BOT - Game Statistics</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh;padding:16px;padding-bottom:30px;background:#0a0820;overflow-x:hidden;position:relative}
#bg-canvas{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}
.bg-gradient{position:fixed;top:0;left:0;width:100%;height:100%;z-index:-2;background:linear-gradient(-45deg,#0a0820,#1a1145,#12162e,#0a0820);background-size:300% 300%;animation:gradientShift 30s ease infinite}
@keyframes gradientShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.container{position:relative;z-index:1;max-width:500px;margin:0 auto}
.top-row{position:fixed;top:10px;left:10px;right:10px;z-index:1000;display:flex;justify-content:space-between;align-items:flex-start;pointer-events:none}
.top-row>*{pointer-events:auto}
.fps-counter{padding:4px 9px;border-radius:10px;background:rgba(0,0,0,0.7);border:1px solid rgba(76,175,80,0.6);color:#4CAF50;font-size:10.5px;font-weight:700;font-family:monospace;display:flex;align-items:center;gap:5px;backdrop-filter:blur(8px)}
.fps-counter.low{color:#FFC107;border-color:#FFC107}
.fps-counter.bad{color:#f44336;border-color:#f44336}
.fps-counter .fps-dot{width:5px;height:5px;border-radius:50%;background:currentColor;animation:fpsBlink 1.6s infinite}
@keyframes fpsBlink{0%,100%{opacity:1}50%{opacity:0.45}}
.music-toggle{width:44px;height:44px;border-radius:50%;background:rgba(0,0,0,0.72);border:1.4px solid rgba(76,175,80,0.55);color:#4CAF50;font-size:19px;display:flex;align-items:center;justify-content:center;cursor:pointer;backdrop-filter:blur(12px)}
.music-toggle.muted{border-color:rgba(244,67,54,0.55);color:#f44336}
.header{text-align:center;padding:55px 0 30px}
.header .logo{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#4CAF50,#2196F3);display:flex;align-items:center;justify-content:center;margin:0 auto 15px;font-size:40px;box-shadow:0 8px 24px rgba(76,175,80,0.4)}
.header h1{color:#4CAF50;font-size:26px;font-weight:800;letter-spacing:1px;margin-bottom:6px}
.header p{color:#aaa;font-size:13px}
.card{background:rgba(255,255,255,0.06);border-radius:18px;padding:18px;margin-bottom:14px;border:1px solid rgba(255,255,255,0.08);backdrop-filter:blur(14px)}
.card-title{color:#4CAF50;font-size:15px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px;text-transform:uppercase;letter-spacing:0.5px}
.info-row{display:flex;justify-content:space-between;align-items:center;padding:11px 0;border-bottom:1px solid rgba(255,255,255,0.06)}
.info-row:last-child{border-bottom:none}
.info-label{color:#999;font-size:13px}
.info-value{color:#fff;font-weight:600;font-size:13px;text-align:right;max-width:60%;word-break:break-word}
.info-value.green{color:#4CAF50}
.info-link{color:#4CAF50;font-weight:700;font-size:13px;text-decoration:none;cursor:pointer;padding:4px 10px;border-radius:8px;display:inline-block}
.info-link.channel{color:#2196F3}
.info-link.owner{color:#FFC107}
.bot-name{background:linear-gradient(135deg,#FF9800,#FFC107,#FF5722);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-weight:800;font-size:14px}
.input-group{margin-bottom:12px}
.input-group input{width:100%;padding:14px 16px;background:rgba(255,255,255,0.08);border:1.5px solid rgba(255,255,255,0.15);border-radius:12px;color:#fff;font-size:15px;font-family:inherit;outline:none}
.input-group input:focus{border-color:#4CAF50;background:rgba(255,255,255,0.12)}
.input-group input::placeholder{color:#666}
.input-group input.error{border-color:#f44336;background:rgba(244,67,54,0.1)}
.input-group input.success{border-color:#4CAF50;background:rgba(76,175,80,0.1)}
.error-message{color:#f44336;font-size:12px;margin-top:4px;display:none}
.error-message.show{display:block}
.photo-upload-box{width:100%;padding:30px 20px;background:rgba(255,255,255,0.06);border:2px dashed rgba(76,175,80,0.5);border-radius:14px;text-align:center;cursor:pointer;margin-bottom:12px}
.photo-upload-box:active{background:rgba(76,175,80,0.15);border-color:#4CAF50}
.photo-upload-box.checking{border-color:#FFC107;background:rgba(255,193,7,0.08)}
.photo-upload-box .icon{font-size:42px;margin-bottom:10px;display:block}
.photo-upload-box .text{color:#4CAF50;font-size:14px;font-weight:600}
.photo-upload-box.checking .text{color:#FFC107}
.photo-upload-box .subtext{color:#888;font-size:11px;margin-top:6px}
#photo-input{display:none}
.photo-preview{display:none;width:100%;max-height:220px;object-fit:cover;border-radius:14px;margin-bottom:12px;border:2px solid #4CAF50}
.photo-preview.show{display:block}
.change-photo-btn{display:none;width:100%;padding:12px;background:rgba(255,255,255,0.1);border:1.5px solid rgba(255,255,255,0.2);border-radius:12px;color:#ccc;font-size:13px;font-weight:600;cursor:pointer;margin-bottom:12px;font-family:inherit}
.change-photo-btn.show{display:block}
.rank-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:8px}
.rank-item{background:rgba(76,175,80,0.15);border:1px solid rgba(76,175,80,0.3);border-radius:10px;padding:12px 10px;text-align:center;font-size:12px;font-weight:600;color:#4CAF50;cursor:pointer}
.rank-item.selected{background:#4CAF50;color:#fff;border-color:#4CAF50}
.rank-item.gold{background:rgba(255,193,7,0.15);border-color:rgba(255,193,7,0.3);color:#FFC107}
.rank-item.gold.selected{background:#FFC107;color:#000}
.rank-item.blue{background:rgba(33,150,243,0.15);border-color:rgba(33,150,243,0.3);color:#2196F3}
.rank-item.blue.selected{background:#2196F3;color:#fff}
.rank-item.purple{background:rgba(156,39,176,0.15);border-color:rgba(156,39,176,0.3);color:#CE93D8}
.rank-item.purple.selected{background:#9C27B0;color:#fff}
.btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:15px;border:none;border-radius:14px;font-size:15px;font-weight:700;cursor:pointer;margin-top:12px;font-family:inherit}
.btn-primary{background:linear-gradient(135deg,#4CAF50,#45a049);color:#fff}
.btn-secondary{background:linear-gradient(135deg,#2196F3,#1976D2);color:#fff}
.btn-warning{background:linear-gradient(135deg,#FF9800,#F57C00);color:#fff}
.btn-outline{background:transparent;border:1.5px solid rgba(255,255,255,0.2);color:#ccc}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700;text-transform:uppercase}
.badge-green{background:rgba(76,175,80,0.2);color:#4CAF50}
.badge-blue{background:rgba(33,150,243,0.2);color:#2196F3}
.footer{text-align:center;padding:25px 0 10px;color:#555;font-size:11px;line-height:1.6}
.footer a{color:#4CAF50;text-decoration:none}
.status-overlay{position:fixed;inset:0;z-index:99999;display:none;align-items:center;justify-content:center;padding:24px;background:rgba(5,3,18,0.75);backdrop-filter:blur(10px)}
.status-overlay.show{display:flex}
.status-box{width:100%;max-width:360px;background:linear-gradient(160deg,rgba(28,22,60,0.98),rgba(14,10,34,0.98));border-radius:22px;padding:32px 24px 24px;text-align:center;border:1.5px solid rgba(255,255,255,0.1)}
.status-icon{font-size:56px;line-height:1;margin-bottom:18px;display:inline-block}
.status-icon.spin{animation:statusSpin 1.1s linear infinite}
@keyframes statusSpin{to{transform:rotate(360deg)}}
.status-title{font-size:18px;font-weight:800;margin-bottom:8px}
.status-title.loading{color:#FFC107}
.status-title.success{color:#4CAF50}
.status-title.error{color:#f44336}
.status-desc{font-size:13px;color:#aaa;line-height:1.5;margin-bottom:20px;white-space:pre-line}
.status-bar{width:100%;height:4px;border-radius:4px;background:rgba(255,255,255,0.08);overflow:hidden;margin-bottom:20px}
.status-bar-fill{height:100%;width:40%;border-radius:4px;background:linear-gradient(90deg,#FFC107,#FF9800);animation:barSlide 1.2s ease-in-out infinite}
.status-bar-fill.success{background:linear-gradient(90deg,#4CAF50,#8BC34A);width:100%;animation:none}
.status-bar-fill.error{background:linear-gradient(90deg,#f44336,#E91E63);width:100%;animation:none}
@keyframes barSlide{0%{transform:translateX(-100%)}100%{transform:translateX(350%)}}
.status-btn{width:100%;padding:14px;border:none;border-radius:14px;font-size:14px;font-weight:700;font-family:inherit;cursor:pointer}
.status-btn.loading{background:rgba(255,255,255,0.08);color:#888;cursor:not-allowed}
.status-btn.success{background:linear-gradient(135deg,#4CAF50,#45a049);color:#fff}
.status-btn.error{background:linear-gradient(135deg,#f44336,#c62828);color:#fff}
</style>
</head>
<body>
<div class="bg-gradient"></div>
<canvas id="bg-canvas"></canvas>
<div class="top-row">
  <div class="fps-counter" id="fps-counter"><span class="fps-dot"></span><span id="fps-value">60</span><span style="opacity:0.65">FPS</span></div>
  <div class="music-toggle" id="music-toggle" onclick="toggleMusic()"><span id="music-icon">🔊</span></div>
</div>
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
    <div class="info-row"><span class="info-label">Status:</span><span class="info-value"><span class="badge badge-green">✅ ACTIVE</span></span></div>
  </div>
  <div class="card">
    <div class="card-title">🆔 PUBG Mobile ID</div>
    <div class="input-group">
      <input type="tel" id="player-id" placeholder="Enter your 11-digit ID" maxlength="11" inputmode="numeric">
      <div class="error-message" id="id-error">ID must be 11 digits, start with 5 or 6.</div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📸 Screenshot</div>
    <div class="photo-upload-box" id="photo-box">
      <span class="icon">📤</span>
      <div class="text">Tap to upload screenshot</div>
      <div class="subtext">JPG, PNG • Max 5MB • PUBG Mobile only</div>
    </div>
    <input type="file" id="photo-input" accept="image/*">
    <img id="photo-preview" class="photo-preview" alt="Preview">
    <button class="change-photo-btn" id="change-photo-btn" onclick="resetPhoto()">🔄 Change Photo</button>
  </div>
  <div class="card">
    <div class="card-title">👑 CLASSIC RANKS</div>
    <div class="rank-grid" id="classic-ranks">
      <div class="rank-item" data-rank="Bronze">Bronze</div>
      <div class="rank-item" data-rank="Silver">Silver</div>
      <div class="rank-item" data-rank="Gold">Gold</div>
      <div class="rank-item" data-rank="Platinum">Platinum</div>
      <div class="rank-item blue" data-rank="Diamond">Diamond</div>
      <div class="rank-item blue" data-rank="Crown">Crown</div>
      <div class="rank-item gold" data-rank="Ace">Ace</div>
      <div class="rank-item gold" data-rank="Ace Master">Ace Master</div>
      <div class="rank-item purple" data-rank="Ace Dominator">Ace Dominator</div>
      <div class="rank-item purple" data-rank="Conqueror">Conqueror</div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">👑 Ultimate Royale</div>
    <div class="rank-grid" id="ultimate-ranks">
      <div class="rank-item" data-rank="Vanguard">Vanguard</div>
      <div class="rank-item" data-rank="Exceed">Exceed</div>
      <div class="rank-item blue" data-rank="Supreme">Supreme</div>
      <div class="rank-item blue" data-rank="Peerless">Peerless</div>
      <div class="rank-item purple" data-rank="Legend">Legend</div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">💀 Kills in 1 Match</div>
    <div class="input-group">
      <input type="tel" id="kills" placeholder="Enter kills (1-100)" maxlength="3" inputmode="numeric">
      <div class="error-message" id="kills-error">Kills must be between 1 and 100.</div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">👤 FOR INQUIRIES</div>
    <div class="info-row"><span class="info-label">Bot name:</span><span class="info-value"><span class="bot-name">TOMMY BOT</span></span></div>
    <div class="info-row"><span class="info-label">Channel:</span><span class="info-value"><a class="info-link channel" onclick="openChannel()">@TommyXcheat2</a></span></div>
    <div class="info-row"><span class="info-label">Owner:</span><span class="info-value"><a class="info-link owner" onclick="openOwner()">@Tommy_1727</a></span></div>
    <div class="info-row"><span class="info-label">Version:</span><span class="info-value"><span class="badge badge-blue">v4.0</span></span></div>
  </div>
  <button class="btn btn-primary" onclick="openStatistics()">📊 STATISTICS</button>
  <button class="btn btn-secondary" onclick="startNew()">📤 START NEW</button>
  <button class="btn btn-warning" onclick="openChannel()">📢 Go to Channel</button>
  <button class="btn btn-outline" onclick="closeApp()">❌ Close</button>
  <div class="footer">© 2026 <a href="https://t.me/Tommy_1727">@Tommy_1727</a><br>All rights reserved.</div>
</div>
<div class="status-overlay" id="status-overlay">
  <div class="status-box">
    <div class="status-icon" id="status-icon">⏳</div>
    <div class="status-title" id="status-title">Sending...</div>
    <div class="status-desc" id="status-desc">Please wait...</div>
    <div class="status-bar"><div class="status-bar-fill" id="status-bar-fill"></div></div>
    <button class="status-btn loading" id="status-btn" onclick="closeStatus()">Please wait...</button>
  </div>
</div>
<script>
const tg = window.Telegram.WebApp;
tg.expand(); tg.ready();
tg.setHeaderColor('#0a0820'); tg.setBackgroundColor('#0a0820');
const API_URL = "/send-feedback";
const CHANNEL_USERNAME = "@TommyXcheat2";
const statusOverlay = document.getElementById('status-overlay');
const statusIcon = document.getElementById('status-icon');
const statusTitle = document.getElementById('status-title');
const statusDesc = document.getElementById('status-desc');
const statusBarFill = document.getElementById('status-bar-fill');
const statusBtn = document.getElementById('status-btn');
function showStatus(type, message) {
  statusOverlay.classList.add('show');
  statusIcon.classList.remove('spin');
  statusTitle.classList.remove('loading','success','error');
  statusBarFill.classList.remove('success','error');
  statusBtn.classList.remove('loading','success','error');
  if (type === 'loading') {
    statusIcon.textContent = '⏳'; statusIcon.classList.add('spin');
    statusTitle.classList.add('loading'); statusTitle.textContent = 'Sending...';
    statusDesc.textContent = message || 'Please wait...';
    statusBarFill.classList.add('loading'); statusBarFill.style.width = '40%';
    statusBtn.classList.add('loading'); statusBtn.textContent = 'Please wait...'; statusBtn.disabled = true;
  } else if (type === 'success') {
    statusIcon.textContent = '✅'; statusTitle.classList.add('success');
    statusTitle.textContent = 'Successfully completed.';
    statusDesc.textContent = message || 'Sent to channel!';
    statusBarFill.classList.add('success'); statusBarFill.style.width = '100%';
    statusBtn.classList.add('success'); statusBtn.textContent = '✅ OK'; statusBtn.disabled = false;
  } else {
    statusIcon.textContent = '❌'; statusTitle.classList.add('error');
    statusTitle.textContent = 'Unsuccessful.';
    statusDesc.textContent = message || 'Try again.';
    statusBarFill.classList.add('error'); statusBarFill.style.width = '100%';
    statusBtn.classList.add('error'); statusBtn.textContent = '❌ Try Again'; statusBtn.disabled = false;
  }
}
function closeStatus() { statusOverlay.classList.remove('show'); }
const fpsCounterEl = document.getElementById('fps-counter');
const fpsValueEl = document.getElementById('fps-value');
let fpsFrames = 0, fpsLastTime = performance.now();
function updateFPS() {
  fpsFrames++;
  const now = performance.now();
  const elapsed = now - fpsLastTime;
  if (elapsed >= 500) {
    const fps = Math.round((fpsFrames*1000)/elapsed);
    fpsValueEl.textContent = fps; fpsFrames = 0; fpsLastTime = now;
    fpsCounterEl.classList.remove('low','bad');
    if (fps < 40) fpsCounterEl.classList.add('bad');
    else if (fps < 55) fpsCounterEl.classList.add('low');
  }
}
const canvas = document.getElementById('bg-canvas');
const ctx = canvas.getContext('2d');
let W = 0, H = 0, particles = [], ripples = [];
function resizeCanvas() {
  const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
  W = window.innerWidth; H = window.innerHeight;
  canvas.width = Math.floor(W*dpr); canvas.height = Math.floor(H*dpr);
  canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
function newParticle() {
  return { x: Math.random()*W, y: Math.random()*H, r: Math.random()*1.4+0.6,
    vx: (Math.random()-0.5)*0.28, vy: (Math.random()-0.5)*0.28,
    hue: [140,210,280][Math.floor(Math.random()*3)], a: Math.random()*0.45+0.3 };
}
resizeCanvas();
for (let i = 0; i < 25; i++) particles.push(newParticle());
window.addEventListener('resize', () => {
  resizeCanvas();
  for (const p of particles) { if (p.x > W) p.x = Math.random()*W; if (p.y > H) p.y = Math.random()*H; }
});
document.addEventListener('pointerdown', (e) => {
  ripples.push({x:e.clientX, y:e.clientY, life:0, maxR:100, maxLife:0.8});
  if (ripples.length > 4) ripples.shift();
}, {passive:true});
function drawBg() {
  ctx.clearRect(0, 0, W, H);
  for (let i = 0; i < particles.length; i++) {
    const pi = particles[i];
    for (let j = i+1; j < particles.length; j++) {
      const pj = particles[j];
      const dx = pi.x-pj.x, dy = pi.y-pj.y, d2 = dx*dx+dy*dy;
      if (d2 < 16900) {
        const alpha = (1 - Math.sqrt(d2)/130)*0.13;
        ctx.beginPath(); ctx.strokeStyle = `hsla(160,70%,55%,${alpha})`;
        ctx.lineWidth = 0.55; ctx.moveTo(pi.x,pi.y); ctx.lineTo(pj.x,pj.y); ctx.stroke();
      }
    }
  }
  for (const p of particles) {
    p.x += p.vx; p.y += p.vy;
    if (p.x < 0 || p.x > W) p.vx = -p.vx;
    if (p.y < 0 || p.y > H) p.vy = -p.vy;
    ctx.beginPath(); ctx.fillStyle = `hsla(${p.hue},80%,68%,${p.a})`;
    ctx.arc(p.x, p.y, p.r*3, 0, Math.PI*2); ctx.fill();
  }
  for (let i = ripples.length-1; i >= 0; i--) {
    const rp = ripples[i]; rp.life += 1/60;
    const t = rp.life/rp.maxLife;
    if (t >= 1) { ripples.splice(i,1); continue; }
    ctx.beginPath(); ctx.strokeStyle = `hsla(140,90%,65%,${(1-t)*0.5})`;
    ctx.lineWidth = 1.5*(1-t)+0.4;
    ctx.arc(rp.x, rp.y, rp.maxR*t, 0, Math.PI*2); ctx.stroke();
  }
}
let lastFT = 0;
function loop(now) {
  requestAnimationFrame(loop);
  if (now - lastFT < 16) return;
  lastFT = now;
  updateFPS(); drawBg();
}
requestAnimationFrame(loop);
let userMuted = false;
function toggleMusic() {
  userMuted = !userMuted;
  const btn = document.getElementById('music-toggle');
  const icon = document.getElementById('music-icon');
  if (userMuted) { btn.classList.add('muted'); icon.textContent = '🔇'; }
  else { btn.classList.remove('muted'); icon.textContent = '🔊'; }
}
const user = tg.initDataUnsafe.user;
if (user) {
  const fullName = ((user.first_name||'')+' '+(user.last_name||'')).trim();
  document.getElementById('user-name').innerText = fullName || `User #${user.id}`;
  document.getElementById('user-username').innerText = user.username ? '@'+user.username : '—';
  document.getElementById('user-id').innerText = user.id;
} else document.getElementById('user-name').innerText = 'Unknown';
function buildOwnerInfo() {
  if (!user) return {plain:'Unknown'};
  if (user.username) return {plain:'@'+user.username};
  const fn = ((user.first_name||'')+' '+(user.last_name||'')).trim();
  if (fn) return {plain:`${fn} (ID: ${user.id})`};
  return {plain:`User #${user.id}`};
}
let selectedClassic = null, selectedUltimate = null;
document.querySelectorAll('#classic-ranks .rank-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('#classic-ranks .rank-item').forEach(i => i.classList.remove('selected'));
    item.classList.add('selected'); selectedClassic = item.dataset.rank;
  });
});
document.querySelectorAll('#ultimate-ranks .rank-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('#ultimate-ranks .rank-item').forEach(i => i.classList.remove('selected'));
    item.classList.add('selected'); selectedUltimate = item.dataset.rank;
  });
});
const photoBox = document.getElementById('photo-box');
const photoInput = document.getElementById('photo-input');
const photoPreview = document.getElementById('photo-preview');
const changePhotoBtn = document.getElementById('change-photo-btn');
let photoValid = false;
photoBox.addEventListener('click', () => { if (!photoBox.classList.contains('checking')) photoInput.click(); });
async function validatePubgScreenshot(file) {
  if (!file.type || !file.type.startsWith('image/')) return {ok:false, reason:'Only image files.'};
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      const w = img.naturalWidth, h = img.naturalHeight;
      if (w < 640 || h < 360) return resolve({ok:false, reason:'Resolution too low.'});
      if (w <= h) return resolve({ok:false, reason:'Landscape only.'});
      const ratio = w/h;
      const allowed = [1.333,1.5,1.6,1.667,1.778,2.0,2.056,2.111,2.167,2.222,2.333,2.444];
      if (!allowed.some(r => Math.abs(ratio-r) <= 0.06)) return resolve({ok:false, reason:'Wrong screen ratio.'});
      resolve({ok:true});
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve({ok:false, reason:'Cannot read image.'}); };
    img.src = url;
  });
}
function setPhotoBoxState(s) {
  const icon = photoBox.querySelector('.icon');
  const text = photoBox.querySelector('.text');
  const sub = photoBox.querySelector('.subtext');
  if (s === 'checking') {
    photoBox.style.display = 'block'; photoBox.classList.add('checking');
    photoPreview.classList.remove('show'); changePhotoBtn.classList.remove('show');
    icon.textContent = '⏳'; text.textContent = 'Checking...'; sub.textContent = 'Verifying PUBG Mobile screenshot';
  } else {
    photoBox.classList.remove('checking');
    icon.textContent = '📤'; text.textContent = 'Tap to upload screenshot';
    sub.textContent = 'JPG, PNG • Max 5MB • PUBG Mobile only';
  }
}
photoInput.addEventListener('change', async function(e) {
  const file = e.target.files[0]; if (!file) return;
  if (file.size > 5*1024*1024) { tg.showAlert("❌ File too large! Max 5MB."); resetPhoto(); return; }
  setPhotoBoxState('checking');
  const result = await validatePubgScreenshot(file);
  if (!result.ok) {
    setPhotoBoxState('idle'); photoInput.value = ''; photoValid = false;
    tg.showAlert("❌ INVALID SCREENSHOT\n\n" + result.reason); return;
  }
  const reader = new FileReader();
  reader.onload = (ev) => {
    photoPreview.src = ev.target.result; photoPreview.classList.add('show');
    photoBox.style.display = 'none'; photoBox.classList.remove('checking');
    changePhotoBtn.classList.add('show'); photoValid = true;
  };
  reader.readAsDataURL(file);
});
function resetPhoto() {
  photoInput.value = ''; photoPreview.src = ''; photoPreview.classList.remove('show');
  photoBox.style.display = 'block'; changePhotoBtn.classList.remove('show');
  photoValid = false; setPhotoBoxState('idle');
}
function validatePlayerId(id) {
  if (!/^\d{11}$/.test(id)) return false;
  if (id[0] !== '5' && id[0] !== '6') return false;
  if (/^(\d)\1{10}$/.test(id)) return false;
  return true;
}
const playerIdInput = document.getElementById('player-id');
const idError = document.getElementById('id-error');
playerIdInput.addEventListener('input', function() {
  const id = this.value.trim();
  playerIdInput.classList.remove('error','success');
  idError.classList.remove('show');
  if (id.length === 11) {
    if (validatePlayerId(id)) playerIdInput.classList.add('success');
    else { playerIdInput.classList.add('error'); idError.classList.add('show'); }
  }
});
const killsInput = document.getElementById('kills');
const killsError = document.getElementById('kills-error');
killsInput.addEventListener('input', function() {
  this.value = this.value.replace(/[^0-9]/g,'');
  if (this.value.startsWith('0') && this.value.length > 1) this.value = this.value.replace(/^0+/,'');
  const val = parseInt(this.value);
  killsInput.classList.remove('error','success');
  killsError.classList.remove('show');
  if (this.value !== '') {
    if (isNaN(val) || val < 1 || val > 100) { killsInput.classList.add('error'); killsError.classList.add('show'); }
    else killsInput.classList.add('success');
  }
});
function validateKills(k) {
  const v = parseInt(k); if (isNaN(v)) return false;
  if (v < 1 || v > 100) return false; return true;
}
function openStatistics() { tg.openTelegramLink("https://t.me/TommyXcheat2"); }
function openChannel() { tg.openTelegramLink("https://t.me/TommyXcheat2"); }
function openOwner() { tg.openTelegramLink("https://t.me/Tommy_1727"); }
function closeApp() { tg.close(); }
async function startNew() {
  const playerId = document.getElementById('player-id').value.trim();
  const kills = document.getElementById('kills').value.trim();
  if (!validatePlayerId(playerId)) { tg.showAlert("❌ Invalid Player ID!"); return; }
  if (!selectedClassic) { tg.showAlert("❌ Select Classic Rank!"); return; }
  if (!selectedUltimate) { tg.showAlert("❌ Select Ultimate Rank!"); return; }
  if (!validateKills(kills)) { tg.showAlert("❌ Invalid Kills!"); return; }
  const file = photoInput.files[0];
  if (!file) { tg.showAlert("❌ Upload a screenshot!"); return; }
  if (!photoValid) { tg.showAlert("❌ Invalid screenshot!"); return; }
  showStatus('loading', 'Please wait, sending to channel.');
  const hiddenId = playerId.substring(0,3) + "***" + playerId.substring(9);
  const now = new Date();
  const hh = String(now.getHours()).padStart(2,'0');
  const mm = String(now.getMinutes()).padStart(2,'0');
  const dd = String(now.getDate()).padStart(2,'0');
  const mo = String(now.getMonth()+1).padStart(2,'0');
  const yy = now.getFullYear();
  const timeStr = `${hh}:${mm}  ${dd}.${mo}.${yy}`;
  const ownerInfo = buildOwnerInfo();
  const caption = `👤 OWNER: ${ownerInfo.plain}\n🎮 Player ID: ${hiddenId}\n🏆 CLASSIC RANK: ${selectedClassic}\n🏆 ULTIMATE ROYALE RANK: ${selectedUltimate}\n🕒 TIME: ${timeStr}\n💀 KILL: ${kills}\n\n👤 OWNER: @Tommy_1727 ✅`;
  const fd = new FormData();
  fd.append('photo', file);
  fd.append('caption', caption);
  try {
    const res = await fetch(API_URL, {method:'POST', body: fd});
    const result = await res.json();
    if (result.ok) {
      showStatus('success', 'Sent to channel successfully!\n\n📢 ' + CHANNEL_USERNAME);
      setTimeout(() => { closeStatus(); setTimeout(() => tg.close(), 300); }, 3000);
    } else {
      showStatus('error', 'Telegram error:\n' + (result.description || 'Unknown'));
    }
  } catch (err) {
    showStatus('error', 'Network error!');
  }
}
</script>
</body>
</html>'''

# ============================================================
# SQLITE
# ============================================================
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, player_id TEXT,
        classic_rank TEXT, ultimate_rank TEXT, kills TEXT, created_at TEXT)""")
    conn.commit(); conn.close()

def save_user(uid, username, first_name):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)",
        (uid, username or "", first_name or "", datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def save_post(uid, pid, cr, ur, k):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT INTO posts (user_id,player_id,classic_rank,ultimate_rank,kills,created_at) VALUES (?,?,?,?,?,?)",
        (uid, pid, cr, ur, k, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

# ============================================================
# YORDAMCHI
# ============================================================
def hide_id(pid):
    p = str(pid).strip()
    if len(p) <= 6: return p
    return p[:3] + "***" + p[-2:]

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
    CW = 240; CH = max(1, int(round(h*(CW/w))))
    small = img.convert("RGB").resize((CW, CH))
    pixels = list(small.getdata()); total = len(pixels)
    white = black = vivid = 0
    green = earth = sky = gray = 0
    for (r,g,b) in pixels:
        hue, sat, val = _rgb_to_hsv(r,g,b)
        if val > 0.86 and sat < 0.12: white += 1
        if val < 0.10: black += 1
        if sat > 0.72 and val > 0.62: vivid += 1
        if sat < 0.16 and 0.15 < val < 0.87: gray += 1
        elif 65 <= hue <= 165 and sat >= 0.16 and val > 0.12: green += 1
        elif 8 <= hue < 60 and sat >= 0.18 and val > 0.12: earth += 1
        elif 175 <= hue <= 260 and sat >= 0.08 and val > 0.35: sky += 1
    whiteR = white/total; blackR = black/total; vividR = vivid/total
    gameR = (green+earth+sky+gray*0.8)/total
    logger.info(f"📊 white={whiteR:.2f} black={blackR:.2f} vivid={vividR:.2f} game={gameR:.2f}")
    if whiteR > 0.55: return False, "Looks like document/chat."
    if vividR > 0.32: return False, "Too colorful."
    if blackR > 0.62: return False, "Too dark."
    if gameR < 0.45: return False, "Not a PUBG screenshot."
    return True, ""

# ============================================================
# 🤖 AI — Gemini rasm tahlili
# ============================================================
def analyze_with_ai(image_bytes):
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        logger.warning("⚠️ AI sozlanmagan")
        return None
    try:
        img = Image.open(BytesIO(image_bytes))
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """You are a PUBG Mobile screenshot analyzer. Analyze this screenshot and extract information. Return ONLY a valid JSON object.

{
  "player_id": "11-digit UID (look in top-left corner, format 'UID:XXXXXXXXXXX') or null",
  "classic_rank": "Bronze/Silver/Gold/Platinum/Diamond/Crown/Ace/Ace Master/Ace Dominator/Conqueror or null",
  "ultimate_rank": "Vanguard/Exceed/Supreme/Peerless/Legend or null",
  "kills": "number of kills in match result or null"
}

Rules:
- player_id: exactly 11 digits starting with 5 or 6
- classic_rank: look at rank badges and text
- ultimate_rank: look at Ultimate Royale section
- kills: number next to skull icon
- If not visible, use null
- Return ONLY JSON, no markdown"""
        response = model.generate_content([prompt, img])
        text = response.text.strip().replace('```json','').replace('```','').strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if not m:
            logger.error(f"❌ JSON topilmadi: {text[:200]}")
            return None
        data = json.loads(m.group())
        logger.info(f"✅ AI natijasi: {data}")
        return data
    except Exception as e:
        logger.error(f"❌ AI xatosi: {e}")
        return None

# ============================================================
# TELEGRAM GA YUBORISH
# ============================================================
def send_to_telegram(image_bytes, caption, mime_type='image/jpeg'):
    try:
        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {'photo': ('screenshot.jpg', image_bytes, mime_type)}
        data = {'chat_id': CHANNEL_ID, 'caption': caption}
        r = requests.post(url, files=files, data=data, timeout=30)
        return r.json()
    except Exception as e:
        return {'ok': False, 'description': str(e)}

# ============================================================
# FLASK WEB SERVER
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
            return jsonify({'ok': False, 'description': 'Photo kerak!'}), 400
        photo = request.files['photo']
        if photo.filename == '':
            return jsonify({'ok': False, 'description': 'No file'}), 400
        photo_bytes = photo.read()
        if len(photo_bytes) > 5*1024*1024:
            return jsonify({'ok': False, 'description': 'Too large'}), 400
        frontend_caption = request.form.get('caption', '')
        owner_name = "Unknown"
        if frontend_caption:
            first_line = frontend_caption.split('\n')[0]
            owner_name = first_line.replace('👤 OWNER: ', '').strip() or "Unknown"
        logger.info(f"📸 Rasm qabul qilindi. Owner: {owner_name}")
        ai_data = analyze_with_ai(photo_bytes)
        if ai_data:
            player_id = ai_data.get('player_id') or ''
            classic_rank = ai_data.get('classic_rank') or 'Unknown'
            ultimate_rank = ai_data.get('ultimate_rank') or 'Unknown'
            kills = ai_data.get('kills') or '0'
            hidden_id = 'Unknown'
            if player_id and str(player_id).strip().isdigit() and len(str(player_id).strip()) == 11:
                pid = str(player_id).strip()
                hidden_id = pid[:3] + '***' + pid[-2:]
            elif player_id:
                hidden_id = str(player_id).strip()
            now = datetime.now()
            time_str = now.strftime('%H:%M  %d.%m.%Y')
            final_caption = (
                f"👤 OWNER: {owner_name}\n"
                f"🎮 Player ID: {hidden_id}\n"
                f"🏆 CLASSIC RANK: {classic_rank}\n"
                f"🏆 ULTIMATE ROYALE RANK: {ultimate_rank}\n"
                f"🕒 TIME: {time_str}\n"
                f"💀 KILL: {kills}\n"
                f"\n"
                f"👤 OWNER: @Tommy_1727 ✅"
            )
            logger.info(f"✅ AI caption yasaldi")
        else:
            logger.warning("⚠️ AI ishlamadi, frontend captioni ishlatiladi")
            final_caption = frontend_caption
        tg_res = send_to_telegram(photo_bytes, final_caption, photo.mimetype or 'image/jpeg')
        return jsonify({
            'ok': tg_res.get('ok', False),
            'description': tg_res.get('description'),
            'ai_data': ai_data,
            'final_caption': final_caption
        }), 200 if tg_res.get('ok') else 500
    except Exception as e:
        logger.error(f"❌ Web xatosi: {e}")
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
        "🤖 TOMMY BOT — AI POWERED\n\n"
        "📸 Faqat PUBG Mobile skrinshotini yuboring.\n"
        "AI hamma narsani o'zi aniqlaydi!",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def rank_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.message.reply_text("📸 PUBG Mobile skrinshotini yuboring:")
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    msg = await update.message.reply_text("⏳ Tekshirilmoqda...\n\n1️⃣ Validatsiya\n2️⃣ AI tahlil")
    try:
        f = await context.bot.get_file(photo.file_id)
        fb = bytes(await f.download_as_bytearray())
        ok, reason = validate_pubg_screenshot(fb)
        if not ok:
            await msg.delete()
            await update.message.reply_text(f"❌ {reason}\n\nQaytadan yuboring:")
            return PHOTO
        await msg.edit_text("🤖 AI tahlil qilmoqda...")
        ai_data = analyze_with_ai(fb)
        user = update.effective_user
        owner_d = f"@{user.username}" if user.username else user.full_name
        if ai_data:
            player_id = ai_data.get('player_id') or ''
            classic_rank = ai_data.get('classic_rank') or 'Unknown'
            ultimate_rank = ai_data.get('ultimate_rank') or 'Unknown'
            kills = ai_data.get('kills') or '0'
            hidden_id = 'Unknown'
            if player_id and str(player_id).strip().isdigit() and len(str(player_id).strip()) == 11:
                pid = str(player_id).strip()
                hidden_id = pid[:3] + '***' + pid[-2:]
            elif player_id:
                hidden_id = str(player_id).strip()
        else:
            hidden_id = 'Unknown'
            classic_rank = 'Unknown'
            ultimate_rank = 'Unknown'
            kills = '0'
        now = datetime.now()
        time_str = now.strftime('%H:%M  %d.%m.%Y')
        cap = (
            f"👤 OWNER: {owner_d}\n"
            f"🎮 Player ID: {hidden_id}\n"
            f"🏆 CLASSIC RANK: {classic_rank}\n"
            f"🏆 ULTIMATE ROYALE RANK: {ultimate_rank}\n"
            f"🕒 TIME: {time_str}\n"
            f"💀 KILL: {kills}\n\n"
            f"👤 OWNER: {OWNER_FIXED} ✅"
        )
        await msg.delete()
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo.file_id, caption=cap)
        await update.message.reply_text("✅ Yuborildi!")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Photo: {e}")
        await update.message.reply_text(f"❌ {e}")
        return PHOTO

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.message.reply_text("Contact: @Tommy_1727")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# ============================================================
# MAIN — Bot main thread'da, Flask background'da
# ============================================================
def main():
    init_db()

    # Flask server'ni BACKGROUND THREAD'da ishga tushirish
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"🌐 Flask server: port {PORT}")

    # Bot'ni MAIN THREAD'da ishga tushirish
    logger.info("🤖 Bot ishga tushirilmoqda...")
    req = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0
    )
    application = Application.builder().token(BOT_TOKEN).request(req).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(rank_start, pattern="^rank_start$")],
        states={PHOTO: [MessageHandler(filters.PHOTO, handle_photo)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv)
    application.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))

    logger.info("✅ Bot ishga tushdi (main thread)")
    logger.info(f"🔑 BOT_TOKEN: {'✅ bor' if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ yo\'q'}")

    application.run_polling(
        stop_signals=None,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
