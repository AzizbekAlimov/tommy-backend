"""
TOMMY BOT — Complete with Command Menu + AI Analysis + Modern WebApp v3.5
"""
import os, sqlite3, asyncio, logging, threading, base64, json
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@TommyXcheat2")
OWNER_FIXED = "@Tommy_1727"
ADMIN_ID = int(os.getenv("ADMIN_ID", "7383782449"))
PORT = int(os.getenv("PORT", 10000))

TZ_TASHKENT = timezone(timedelta(hours=5))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if GEMINI_API_KEY:
    logger.info("✅ Gemini API key loaded")
else:
    logger.warning("⚠️ GEMINI_API_KEY yo'q — AI tahlil o'chirilgan")

PHOTO, PLAYER_ID, CLASSIC, ULTIMATE, KILLS = range(5)

# ============================================================
# COMMAND LISTS
# ============================================================
PRIVATE_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("cancel", "Cancel operation"),
    BotCommand("admin", "Bot statistics"),
    BotCommand("stats", "Bot statistics"),
    BotCommand("users", "Users list"),
    BotCommand("broadcast", "Broadcast message"),
    BotCommand("ban", "Ban user"),
    BotCommand("unban", "Unban user"),
    BotCommand("banned", "Banned users list"),
]

GROUP_ADMIN_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("setup", "Setup command menu"),
    BotCommand("mute", "Mute user (reply)"),
    BotCommand("unmute", "Unmute user (reply)"),
    BotCommand("clear", "Clear recent messages"),
]

GROUP_PUBLIC_COMMANDS = [
    BotCommand("start", "Start the bot"),
]

