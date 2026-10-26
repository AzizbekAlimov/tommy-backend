import os
import time
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

# Aiogram (Telegram Bot)
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# ==========================================
# 1. SOZLAMALAR
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN") 
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST") 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# ==========================================
# 2. TELEGRAM BOT QISMI
# ==========================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 INSTAGRAM Ochish", web_app=WebAppInfo(url=WEBHOOK_HOST))]
    ])
    await message.answer(
        f"Salom, {message.from_user.first_name}!\n\n"
        "Instagram obunachilarini tozalash uchun pastdagi tugmani bosing.",
        reply_markup=kb
    )

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    if BOT_TOKEN:
        webhook_url = f"{WEBHOOK_HOST}/webhook"
        await bot.set_webhook(webhook_url)
        print(f"Webhook o'rnatildi: {webhook_url}")

# ==========================================
# 3. WEBAPP VA API QISMI
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Xatolik: index.html fayli topilmadi!"

# --- TERMUX UCHUN SKRIPTNI TARQATISH (2FA bilan) ---
@app.get("/get_id.py", response_class=PlainTextResponse)
async def serve_python_script():
    script = """from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired
import sys

print("\\n--- Instagram Session ID Olish ---")
u = input("Username: ")
p = input("Parol: ")

c = Client()
try:
    c.login(u, p)
except TwoFactorRequired:
    print("\\n[!] Akkauntda 2FA (ikki bosqichli himoya) yoqilgan.")
    code = input("2FA kodini kiriting (SMS yoki Authenticator): ")
    try:
        c.login(u, p, verification_code=code)
    except Exception as e2:
        print("\\n❌ 2FA kodida xatolik:", e2)
        sys.exit()
except Exception as e:
    print("\\n❌ Kirishda xatolik:", e)
    sys.exit()

print("\\n✅ Muvaffaqiyatli kirdingiz!")
print("Sizning Session ID'ingiz (nusxalab oling):\\n")
print(c.sessionid)
print("\\n")
"""
    return script

# --- UNFOLLOW QILISH API ---
class UnfollowRequest(BaseModel):
    session_id: str
    count: int

def process_unfollow(session_id: str, count: int):
    try:
        cl = Client()
        cl.login_by_sessionid(session_id)
        following = cl.user_following(cl.user_id)
        unfollowed_count = 0

        for user_id in list(following.keys()):
            if unfollowed_count >= count:
                break
            try:
                cl.user_unfollow(user_id)
                unfollowed_count += 1
                time.sleep(3)
            except Exception as e:
                print(f"Xatolik: {e}")
                continue
        print(f"Jami {unfollowed_count} ta obuna bekor qilindi.")
    except LoginRequired:
        print("Sessiya eskirgan.")
    except Exception as e:
        print(f"Ulanishda xatolik: {e}")

@app.post("/api/unfollow")
async def start_unfollow(request: UnfollowRequest, background_tasks: BackgroundTasks):
    if request.count < 1 or request.count > 10000:
        raise HTTPException(status_code=400, detail="Xato! Son 1 dan 10,000 gacha bo'lishi kerak.")
    if not request.session_id:
        raise HTTPException(status_code=400, detail="Session ID kiritilmadi!")

    background_tasks.add_task(process_unfollow, request.session_id, request.count)
    return {"status": "success", "message": f"{request.count} ta obunani bekor qilish boshlandi."}