# ============================================================
# HTML (WebApp v3.5 - Modern)
# ============================================================
INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>TOMMY BOT - Game Statistics v2</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        html, body { height: 100%; overflow-x: hidden; }
        body {
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            padding: 16px;
            padding-bottom: 30px;
            position: relative;
            background: #0a0820;
            overflow-x: hidden;
        }
        #bg-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none; }
        .bg-gradient {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -2;
            background: linear-gradient(-45deg, #0a0820, #1a1145, #12162e, #0a0820);
            background-size: 300% 300%;
            animation: gradientShift 30s ease infinite;
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .aurora {
            position: fixed; width: 100%; height: 50vh; left: 0;
            filter: blur(60px); opacity: 0.22; pointer-events: none; z-index: -1;
        }
        .aurora.a1 {
            top: -5vh;
            background: radial-gradient(circle at 30% 50%, #4CAF50 0%, transparent 55%);
            animation: auroraMove1 26s ease-in-out infinite;
        }
        .aurora.a2 {
            bottom: -5vh;
            background: radial-gradient(circle at 70% 50%, #2196F3 0%, transparent 55%);
            animation: auroraMove2 32s ease-in-out infinite;
        }
        @keyframes auroraMove1 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(6%,4%) scale(1.08); } }
        @keyframes auroraMove2 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-6%,-4%) scale(1.08); } }
        .container { position: relative; z-index: 1; max-width: 500px; margin: 0 auto; }
        .top-row {
            position: fixed; top: 10px; left: 10px; right: 10px; z-index: 1000;
            display: flex; justify-content: space-between; align-items: flex-start;
            pointer-events: none;
        }
        .top-row > * { pointer-events: auto; }
        .fps-counter {
            padding: 4px 9px; border-radius: 10px;
            background: rgba(0, 0, 0, 0.7);
            border: 1px solid rgba(76, 175, 80, 0.6);
            color: #4CAF50; font-size: 10.5px; font-weight: 700;
            font-family: 'SF Mono', Menlo, Consolas, monospace;
            letter-spacing: 0.4px; user-select: none; pointer-events: none;
            display: flex; align-items: center; gap: 5px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
        }
        .fps-counter.low { color: #FFC107; border-color: #FFC107; }
        .fps-counter.bad { color: #f44336; border-color: #f44336; }
        .fps-counter .fps-dot {
            width: 5px; height: 5px; border-radius: 50%;
            background: currentColor; box-shadow: 0 0 5px currentColor;
            flex-shrink: 0; animation: fpsBlink 1.6s ease-in-out infinite;
        }
        @keyframes fpsBlink { 0%,100% { opacity: 1; } 50% { opacity: 0.45; } }
        .music-toggle {
            width: 44px; height: 44px; border-radius: 50%;
            background: rgba(0, 0, 0, 0.72);
            border: 1.4px solid rgba(76, 175, 80, 0.55);
            color: #4CAF50; font-size: 19px;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; transition: all 0.2s ease; position: relative;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
            user-select: none;
        }
        .music-toggle:active { transform: scale(0.9); }
        .music-toggle.muted {
            border-color: rgba(244, 67, 54, 0.55); color: #f44336;
            box-shadow: 0 4px 18px rgba(244, 67, 54, 0.25);
        }
        .music-toggle .pulse {
            position: absolute; inset: -3px; border-radius: 50%;
            border: 1.4px solid rgba(76, 175, 80, 0.55);
            opacity: 0; pointer-events: none;
        }
        .music-toggle:not(.muted) .pulse { animation: soundPulse 2.2s ease-out infinite; }
        @keyframes soundPulse { 0% { transform: scale(1); opacity: 0.65; } 100% { transform: scale(1.55); opacity: 0; } }
        .header { text-align: center; padding: 55px 0 30px; }
        .header .logo-wrapper {
            position: relative;
            width: 180px;
            height: 180px;
            margin: 0 auto 15px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .header .logo {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4CAF50, #2196F3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 45px;
            box-shadow: 0 8px 24px rgba(76, 175, 80, 0.4);
            animation: logoPulse 3s ease-in-out infinite;
            position: relative;
            z-index: 2;
        }
        @keyframes logoPulse {
            0%, 100% {
                box-shadow: 0 8px 24px rgba(76, 175, 80, 0.4), 0 0 0 0 rgba(76, 175, 80, 0.6);
                transform: scale(1);
            }
            50% {
                box-shadow: 0 8px 50px rgba(76, 175, 80, 0.9), 0 0 60px 20px rgba(76, 175, 80, 0.3);
                transform: scale(1.08);
            }
        }
        .header .ring {
            position: absolute;
            border-radius: 50%;
            border: 4px solid transparent;
            pointer-events: none;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        .header .ring-1 {
            width: 110px;
            height: 110px;
            border-top-color: #4CAF50;
            border-right-color: #4CAF50;
            animation: spin1 2.5s linear infinite;
            filter: drop-shadow(0 0 10px #4CAF50) drop-shadow(0 0 20px #4CAF50);
        }
        .header .ring-2 {
            width: 140px;
            height: 140px;
            border-bottom-color: #2196F3;
            border-left-color: #2196F3;
            animation: spin2 3.5s linear infinite reverse;
            filter: drop-shadow(0 0 10px #2196F3) drop-shadow(0 0 20px #2196F3);
        }
        .header .ring-3 {
            width: 170px;
            height: 170px;
            border-top-color: #FFC107;
            border-left-color: #FFC107;
            opacity: 0.85;
            animation: spin3 5s linear infinite;
            filter: drop-shadow(0 0 10px #FFC107) drop-shadow(0 0 20px #FFC107);
        }
        @keyframes spin1 {
            from { transform: translate(-50%, -50%) rotate(0deg); }
            to   { transform: translate(-50%, -50%) rotate(360deg); }
        }
        @keyframes spin2 {
            from { transform: translate(-50%, -50%) rotate(0deg); }
            to   { transform: translate(-50%, -50%) rotate(-360deg); }
        }
        @keyframes spin3 {
            from { transform: translate(-50%, -50%) rotate(0deg); }
            to   { transform: translate(-50%, -50%) rotate(360deg); }
        }
        .header h1 { color: #4CAF50; font-size: 26px; font-weight: 800; letter-spacing: 1px; margin-bottom: 6px; text-shadow: 0 0 20px rgba(76, 175, 80, 0.5); }
        .header p { color: #aaa; font-size: 13px; }
        .card {
            background: rgba(255, 255, 255, 0.06);
            border-radius: 18px; padding: 18px; margin-bottom: 14px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
        }
        .card-title {
            color: #4CAF50; font-size: 15px; font-weight: 700;
            margin-bottom: 14px; display: flex; align-items: center; gap: 8px;
            text-transform: uppercase; letter-spacing: 0.5px;
        }
        .info-row {
            display: flex; justify-content: space-between; align-items: center;
            padding: 11px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .info-row:last-child { border-bottom: none; }
        .info-label { color: #999; font-size: 13px; }
        .info-value { color: #fff; font-weight: 600; font-size: 13px; text-align: right; max-width: 60%; word-break: break-word; }
        .info-value.green { color: #4CAF50; }
        .info-link {
            color: #4CAF50; font-weight: 700; font-size: 13px;
            text-decoration: none; cursor: pointer; padding: 4px 10px;
            border-radius: 8px; display: inline-block;
        }
        .info-link:active { transform: scale(0.95); background: rgba(76, 175, 80, 0.15); }
        .info-link.channel { color: #2196F3; }
        .info-link.owner   { color: #FFC107; }
        .bot-name {
            background: linear-gradient(135deg, #FF9800, #FFC107, #FF5722);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text; font-weight: 800; font-size: 14px; letter-spacing: 0.5px;
        }
        .input-group { margin-bottom: 12px; }
        .input-group input {
            width: 100%; padding: 14px 16px;
            background: rgba(255, 255, 255, 0.08);
            border: 1.5px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px; color: #fff; font-size: 15px;
            font-family: inherit; outline: none;
            transition: border-color 0.2s, background 0.2s;
        }
        .input-group input:focus { border-color: #4CAF50; background: rgba(255, 255, 255, 0.12); box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.15); }
        .input-group input::placeholder { color: #666; }
        .input-group input.error { border-color: #f44336; background: rgba(244, 67, 54, 0.1); }
        .input-group input.error:focus { box-shadow: 0 0 0 3px rgba(244, 67, 54, 0.15); }
        .input-group input.success { border-color: #4CAF50; background: rgba(76, 175, 80, 0.1); }
        .input-group input.success:focus { box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.25); }
        .error-message { color: #f44336; font-size: 12px; margin-top: 4px; display: none; }
        .error-message.show { display: block; }
        .photo-upload-box {
            width: 100%; padding: 30px 20px;
            background: rgba(255, 255, 255, 0.06);
            border: 2px dashed rgba(76, 175, 80, 0.5);
            border-radius: 14px; text-align: center; cursor: pointer;
            transition: 0.2s; margin-bottom: 12px;
        }
        .photo-upload-box:active { background: rgba(76, 175, 80, 0.15); border-color: #4CAF50; }
        .photo-upload-box.checking { border-color: #FFC107; background: rgba(255, 193, 7, 0.08); }
        .photo-upload-box .icon { font-size: 42px; margin-bottom: 10px; display: block; }
        .photo-upload-box .text { color: #4CAF50; font-size: 14px; font-weight: 600; }
        .photo-upload-box.checking .text { color: #FFC107; }
        .photo-upload-box .subtext { color: #888; font-size: 11px; margin-top: 6px; }
        #photo-input { display: none; }
        .photo-preview { display: none; width: 100%; max-height: 220px; object-fit: cover; border-radius: 14px; margin-bottom: 12px; border: 2px solid #4CAF50; }
        .photo-preview.show { display: block; }
        .change-photo-btn {
            display: none; width: 100%; padding: 12px;
            background: rgba(255, 255, 255, 0.1);
            border: 1.5px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px; color: #ccc; font-size: 13px;
            font-weight: 600; cursor: pointer; margin-bottom: 12px; font-family: inherit;
        }
        .change-photo-btn.show { display: block; }
        .rank-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 8px; }
        .rank-item {
            background: rgba(76, 175, 80, 0.15);
            border: 1px solid rgba(76, 175, 80, 0.3);
            border-radius: 10px; padding: 12px 10px; text-align: center;
            font-size: 12px; font-weight: 600; color: #4CAF50;
            cursor: pointer; transition: 0.2s;
        }
        .rank-item:active { transform: scale(0.95); }
        .rank-item.selected { background: #4CAF50; color: #fff; border-color: #4CAF50; }
        .rank-item.gold { background: rgba(255, 193, 7, 0.15); border-color: rgba(255, 193, 7, 0.3); color: #FFC107; }
        .rank-item.gold.selected { background: #FFC107; color: #000; }
        .rank-item.blue { background: rgba(33, 150, 243, 0.15); border-color: rgba(33, 150, 243, 0.3); color: #2196F3; }
        .rank-item.blue.selected { background: #2196F3; color: #fff; }
        .rank-item.purple { background: rgba(156, 39, 176, 0.15); border-color: rgba(156, 39, 176, 0.3); color: #CE93D8; }
        .rank-item.purple.selected { background: #9C27B0; color: #fff; }
        .btn {
            display: flex; align-items: center; justify-content: center;
            gap: 10px; width: 100%; padding: 15px; border: none;
            border-radius: 14px; font-size: 15px; font-weight: 700;
            cursor: pointer; margin-top: 12px; transition: transform 0.15s ease; font-family: inherit;
        }
        .btn:active { transform: scale(0.97); }
        .btn-primary { background: linear-gradient(135deg, #4CAF50, #45a049); color: #fff; box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4); }
        .btn-secondary { background: linear-gradient(135deg, #2196F3, #1976D2); color: #fff; box-shadow: 0 4px 15px rgba(33, 150, 243, 0.4); }
        .btn-warning { background: linear-gradient(135deg, #FF9800, #F57C00); color: #fff; box-shadow: 0 4px 15px rgba(255, 152, 0, 0.4); }
        .btn-outline { background: transparent; border: 1.5px solid rgba(255, 255, 255, 0.2); color: #ccc; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
        .badge-green { background: rgba(76, 175, 80, 0.2); color: #4CAF50; }
        .badge-blue { background: rgba(33, 150, 243, 0.2); color: #2196F3; }
        .footer { text-align: center; padding: 25px 0 10px; color: #555; font-size: 11px; line-height: 1.6; }
        .footer a { color: #4CAF50; text-decoration: none; }
        .fade-in { animation: fadeIn 0.4s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

        .status-overlay {
            position: fixed;
            inset: 0;
            z-index: 99999;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 24px;
            background: rgba(5, 3, 18, 0.75);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            animation: overlayFadeIn 0.25s ease;
        }
        .status-overlay.show { display: flex; }
        @keyframes overlayFadeIn { from { opacity: 0; } to { opacity: 1; } }
        .status-box {
            width: 100%;
            max-width: 360px;
            background: linear-gradient(160deg, rgba(28, 22, 60, 0.98), rgba(14, 10, 34, 0.98));
            border-radius: 22px;
            padding: 32px 24px 24px;
            text-align: center;
            border: 1.5px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
            animation: statusPop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
            position: relative;
            overflow: hidden;
        }
        @keyframes statusPop {
            0%   { transform: scale(0.85); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }
        .status-box::before {
            content: '';
            position: absolute;
            top: -50%; left: -50%;
            width: 200%; height: 200%;
            background: conic-gradient(from 0deg, transparent, rgba(76, 175, 80, 0.08), transparent 30%);
            animation: statusRotate 4s linear infinite;
            pointer-events: none;
        }
        @keyframes statusRotate { to { transform: rotate(360deg); } }
        .status-icon {
            font-size: 56px;
            line-height: 1;
            margin-bottom: 18px;
            display: inline-block;
            position: relative;
            z-index: 1;
        }
        .status-icon.spin { animation: statusSpin 1.1s linear infinite; }
        @keyframes statusSpin { to { transform: rotate(360deg); } }
        .status-title {
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 0.4px;
            margin-bottom: 8px;
            position: relative;
            z-index: 1;
        }
        .status-title.loading { color: #FFC107; }
        .status-title.success { color: #4CAF50; text-shadow: 0 0 18px rgba(76, 175, 80, 0.6); }
        .status-title.error   { color: #f44336; text-shadow: 0 0 18px rgba(244, 67, 54, 0.5); }
        .status-desc {
            font-size: 13px;
            color: #aaa;
            line-height: 1.5;
            margin-bottom: 20px;
            position: relative;
            z-index: 1;
            white-space: pre-line;
        }
        .status-bar {
            width: 100%;
            height: 4px;
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.08);
            overflow: hidden;
            margin-bottom: 20px;
            position: relative;
            z-index: 1;
        }
        .status-bar-fill {
            height: 100%;
            width: 40%;
            border-radius: 4px;
            background: linear-gradient(90deg, #FFC107, #FF9800);
            animation: barSlide 1.2s ease-in-out infinite;
        }
        .status-bar-fill.success { background: linear-gradient(90deg, #4CAF50, #8BC34A); width: 100%; animation: none; }
        .status-bar-fill.error   { background: linear-gradient(90deg, #f44336, #E91E63); width: 100%; animation: none; }
        @keyframes barSlide {
            0%   { transform: translateX(-100%); }
            100% { transform: translateX(350%); }
        }
        .status-btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 14px;
            font-size: 14px;
            font-weight: 700;
            font-family: inherit;
            cursor: pointer;
            transition: transform 0.15s ease;
            position: relative;
            z-index: 1;
        }
        .status-btn:active { transform: scale(0.97); }
        .status-btn.loading { background: rgba(255, 255, 255, 0.08); color: #888; cursor: not-allowed; }
        .status-btn.success { background: linear-gradient(135deg, #4CAF50, #45a049); color: #fff; box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4); }
        .status-btn.error   { background: linear-gradient(135deg, #f44336, #c62828); color: #fff; box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4); }
    </style>
</head>
<body>
    <div class="bg-gradient"></div>
    <div class="aurora a1"></div>
    <div class="aurora a2"></div>
    <canvas id="bg-canvas"></canvas>

    <div class="top-row">
        <div class="fps-counter" id="fps-counter">
            <span class="fps-dot"></span>
            <span id="fps-value">60</span>
            <span style="opacity:0.65">FPS</span>
        </div>
        <div class="music-toggle" id="music-toggle" onclick="toggleMusic()">
            <span class="pulse"></span>
            <span id="music-icon">🔊</span>
        </div>
    </div>

    <div class="container">
        <div class="header fade-in">
            <div class="logo-wrapper">
                <div class="ring ring-1"></div>
                <div class="ring ring-2"></div>
                <div class="ring ring-3"></div>
                <div class="logo">🎮</div>
            </div>
            <h1>TOMMY BOT</h1>
            <p>PUBG Mobile Statistics Panel</p>
        </div>

        <div class="card fade-in">
            <div class="card-title">👤 Your Information</div>
            <div class="info-row"><span class="info-label">Name:</span><span class="info-value" id="user-name">Loading...</span></div>
            <div class="info-row"><span class="info-label">Username:</span><span class="info-value green" id="user-username">-</span></div>
            <div class="info-row"><span class="info-label">Telegram ID:</span><span class="info-value" id="user-id">-</span></div>
            <div class="info-row"><span class="info-label">Status:</span><span class="info-value"><span class="badge badge-green">✅ ACTIVE</span></span></div>
        </div>

        <div class="card fade-in">
            <div class="card-title">🆔 PUBG Mobile ID</div>
            <div class="input-group">
                <input type="tel" id="player-id" placeholder="Enter your 11-digit ID" maxlength="11" inputmode="numeric">
                <div class="error-message" id="id-error">ID must be 11 digits, start with 5 or 6, and contain no identical digits.</div>
            </div>
        </div>

        <div class="card fade-in">
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

        <div class="card fade-in">
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

        <div class="card fade-in">
            <div class="card-title">👑 Ultimate Royale</div>
            <div class="rank-grid" id="ultimate-ranks">
                <div class="rank-item" data-rank="Vanguard">Vanguard</div>
                <div class="rank-item" data-rank="Exceed">Exceed</div>
                <div class="rank-item blue" data-rank="Supreme">Supreme</div>
                <div class="rank-item blue" data-rank="Peerless">Peerless</div>
                <div class="rank-item purple" data-rank="Legend">Legend</div>
            </div>
        </div>

        <div class="card fade-in">
            <div class="card-title">💀 Kills in 1 Match</div>
            <div class="input-group">
                <input type="tel" id="kills" placeholder="Enter kills (1-100)" maxlength="3" inputmode="numeric">
                <div class="error-message" id="kills-error">Kills must be between 1 and 100.</div>
            </div>
        </div>

        <div class="card fade-in">
            <div class="card-title">👤 FOR INQUIRIES</div>
            <div class="info-row"><span class="info-label">Bot name:</span><span class="info-value"><span class="bot-name">TOMMY BOT</span></span></div>
            <div class="info-row"><span class="info-label">Channel:</span><span class="info-value"><a class="info-link channel" onclick="openChannel()">@TommyXcheat2</a></span></div>
            <div class="info-row"><span class="info-label">Owner:</span><span class="info-value"><a class="info-link owner" onclick="openOwner()">@Tommy_1727</a></span></div>
            <div class="info-row"><span class="info-label">Version:</span><span class="info-value"><span class="badge badge-blue">v3.5</span></span></div>
        </div>

        <button class="btn btn-primary" onclick="openStatistics()">📊 STATISTICS</button>
        <button class="btn btn-secondary" onclick="startNew()">📤 START NEW</button>
        <button class="btn btn-warning" onclick="openChannel()">📢 Go to Channel</button>
        <button class="btn btn-outline" onclick="closeApp()">❌ Close</button>

        <div class="footer">
            © 2026 <a href="https://t.me/Tommy_1727">@Tommy_1727</a><br>
            All rights reserved.
        </div>
    </div>

    <div class="status-overlay" id="status-overlay">
        <div class="status-box">
            <div class="status-icon" id="status-icon">⏳</div>
            <div class="status-title" id="status-title">Sending...</div>
            <div class="status-desc" id="status-desc">Please wait, sending to channel.</div>
            <div class="status-bar"><div class="status-bar-fill" id="status-bar-fill"></div></div>
            <button class="status-btn loading" id="status-btn" onclick="closeStatus()">Please wait...</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        tg.setHeaderColor('#0a0820');
        tg.setBackgroundColor('#0a0820');

        const API_URL = "https://tommy-backend.onrender.com/send-feedback";
        const CHANNEL_USERNAME = "@TommyXcheat2";

        const statusOverlay = document.getElementById('status-overlay');
        const statusIcon    = document.getElementById('status-icon');
        const statusTitle   = document.getElementById('status-title');
        const statusDesc    = document.getElementById('status-desc');
        const statusBarFill = document.getElementById('status-bar-fill');
        const statusBtn     = document.getElementById('status-btn');

        function showStatus(type, message) {
            statusOverlay.classList.add('show');
            statusIcon.classList.remove('spin');
            statusTitle.classList.remove('loading', 'success', 'error');
            statusBarFill.classList.remove('success', 'error');
            statusBtn.classList.remove('loading', 'success', 'error');

            if (type === 'loading') {
                statusIcon.textContent = '⏳';
                statusIcon.classList.add('spin');
                statusTitle.classList.add('loading');
                statusTitle.textContent = 'Sending...';
                statusDesc.textContent = message || 'Please wait, sending to channel.';
                statusBarFill.classList.add('loading');
                statusBarFill.style.width = '40%';
                statusBtn.classList.add('loading');
                statusBtn.textContent = 'Please wait...';
                statusBtn.disabled = true;
            } else if (type === 'success') {
                statusIcon.textContent = '✅';
                statusTitle.classList.add('success');
                statusTitle.textContent = 'Successfully completed.';
                statusDesc.textContent = message || 'Your statistics have been sent to the channel.';
                statusBarFill.classList.add('success');
                statusBarFill.style.width = '100%';
                statusBtn.classList.add('success');
                statusBtn.textContent = '✅ OK';
                statusBtn.disabled = false;
            } else if (type === 'error') {
                statusIcon.textContent = '❌';
                statusTitle.classList.add('error');
                statusTitle.textContent = 'Unsuccessfully completed.';
                statusDesc.textContent = message || 'Something went wrong. Please try again.';
                statusBarFill.classList.add('error');
                statusBarFill.style.width = '100%';
                statusBtn.classList.add('error');
                statusBtn.textContent = '❌ Try Again';
                statusBtn.disabled = false;
            }
        }

        function closeStatus() { statusOverlay.classList.remove('show'); }

        const fpsCounterEl = document.getElementById('fps-counter');
        const fpsValueEl   = document.getElementById('fps-value');
        let fpsFrames = 0, fpsLastTime = performance.now(), currentFPS = 60, lowFpsStreak = 0, particleCountMult = 1.0;

        function updateFPS() {
            fpsFrames++;
            const now = performance.now();
            const elapsed = now - fpsLastTime;
            if (elapsed >= 500) {
                currentFPS = Math.round((fpsFrames * 1000) / elapsed);
                fpsValueEl.textContent = currentFPS;
                fpsFrames = 0; fpsLastTime = now;
                fpsCounterEl.classList.remove('low', 'bad');
                if (currentFPS < 40) fpsCounterEl.classList.add('bad');
                else if (currentFPS < 55) fpsCounterEl.classList.add('low');
                if (currentFPS < 55) {
                    lowFpsStreak++;
                    if (lowFpsStreak >= 1 && particleCountMult > 0.3) {
                        particleCountMult = Math.max(0.3, particleCountMult - 0.2);
                        rebuildParticles(); lowFpsStreak = 0;
                    }
                } else if (currentFPS >= 60 && particleCountMult < 1.0) {
                    particleCountMult = Math.min(1.0, particleCountMult + 0.1);
                    rebuildParticles();
                } else { lowFpsStreak = 0; }
            }
        }

        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d', { alpha: true, desynchronized: true });
        let W = 0, H = 0, particles = [], ripples = [], maxParticles = 25;
        const CONNECTION_DIST = 130, CONNECTION_DIST_SQ = CONNECTION_DIST * CONNECTION_DIST;

        function computeMaxParticles() {
            const area = window.innerWidth * window.innerHeight;
            const base = Math.min(30, Math.floor(area / 28000));
            return Math.max(12, Math.floor(base * particleCountMult));
        }

        function resizeCanvas() {
            const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
            W = window.innerWidth; H = window.innerHeight;
            canvas.width  = Math.floor(W * dpr); canvas.height = Math.floor(H * dpr);
            canvas.style.width  = W + 'px'; canvas.style.height = H + 'px';
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        function newParticle() {
            return {
                x: Math.random() * W, y: Math.random() * H,
                r: Math.random() * 1.4 + 0.6,
                vx: (Math.random() - 0.5) * 0.28,
                vy: (Math.random() - 0.5) * 0.28,
                hue: [140, 210, 280][Math.floor(Math.random() * 3)],
                a: Math.random() * 0.45 + 0.3
            };
        }

        function rebuildParticles() {
            maxParticles = computeMaxParticles();
            while (particles.length > maxParticles) particles.pop();
            while (particles.length < maxParticles) particles.push(newParticle());
        }

        function initBackground() {
            resizeCanvas(); particles = [];
            const count = computeMaxParticles();
            for (let i = 0; i < count; i++) particles.push(newParticle());
            ripples = [];
        }
        initBackground();

        let resizeTimeout = null;
        window.addEventListener('resize', () => {
            if (resizeTimeout) clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                resizeCanvas();
                for (const p of particles) {
                    if (p.x > W) p.x = Math.random() * W;
                    if (p.y > H) p.y = Math.random() * H;
                }
            }, 150);
        });

        let lastRippleTime = 0;
        document.addEventListener('pointerdown', (e) => {
            const now = performance.now();
            if (now - lastRippleTime < 80) return;
            lastRippleTime = now;
            ripples.push({ x: e.clientX, y: e.clientY, r: 0, maxR: 100, life: 0, maxLife: 0.8 });
            if (ripples.length > 4) ripples.shift();
        }, { passive: true });

        function drawBackground() {
            ctx.clearRect(0, 0, W, H);
            const n = particles.length;
            for (let i = 0; i < n; i++) {
                const pi = particles[i];
                for (let j = i + 1; j < n; j++) {
                    const pj = particles[j];
                    const dx = pi.x - pj.x, dy = pi.y - pj.y;
                    const d2 = dx * dx + dy * dy;
                    if (d2 < CONNECTION_DIST_SQ) {
                        const alpha = (1 - Math.sqrt(d2) / CONNECTION_DIST) * 0.13;
                        ctx.beginPath(); ctx.strokeStyle = `hsla(160, 70%, 55%, ${alpha})`;
                        ctx.lineWidth = 0.55; ctx.moveTo(pi.x, pi.y); ctx.lineTo(pj.x, pj.y); ctx.stroke();
                    }
                }
            }
            for (let i = 0; i < n; i++) {
                const p = particles[i];
                p.x += p.vx; p.y += p.vy;
                if (p.x < 0 || p.x > W) p.vx = -p.vx;
                if (p.y < 0 || p.y > H) p.vy = -p.vy;
                ctx.beginPath();
                ctx.fillStyle = `hsla(${p.hue}, 80%, 68%, ${p.a})`;
                ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2);
                ctx.fill();
            }
            for (let i = ripples.length - 1; i >= 0; i--) {
                const rp = ripples[i];
                rp.life += 1 / 60;
                const t = rp.life / rp.maxLife;
                if (t >= 1) { ripples.splice(i, 1); continue; }
                ctx.beginPath();
                ctx.strokeStyle = `hsla(140, 90%, 65%, ${(1 - t) * 0.5})`;
                ctx.lineWidth = 1.5 * (1 - t) + 0.4;
                ctx.arc(rp.x, rp.y, rp.maxR * t, 0, Math.PI * 2);
                ctx.stroke();
            }
        }

        const FRAME_INTERVAL = 1000 / 60;
        let lastFrameTime = 0, masterRafId = null;
        function masterLoop(now) {
            masterRafId = requestAnimationFrame(masterLoop);
            const delta = now - lastFrameTime;
            if (delta < FRAME_INTERVAL - 0.5) return;
            lastFrameTime = now; updateFPS(); drawBackground();
        }
        masterRafId = requestAnimationFrame(masterLoop);

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) { if (masterRafId) cancelAnimationFrame(masterRafId); masterRafId = null; }
            else if (!masterRafId) { fpsFrames = 0; fpsLastTime = performance.now(); lastFrameTime = 0; masterRafId = requestAnimationFrame(masterLoop); }
        });

        let audioCtx = null, musicBus = null, compressor = null, musicFilter = null;
        let musicDelay = null, musicDelayFb = null, musicDelayWet = null;
        let musicPlaying = false, schedulerTimer = null;
        let droneOsc1 = null, droneGain1 = null, droneOsc2 = null, droneGain2 = null, droneOsc3 = null, droneGain3 = null;

        const SCHEDULE_AHEAD = 0.8, SCHEDULER_TICK = 200, MEASURE_DURATION = 12.0;
        const NOTE_FADE_IN = 1.5, NOTE_FADE_OUT = 2.0, FADE_EPSILON = 0.0008;
        const BASE_MUSIC_VOLUME = 0.055, BASE_CLICK_VOLUME = 0.018;
        const BASE_SUCCESS_VOLUME = 0.032, BASE_ERROR_VOLUME = 0.038;

        let nextChordTime = 0, chordIndex = 0;

        const CHORDS = [
            { bass: 87.31, notes: [349.23, 440.00, 523.25] },
            { bass: 98.00, notes: [392.00, 466.16, 587.33] },
            { bass: 73.42, notes: [293.66, 349.23, 440.00] },
            { bass: 116.54, notes: [466.16, 587.33, 698.46] },
            { bass: 130.81, notes: [261.63, 311.13, 392.00] },
            { bass: 87.31, notes: [349.23, 440.00, 523.25] }
        ];

        const MELODY_NOTES = [
            698.46, 880.00, 1046.50, 880.00, 783.99, 932.33, 1174.66, 932.33,
            587.33, 698.46, 880.00, 698.46, 932.33, 1174.66, 1396.91, 1174.66,
            523.25, 622.25, 783.99, 622.25, 698.46, 880.00, 1046.50, 880.00
        ];
        let melodyIndex = 0;

        function ensureAudio() {
            if (audioCtx) return audioCtx;
            try { audioCtx = new (window.AudioContext || window.webkitAudioContext)({ latencyHint: 'playback' }); }
            catch (e) { return null; }
            return audioCtx;
        }
        function unlockAudio() {
            const c = ensureAudio();
            if (c && c.state === 'suspended') c.resume();
        }
        function buildAudioGraph() {
            const c = ensureAudio(); if (!c) return;
            compressor = c.createDynamicsCompressor();
            compressor.threshold.value = -20; compressor.knee.value = 30;
            compressor.ratio.value = 8; compressor.attack.value = 0.01;
            compressor.release.value = 0.35;
            compressor.connect(c.destination);
            musicBus = c.createGain(); musicBus.gain.value = FADE_EPSILON;
            musicBus.connect(compressor);
            musicFilter = c.createBiquadFilter();
            musicFilter.type = 'lowpass'; musicFilter.frequency.value = 1600;
            musicFilter.Q.value = 0.4; musicFilter.connect(musicBus);
            musicDelay = c.createDelay(2.0); musicDelay.delayTime.value = 0.65;
            musicDelayFb = c.createGain(); musicDelayFb.gain.value = 0.38;
            musicDelayWet = c.createGain(); musicDelayWet.gain.value = 0.40;
            musicDelay.connect(musicDelayFb); musicDelayFb.connect(musicDelay);
            musicDelay.connect(musicDelayWet); musicDelayWet.connect(musicBus);
        }
        function startDrone() {
            const c = audioCtx;
            droneOsc1 = c.createOscillator(); droneOsc1.type = 'sine'; droneOsc1.frequency.value = 87.31;
            droneGain1 = c.createGain();
            droneGain1.gain.setValueAtTime(0, c.currentTime);
            droneGain1.gain.linearRampToValueAtTime(0.055, c.currentTime + 6);
            droneOsc1.connect(droneGain1); droneGain1.connect(musicFilter); droneGain1.connect(musicDelay); droneOsc1.start();
            droneOsc2 = c.createOscillator(); droneOsc2.type = 'sine'; droneOsc2.frequency.value = 130.81;
            droneGain2 = c.createGain();
            droneGain2.gain.setValueAtTime(0, c.currentTime);
            droneGain2.gain.linearRampToValueAtTime(0.035, c.currentTime + 8);
            droneOsc2.connect(droneGain2); droneGain2.connect(musicFilter); droneGain2.connect(musicDelay); droneOsc2.start();
            droneOsc3 = c.createOscillator(); droneOsc3.type = 'sine'; droneOsc3.frequency.value = 349.23;
            droneGain3 = c.createGain();
            droneGain3.gain.setValueAtTime(0, c.currentTime);
            droneGain3.gain.linearRampToValueAtTime(0.012, c.currentTime + 10);
            droneOsc3.connect(droneGain3); droneGain3.connect(musicFilter); droneGain3.connect(musicDelay); droneOsc3.start();
        }
        function stopDrone() {
            const c = audioCtx; if (!c) return;
            const now = c.currentTime, end = now + 3.0;
            try {
                [droneGain1, droneGain2, droneGain3].forEach(g => {
                    if (g) { g.gain.cancelScheduledValues(now); g.gain.setValueAtTime(g.gain.value, now); g.gain.linearRampToValueAtTime(0, end); }
                });
            } catch (e) {}
            setTimeout(() => {
                [droneOsc1, droneOsc2, droneOsc3].forEach(o => { try { o && o.stop(); } catch (e) {} try { o && o.disconnect(); } catch (e) {} });
                [droneGain1, droneGain2, droneGain3].forEach(g => { try { g && g.disconnect(); } catch (e) {} });
                droneOsc1 = droneGain1 = droneOsc2 = droneGain2 = droneOsc3 = droneGain3 = null;
            }, 3200);
        }
        function addPadVoice(freq, type, startTime, dur, peak) {
            const c = audioCtx;
            const osc = c.createOscillator(); osc.type = type; osc.frequency.value = freq;
            const g = c.createGain();
            const sustainEnd = startTime + dur - NOTE_FADE_OUT;
            g.gain.setValueAtTime(0, startTime);
            g.gain.linearRampToValueAtTime(peak, startTime + NOTE_FADE_IN);
            g.gain.setValueAtTime(peak, sustainEnd);
            g.gain.linearRampToValueAtTime(FADE_EPSILON, startTime + dur);
            osc.connect(g); g.connect(musicFilter); g.connect(musicDelay);
            osc.start(startTime); osc.stop(startTime + dur + 0.1);
            osc.onended = () => { try { g.disconnect(); osc.disconnect(); } catch (e) {} };
        }
        function addMelodyNote(freq, startTime) {
            const c = audioCtx; const dur = 3.2;
            const osc = c.createOscillator(); osc.type = 'triangle'; osc.frequency.value = freq;
            const harm = c.createOscillator(); harm.type = 'sine'; harm.frequency.value = freq * 2;
            const g = c.createGain();
            g.gain.setValueAtTime(0, startTime);
            g.gain.linearRampToValueAtTime(0.085, startTime + 0.04);
            g.gain.exponentialRampToValueAtTime(0.015, startTime + 1.5);
            g.gain.linearRampToValueAtTime(FADE_EPSILON, startTime + dur);
            const gh = c.createGain();
            gh.gain.setValueAtTime(0, startTime);
            gh.gain.linearRampToValueAtTime(0.025, startTime + 0.03);
            gh.gain.exponentialRampToValueAtTime(0.003, startTime + 1.2);
            gh.gain.linearRampToValueAtTime(FADE_EPSILON, startTime + dur);
            osc.connect(g); harm.connect(gh);
            g.connect(musicFilter); gh.connect(musicFilter);
            g.connect(musicDelay); gh.connect(musicDelay);
            osc.start(startTime); harm.start(startTime);
            osc.stop(startTime + dur + 0.05); harm.stop(startTime + dur + 0.05);
            osc.onended = () => { try { g.disconnect(); gh.disconnect(); osc.disconnect(); harm.disconnect(); } catch (e) {} };
        }
        function scheduleMeasure(startTime) {
            const chord = CHORDS[chordIndex % CHORDS.length]; chordIndex++;
            addPadVoice(chord.bass, 'sine', startTime, MEASURE_DURATION, 0.09);
            chord.notes.forEach((f, i) => addPadVoice(f, i === 0 ? 'sine' : 'triangle', startTime, MEASURE_DURATION, 0.048));
            const step = MEASURE_DURATION / 4;
            for (let k = 0; k < 4; k++) {
                const note = MELODY_NOTES[melodyIndex % MELODY_NOTES.length]; melodyIndex++;
                addMelodyNote(note, startTime + k * step);
            }
        }
        function musicScheduler() {
            if (!musicPlaying || !audioCtx) return;
            while (nextChordTime < audioCtx.currentTime + SCHEDULE_AHEAD) {
                scheduleMeasure(nextChordTime); nextChordTime += MEASURE_DURATION;
            }
        }
        function startMusic() {
            const c = ensureAudio(); if (!c) return;
            if (c.state === 'suspended') c.resume();
            if (musicPlaying) return;
            if (!musicBus) buildAudioGraph();
            const now = c.currentTime;
            musicBus.gain.cancelScheduledValues(now);
            musicBus.gain.setValueAtTime(FADE_EPSILON, now);
            musicBus.gain.linearRampToValueAtTime(BASE_MUSIC_VOLUME, now + 3.5);
            startDrone(); nextChordTime = now + 0.3; musicPlaying = true;
            musicScheduler(); schedulerTimer = setInterval(musicScheduler, SCHEDULER_TICK);
        }
        function stopMusic() {
            if (!musicPlaying) return;
            musicPlaying = false;
            if (schedulerTimer) { clearInterval(schedulerTimer); schedulerTimer = null; }
            if (musicBus && audioCtx) {
                const now = audioCtx.currentTime;
                try {
                    musicBus.gain.cancelScheduledValues(now);
                    musicBus.gain.setValueAtTime(musicBus.gain.value, now);
                    musicBus.gain.linearRampToValueAtTime(FADE_EPSILON, now + 1.5);
                } catch (e) {}
            }
            stopDrone();
        }
        function playClickSound() {
            const c = ensureAudio(); if (!c) return;
            if (c.state === 'suspended') c.resume();
            if (!compressor) buildAudioGraph();
            const now = c.currentTime;
            const osc = c.createOscillator(); osc.type = 'sine';
            osc.frequency.setValueAtTime(520, now);
            osc.frequency.exponentialRampToValueAtTime(380, now + 0.07);
            const g = c.createGain();
            g.gain.setValueAtTime(0, now);
            g.gain.linearRampToValueAtTime(BASE_CLICK_VOLUME, now + 0.005);
            g.gain.exponentialRampToValueAtTime(FADE_EPSILON, now + 0.10);
            osc.connect(g); g.connect(compressor);
            osc.start(now); osc.stop(now + 0.14);
        }
        function playSuccessSound() {
            const c = ensureAudio(); if (!c) return;
            if (!compressor) buildAudioGraph();
            const now = c.currentTime;
            [523.25, 659.25, 783.99, 1046.50].forEach((f, i) => {
                const o = c.createOscillator(); o.type = 'sine'; o.frequency.value = f;
                const g = c.createGain();
                const t = now + i * 0.11; const dur = 0.65;
                g.gain.setValueAtTime(0, t);
                g.gain.linearRampToValueAtTime(BASE_SUCCESS_VOLUME, t + 0.02);
                g.gain.exponentialRampToValueAtTime(FADE_EPSILON, t + dur);
                o.connect(g); g.connect(compressor);
                o.start(t); o.stop(t + dur + 0.05);
            });
        }
        function playErrorSound() {
            const c = ensureAudio(); if (!c) return;
            if (c.state === 'suspended') c.resume();
            if (!compressor) buildAudioGraph();
            const now = c.currentTime;
            [{ start: now }, { start: now + 0.18 }].forEach((b) => {
                const osc = c.createOscillator(); osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(320, b.start);
                osc.frequency.exponentialRampToValueAtTime(240, b.start + 0.14);
                const g = c.createGain();
                g.gain.setValueAtTime(0, b.start);
                g.gain.linearRampToValueAtTime(BASE_ERROR_VOLUME * 0.6, b.start + 0.01);
                g.gain.exponentialRampToValueAtTime(FADE_EPSILON, b.start + 0.16);
                osc.connect(g); g.connect(compressor);
                osc.start(b.start); osc.stop(b.start + 0.2);
            });
        }

        let userMuted = false;
        function toggleMusic() {
            unlockAudio();
            const btn = document.getElementById('music-toggle');
            const icon = document.getElementById('music-icon');
            if (musicPlaying) {
                stopMusic(); userMuted = true;
                btn.classList.add('muted'); icon.textContent = '🔇'; playClickSound();
            } else {
                startMusic(); userMuted = false;
                btn.classList.remove('muted'); icon.textContent = '🔊';
            }
        }

        function attachClickSounds() {
            document.querySelectorAll('.btn, .rank-item, .info-link, .change-photo-btn, #photo-box').forEach(el => {
                if (el.dataset.soundBound) return;
                el.dataset.soundBound = "1";
                el.addEventListener('click', () => playClickSound(), { passive: true });
            });
        }
        function armAutoStart() {
            const kick = () => {
                unlockAudio();
                if (!userMuted && !musicPlaying) startMusic();
                document.removeEventListener('touchstart', kick);
                document.removeEventListener('click', kick);
            };
            document.addEventListener('touchstart', kick, { once: true, passive: true });
            document.addEventListener('click', kick, { once: true });
        }

        const user = tg.initDataUnsafe.user;
        if (user) {
            const fullName = ((user.first_name || '') + ' ' + (user.last_name || '')).trim();
            document.getElementById('user-name').innerText = fullName || `User #${user.id}`;
            document.getElementById('user-username').innerText = user.username ? '@' + user.username : "—";
            document.getElementById('user-id').innerText = user.id;
        } else {
            document.getElementById('user-name').innerText = "Unknown";
        }

        function buildOwnerInfo() {
            if (!user) return { plain: "Unknown" };
            if (user.username) return { plain: "@" + user.username };
            const fullName = ((user.first_name || '') + ' ' + (user.last_name || '')).trim();
            if (fullName) return { plain: `${fullName} (ID: ${user.id})` };
            return { plain: `User #${user.id}` };
        }

        let selectedClassic = null, selectedUltimate = null;
        document.querySelectorAll('#classic-ranks .rank-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('#classic-ranks .rank-item').forEach(i => i.classList.remove('selected'));
                item.classList.add('selected'); selectedClassic = item.dataset.rank; playSuccessSound();
            });
        });
        document.querySelectorAll('#ultimate-ranks .rank-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('#ultimate-ranks .rank-item').forEach(i => i.classList.remove('selected'));
                item.classList.add('selected'); selectedUltimate = item.dataset.rank; playSuccessSound();
            });
        });

        const photoBox = document.getElementById('photo-box');
        const photoInput = document.getElementById('photo-input');
        const photoPreview = document.getElementById('photo-preview');
        const changePhotoBtn = document.getElementById('change-photo-btn');
        let photoValid = false;

        photoBox.addEventListener('click', () => { if (!photoBox.classList.contains('checking')) photoInput.click(); });

        function loadImageFromFile(file) {
            return new Promise((resolve, reject) => {
                const url = URL.createObjectURL(file);
                const img = new Image();
                img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
                img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('decode failed')); };
                img.src = url;
            });
        }
        function rgbToHsv(r, g, b) {
            r /= 255; g /= 255; b /= 255;
            const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
            let h = 0;
            if (d !== 0) {
                if (max === r) h = ((g - b) / d) % 6;
                else if (max === g) h = (b - r) / d + 2;
                else h = (r - g) / d + 4;
                h *= 60; if (h < 0) h += 360;
            }
            const s = max === 0 ? 0 : d / max;
            return [h, s, max];
        }
        async function validatePubgScreenshot(file) {
            if (!file.type || !file.type.startsWith('image/'))
                return { ok: false, reason: 'Only image files are allowed (JPG / PNG).' };
            let img;
            try { img = await loadImageFromFile(file); }
            catch (e) { return { ok: false, reason: 'Could not read this image.' }; }
            const w = img.naturalWidth || img.width;
            const h = img.naturalHeight || img.height;
            if (w < 640 || h < 360) return { ok: false, reason: 'Image resolution is too low.' };
            if (w <= h) return { ok: false, reason: 'PUBG Mobile is a landscape game. Portrait images not accepted.' };
            const ratio = w / h;
            const allowedRatios = [1.333, 1.5, 1.6, 1.667, 1.778, 2.0, 2.056, 2.111, 2.167, 2.222, 2.333, 2.444];
            if (!allowedRatios.some(r => Math.abs(ratio - r) <= 0.06))
                return { ok: false, reason: 'This image does not match phone/tablet screen ratio.' };
            const CW = 240, CH = Math.max(1, Math.round(h * (CW / w)));
            const c2 = document.createElement('canvas');
            c2.width = CW; c2.height = CH;
            const cctx = c2.getContext('2d', { willReadFrequently: true });
            cctx.drawImage(img, 0, 0, CW, CH);
            let data;
            try { data = cctx.getImageData(0, 0, CW, CH).data; }
            catch (e) { return { ok: false, reason: 'Security error.' }; }
            const totalPx = CW * CH;
            let white = 0, black = 0, vivid = 0, green = 0, earth = 0, sky = 0, gray = 0;
            for (let i = 0; i < data.length; i += 4) {
                const hsv = rgbToHsv(data[i], data[i + 1], data[i + 2]);
                const hue = hsv[0], sat = hsv[1], val = hsv[2];
                if (val > 0.86 && sat < 0.12) white++;
                if (val < 0.10) black++;
                if (sat > 0.72 && val > 0.62) vivid++;
                if (sat < 0.16 && val > 0.15 && val < 0.87) gray++;
                else if (hue >= 65 && hue <= 165 && sat >= 0.16 && val > 0.12) green++;
                else if (hue >= 8 && hue < 60 && sat >= 0.18 && val > 0.12) earth++;
                else if (hue >= 175 && hue <= 260 && sat >= 0.08 && val > 0.35) sky++;
            }
            const whiteR = white / totalPx, blackR = black / totalPx, vividR = vivid / totalPx;
            const gameR = (green + earth + sky + gray * 0.8) / totalPx;
            if (whiteR > 0.55) return { ok: false, reason: 'Looks like a document/chat screenshot.' };
            if (vividR > 0.32) return { ok: false, reason: 'Image is too colorful.' };
            if (blackR > 0.62) return { ok: false, reason: 'Image is too dark.' };
            if (gameR < 0.45) return { ok: false, reason: 'Does not look like a PUBG Mobile screenshot.' };
            return { ok: true, reason: '' };
        }
        function setPhotoBoxState(state) {
            const icon = photoBox.querySelector('.icon');
            const text = photoBox.querySelector('.text');
            const sub = photoBox.querySelector('.subtext');
            if (state === 'checking') {
                photoBox.style.display = 'block';
                photoBox.classList.add('checking');
                photoPreview.classList.remove('show');
                changePhotoBtn.classList.remove('show');
                icon.textContent = '⏳';
                text.textContent = 'Checking screenshot...';
                sub.textContent = 'PUBG Mobile verification in progress';
            } else {
                photoBox.classList.remove('checking');
                icon.textContent = '📤';
                text.textContent = 'Tap to upload screenshot';
                sub.textContent = 'JPG, PNG • Max 5MB • PUBG Mobile only';
            }
        }
        photoInput.addEventListener('change', async function (e) {
            const file = e.target.files[0];
            if (!file) return;
            if (file.size > 5 * 1024 * 1024) {
                playErrorSound();
                tg.showAlert("❌ File too large!\n\nMaximum size is 5 MB.");
                resetPhoto(); return;
            }
            setPhotoBoxState('checking');
            const result = await validatePubgScreenshot(file);
            if (!result.ok) {
                setPhotoBoxState('idle');
                photoInput.value = '';
                photoValid = false;
                playErrorSound();
                tg.showAlert("❌ INVALID SCREENSHOT\n\n" + result.reason);
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                photoPreview.src = event.target.result;
                photoPreview.classList.add('show');
                photoBox.style.display = 'none';
                photoBox.classList.remove('checking');
                changePhotoBtn.classList.add('show');
                photoValid = true;
                playSuccessSound();
            };
            reader.readAsDataURL(file);
        });
        function resetPhoto() {
            photoInput.value = '';
            photoPreview.src = '';
            photoPreview.classList.remove('show');
            photoBox.style.display = 'block';
            changePhotoBtn.classList.remove('show');
            photoValid = false;
            setPhotoBoxState('idle');
        }
        function validatePlayerId(id) {
            if (!/^\d{11}$/.test(id)) return false;
            if (id[0] !== '5' && id[0] !== '6') return false;
            if (/^(\d)\1{10}$/.test(id)) return false;
            return true;
        }
        const playerIdInput = document.getElementById('player-id');
        const idError = document.getElementById('id-error');
        let idSoundTimer = null;
        playerIdInput.addEventListener('input', function() {
            const id = this.value.trim();
            playerIdInput.classList.remove('error', 'success');
            idError.classList.remove('show');
            if (id.length === 11) {
                if (validatePlayerId(id)) playerIdInput.classList.add('success');
                else { playerIdInput.classList.add('error'); idError.classList.add('show'); }
            }
            clearTimeout(idSoundTimer);
            idSoundTimer = setTimeout(() => {
                if (id.length === 0) return;
                if (id.length === 11) {
                    if (validatePlayerId(id)) playSuccessSound();
                    else playErrorSound();
                }
            }, 700);
        });

        const killsInput = document.getElementById('kills');
        const killsError = document.getElementById('kills-error');
        let killsSoundTimer = null;
        killsInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value.startsWith('0') && this.value.length > 1)
                this.value = this.value.replace(/^0+/, '');
            const val = parseInt(this.value);
            killsInput.classList.remove('error', 'success');
            killsError.classList.remove('show');
            if (this.value !== '') {
                if (isNaN(val) || val < 1 || val > 100) {
                    killsInput.classList.add('error');
                    killsError.classList.add('show');
                } else killsInput.classList.add('success');
            }
            clearTimeout(killsSoundTimer);
            killsSoundTimer = setTimeout(() => {
                const v = this.value; if (v === '') return;
                const num = parseInt(v);
                if (isNaN(num) || num < 1 || num > 100) playErrorSound();
                else playSuccessSound();
            }, 700);
        });
        function validateKills(k) {
            const val = parseInt(k);
            if (isNaN(val)) return false;
            if (val < 1 || val > 100) return false;
            return true;
        }

        function openStatistics() { tg.openTelegramLink("https://t.me/TommyXcheat2"); }

        async function startNew() {
            const playerId = document.getElementById('player-id').value.trim();
            const kills = document.getElementById('kills').value.trim();

            if (!validatePlayerId(playerId)) {
                playErrorSound();
                tg.showAlert("❌ Invalid Player ID!\n\nID must be:\n• 11 digits\n• Start with 5 or 6\n• No identical digits");
                return;
            }
            if (!selectedClassic) { playErrorSound(); tg.showAlert("❌ Please select a Classic Rank!"); return; }
            if (!selectedUltimate) { playErrorSound(); tg.showAlert("❌ Please select an Ultimate Royale Rank!"); return; }
            if (!validateKills(kills)) { playErrorSound(); tg.showAlert("❌ Invalid Kills!\n\nKills must be between 1 and 100."); return; }

            const file = photoInput.files[0];
            if (!file) { playErrorSound(); tg.showAlert("❌ Please upload a screenshot!"); return; }
            if (!photoValid) { playErrorSound(); tg.showAlert("❌ Invalid screenshot!"); return; }

            showStatus('loading', 'Please wait, sending to channel.');

            const hiddenId = playerId.substring(0, 3) + "***" + playerId.substring(9);
            const now = new Date();
            const hours   = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const day     = String(now.getDate()).padStart(2, '0');
            const month   = String(now.getMonth() + 1).padStart(2, '0');
            const year    = now.getFullYear();
            const timeStr = `${hours}:${minutes}  ${day}.${month}.${year}`;
            const ownerInfo = buildOwnerInfo();

            const caption =
                `👤 OWNER: ${ownerInfo.plain}\n` +
                `🎮 Player ID: ${hiddenId}\n` +
                `🏆 CLASSIC RANK: ${selectedClassic}\n` +
                `🏆 ULTIMATE ROYALE RANK: ${selectedUltimate}\n` +
                `🕒 TIME: ${timeStr}\n` +
                `💀 KILL: ${kills}\n` +
                `\n` +
                `👤 OWNER: @Tommy_1727 ✅`;

            const formData = new FormData();
            formData.append('photo', file);
            formData.append('caption', caption);

            try {
                const response = await fetch(API_URL, { method: 'POST', body: formData });
                const result = await response.json();
                if (result.ok) {
                    playSuccessSound();
                    showStatus('success', 'Statistics sent to channel successfully!\n\n📢 ' + CHANNEL_USERNAME);
                    setTimeout(() => { closeStatus(); setTimeout(() => { tg.close(); }, 300); }, 3000);
                } else {
                    playErrorSound();
                    showStatus('error', 'Telegram error:\n' + (result.description || 'Unknown error'));
                }
            } catch (error) {
                console.error("Fetch error:", error);
                playErrorSound();
                showStatus('error', 'Network error!\nBackend serverga ulanib bo\'lmadi.');
            }
        }

        function openChannel() { tg.openTelegramLink("https://t.me/TommyXcheat2"); }
        function openOwner()   { tg.openTelegramLink("https://t.me/Tommy_1727"); }
        function closeApp()    { tg.close(); }

        tg.BackButton.show();
        tg.BackButton.onClick(() => tg.close());

        attachClickSounds();
        armAutoStart();
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
    ratio = w / h
    allowed = [1.333, 1.5, 1.6, 1.667, 1.778, 2.0, 2.056, 2.111, 2.167, 2.222, 2.333, 2.444]
    if not any(abs(ratio - r) <= 0.06 for r in allowed):
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
# GEMINI AI
# ============================================================
def analyze_with_ai(image_bytes, mime_type="image/jpeg"):
    if not GEMINI_API_KEY:
        return None
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            "You are a PUBG Mobile screenshot analyzer. "
            "Return ONLY a valid JSON object, no markdown, no extra text:\n"
            '{"player_id":"11-digit UID or null","classic_rank":"... or null",'
            '"ultimate_rank":"... or null","kills":"number or null","map":"name or null"}\n'
            "RULES: player_id is exactly 11 digits starting with 5 or 6. "
            "If not visible, set null."
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 500}
        }
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload)
            result = r.json()
        if "candidates" not in result or not result["candidates"]:
            logger.error(f"❌ AI xato: {str(result)[:300]}")
            return None
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{"); end = text.rfind("}")
        if start == -1 or end == -1:
            logger.error(f"❌ JSON topilmadi: {text}")
            return None
        data = json.loads(text[start:end + 1])
        logger.info(f"✅ AI natijasi: {data}")
        return data
    except Exception as e:
        logger.error(f"❌ AI xatosi: {e}")
        return None

# ============================================================
# SEND TO TELEGRAM
# ============================================================
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

@flask_app.route('/send-feedback', methods=['POST'])
def send_feedback():
    try:
        if 'photo' not in request.files:
            return jsonify({'ok': False, 'description': 'Photo required!'}), 400
        photo = request.files['photo']
        if photo.filename == '':
            return jsonify({'ok': False, 'description': 'No file'}), 400
        photo_bytes = photo.read()
        if len(photo_bytes) > 5 * 1024 * 1024:
            return jsonify({'ok': False, 'description': 'Too large'}), 400
        frontend_caption = request.form.get('caption', '')
        ai_data = analyze_with_ai(photo_bytes, photo.mimetype or 'image/jpeg')
        if ai_data:
            pid = str(ai_data.get('player_id') or '')
            hidden = hide_id(pid) if pid else 'Unknown'
            classic = ai_data.get('classic_rank') or 'Unknown'
            ultimate = ai_data.get('ultimate_rank') or 'Unknown'
            kills = ai_data.get('kills') or '0'
            owner_line = frontend_caption.split('\n')[0] or '👤 OWNER: Unknown'
            owner = owner_line.replace('👤 OWNER: ', '').strip()
            now = datetime.now(TZ_TASHKENT)
            time_str = now.strftime('%H:%M  %d.%m.%Y')
            final_caption = (
                f"👤 OWNER: {owner}\n"
                f"🎮 Player ID: {hidden}\n"
                f"🏆 CLASSIC RANK: {classic}\n"
                f"🏆 ULTIMATE ROYALE RANK: {ultimate}\n"
                f"🕒 TIME: {time_str}\n"
                f"💀 KILL: {kills}\n\n"
                f"👤 OWNER: {OWNER_FIXED} ✅"
            )
        else:
            if not frontend_caption:
                return jsonify({'ok': False, 'description': 'Caption required!'}), 400
            final_caption = frontend_caption
        tg_res = send_to_telegram(photo_bytes, final_caption, photo.mimetype or 'image/jpeg')
        return jsonify({
            'ok': tg_res.get('ok', False),
            'description': tg_res.get('description'),
            'ai_data': ai_data
        }), 200 if tg_res.get('ok') else 500
    except Exception as e:
        logger.error(f"❌ Web error: {e}")
        return jsonify({'ok': False, 'description': str(e)}), 500

def run_flask():
    flask_app.run(
        host='0.0.0.0',
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )

# ============================================================
# TELEGRAM BOT
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if update.effective_chat.type == 'private' and is_banned(u.id):
        await update.message.reply_text(
            "🚫 <b>You have been banned from using this bot.</b>\n\n"
            f"Contact: {OWNER_FIXED}",
            parse_mode='HTML'
        )
        return
    save_user(u.id, u.username, u.first_name)
    context.user_data.clear()
    kb = [
        [InlineKeyboardButton("🏆 RANK STATISTICA", callback_data="rank_start")],
        [InlineKeyboardButton("🌐 WebApp", web_app={"url": f"https://tommy-backend.onrender.com"})],
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
    ranks = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Crown",
             "Ace", "Ace Master", "Ace Dominator", "Conqueror"]
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
        save_post(user.id,
                  context.user_data.get('player_id', ''),
                  context.user_data.get('classic_rank', ''),
                  context.user_data.get('ultimate_rank', ''),
                  context.user_data.get('kills', ''))
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
    await q.message.reply_text(f"Contact: {OWNER_FIXED}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['broadcast_mode'] = False
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# ============================================================
# ADMIN
# ============================================================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return
    text = (
        f"📊 <b>BOT STATISTICS</b>\n\n"
        f"👥 Total users: <b>{get_users_count()}</b>\n"
        f"🆕 Today joined: <b>{get_today_users_count()}</b>\n"
        f"📸 Total posts: <b>{get_posts_count()}</b>\n"
        f"🚫 Banned: <b>{len(get_banned_users())}</b>\n"
        f"🕒 Time: {datetime.now(TZ_TASHKENT).strftime('%H:%M %d.%m.%Y')}\n\n"
    )
    users = get_all_users(limit=10)
    if users:
        text += "<b>👤 Last 10 users:</b>\n"
        for uid, un, fn, ja in users:
            name = f"@{un}" if un else (fn if fn else "User")
            text += f"• {name} — {ja}\n"
    posts = get_recent_posts(limit=5)
    if posts:
        text += "\n<b>📸 Last 5 posts:</b>\n"
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
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i + 4000], parse_mode='HTML')

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!")
        return
    context.user_data['broadcast_mode'] = True
    await update.message.reply_text(
        "📢 <b>BROADCAST MODE</b>\n\nSend message.\nUse /cancel to abort.",
        parse_mode='HTML'
    )

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('broadcast_mode'): return
    if update.effective_user.id != ADMIN_ID: return
    text = update.message.text
    if not text: return
    context.user_data['broadcast_mode'] = False
    users = get_all_users(limit=1000)
    total = len(users); sent = 0; failed = 0
    progress = await update.message.reply_text(f"📤 Sending... 0/{total}")
    for idx, (uid, _, _, _) in enumerate(users, 1):
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except Exception:
            failed += 1
        if idx % 10 == 0 or idx == total:
            try: await progress.edit_text(f"📤 Sending... {idx}/{total}")
            except Exception: pass
    await progress.edit_text(
        f"✅ <b>Done!</b>\n✔️ Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
        parse_mode='HTML'
    )

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!"); return
    if not context.args:
        await update.message.reply_text("Usage: <code>/ban USER_ID</code>", parse_mode='HTML'); return
    try: uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID"); return
    if uid == ADMIN_ID:
        await update.message.reply_text("❌ You cannot ban yourself!"); return
    ban_user(uid)
    await update.message.reply_text(f"✅ User <code>{uid}</code> banned.", parse_mode='HTML')

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!"); return
    if not context.args:
        await update.message.reply_text("Usage: <code>/unban USER_ID</code>", parse_mode='HTML'); return
    try: uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID"); return
    unban_user(uid)
    await update.message.reply_text(f"✅ User <code>{uid}</code> unbanned.", parse_mode='HTML')

async def banned_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin!"); return
    banned = get_banned_users()
    if not banned:
        await update.message.reply_text("✅ No banned users."); return
    text = f"🚫 <b>BANNED USERS ({len(banned)})</b>\n\n"
    for uid, when in banned:
        text += f"• <code>{uid}</code> — {when}\n"
    await update.message.reply_text(text, parse_mode='HTML')

# ============================================================
# GROUP ADMIN COMMANDS
# ============================================================
async def is_group_admin(update, context):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ('group', 'supergroup'): return False
    try:
        member = await chat.get_member(user.id)
        return member.status in ('administrator', 'creator')
    except Exception:
        return False

async def check_group_admin(update, context):
    if not await is_group_admin(update, context):
        await update.message.reply_text(
            "🚫 <b>This command is only for group admins.</b>",
            parse_mode='HTML'
        )
        return False
    return True

async def setup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ('group', 'supergroup'):
        await update.message.reply_text("❌ Only in groups."); return
    if not await check_group_admin(update, context): return
    await setup_group_commands(context.application, chat.id)
    await update.message.reply_text(
        "✅ <b>Command menu set!</b>\n\n"
        "• Admins see: /mute, /unmute, /clear\n"
        "• Members see: /start",
        parse_mode='HTML'
    )

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "🔇 Reply to a user's message with:\n"
            "<code>/mute 5m</code> — 5 min\n"
            "<code>/mute 2h</code> — 2 hours\n"
            "<code>/mute 1d</code> — 1 day\n"
            "<code>/mute 1w</code> — 1 week\n"
            "<code>/mute</code> — 1 hour",
            parse_mode='HTML'
        )
        return
    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("❌ Cannot mute yourself."); return
    if target.id == context.bot.id:
        await update.message.reply_text("❌ Cannot mute myself."); return
    try:
        tm = await chat.get_member(target.id)
        if tm.status in ('administrator', 'creator'):
            await update.message.reply_text("❌ Cannot mute admins."); return
    except Exception:
        pass
    if context.args:
        duration = parse_duration(context.args[0])
        if not duration:
            await update.message.reply_text("❌ Invalid. Examples: 30s, 5m, 2h, 1d, 1w", parse_mode='HTML')
            return
    else:
        duration = timedelta(hours=1)
    if duration > timedelta(days=366):
        duration = timedelta(days=366)
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id, user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now(timezone.utc) + duration
        )
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(
            f"🔇 <b>{name}</b> muted for <b>{human_duration(duration)}</b>.\n👮 {user.mention_html()}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: <code>{e}</code>", parse_mode='HTML')

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("🔊 Reply to a message with <code>/unmute</code>", parse_mode='HTML')
        return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id, user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_send_polls=True, can_invite_users=True
            )
        )
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(
            f"🔊 <b>{name}</b> unmuted.\n👮 {user.mention_html()}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: <code>{e}</code>", parse_mode='HTML')

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    end_id = update.message.message_id
    if update.message.reply_to_message:
        start_id = update.message.reply_to_message.message_id
    else:
        start_id = max(1, end_id - 50)
    status = await update.message.reply_text("🗑️ Clearing...")
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
        text=f"✅ <b>Cleared!</b>\n✔️ {deleted}\n❌ {failed}\n\n<i>Only &lt;48h messages.</i>",
        parse_mode='HTML'
    )
    await asyncio.sleep(5)
    try: await report.delete()
    except Exception: pass

# ============================================================
# BOT ADDED TO GROUP
# ============================================================
async def on_bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mcm = update.my_chat_member
    if not mcm: return
    chat = mcm.chat
    new_status = mcm.new_chat_member.status
    if chat.type in ('group', 'supergroup'):
        if new_status in ('member', 'administrator'):
            logger.info(f"Bot added to group: {chat.title} ({chat.id})")
            await setup_group_commands(context.application, chat.id)
        elif new_status in ('left', 'kicked'):
            logger.info(f"Bot removed from group: {chat.title}")
            try:
                await context.bot.delete_my_commands(
                    scope=BotCommandScopeChatAdministrators(chat_id=chat.id))
                await context.bot.delete_my_commands(
                    scope=BotCommandScopeChat(chat_id=chat.id))
            except Exception:
                pass

# ============================================================
# COMMAND MENU SETUP
# ============================================================
async def setup_private_commands(application):
    try:
        await application.bot.set_my_commands(
            PRIVATE_COMMANDS,
            scope=BotCommandScopeAllPrivateChats()
        )
        logger.info("✅ Private commands set")
    except Exception as e:
        logger.error(f"❌ Private commands error: {e}")

async def setup_group_commands(application, chat_id):
    try:
        await application.bot.set_my_commands(
            GROUP_ADMIN_COMMANDS,
            scope=BotCommandScopeChatAdministrators(chat_id=chat_id)
        )
        await application.bot.set_my_commands(
            GROUP_PUBLIC_COMMANDS,
            scope=BotCommandScopeChat(chat_id=chat_id)
        )
        logger.info(f"✅ Group commands set for chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ Group commands error for {chat_id}: {e}")

async def post_init(application):
    await setup_private_commands(application)
    logger.info("✅ post_init done")

# ============================================================
# START BOT (MAIN THREAD)
# ============================================================
def start_bot():
    logger.info("🤖 Bot starting on MAIN thread...")
    try:
        req = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=30.0, read_timeout=30.0,
            write_timeout=30.0, pool_timeout=30.0
        )
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .request(req)
            .post_init(post_init)
            .build()
        )
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
        application.add_handler(CommandHandler("admin", admin_stats))
        application.add_handler(CommandHandler("stats", admin_stats))
        application.add_handler(CommandHandler("users", users_list))
        application.add_handler(CommandHandler("broadcast", broadcast_cmd))
        application.add_handler(CommandHandler("ban", ban_cmd))
        application.add_handler(CommandHandler("unban", unban_cmd))
        application.add_handler(CommandHandler("banned", banned_list_cmd))
        application.add_handler(CommandHandler("setup", setup_cmd))
        application.add_handler(CommandHandler("mute", mute_cmd))
        application.add_handler(CommandHandler("unmute", unmute_cmd))
        application.add_handler(CommandHandler("clear", clear_cmd))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.ChatType.PRIVATE,
            handle_broadcast_message
        ))
        application.add_handler(ChatMemberHandler(
            on_bot_added_to_group,
            ChatMemberHandler.MY_CHAT_MEMBER
        ))
        logger.info("✅ All handlers registered")
        logger.info("✅ Bot starting polling...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

# ============================================================
# MAIN
# ============================================================
def main():
    init_db()
    logger.info("=" * 50)
    logger.info("🚀 TOMMY BOT STARTING...")
    logger.info("=" * 50)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"🌐 Flask server running on port {PORT} (background thread)")

    logger.info("🤖 Starting Telegram bot on MAIN thread...")
    start_bot()

if __name__ == "__main__":
    main()
