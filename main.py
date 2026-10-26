import os
import time
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from instagrapi import Client

# Aiogram (Telegram Bot) uchun kutubxonalar
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# ==========================================
# 1. SOZLAMALAR (SHU YERLARNI O'ZGARTIRING)
# ==========================================
BOT_TOKEN = "8929742650:AAEGS3uTD515ucmLdCAAP8NeiJ-hz6VfgBQ" 
# Masalan: "7123456789:AAH..."
WEBHOOK_HOST = "https://tommy-backend-1.onrender.com" # Render'dagi havolangiz

# Bot va FastAPI ob'ektlarini yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# ==========================================
# 2. TELEGRAM BOT QISMI (/start va Webhook)
# ==========================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    """Foydalanuvchi /start bosganda ishlaydigan qism"""
    
    # WebApp'ni ochuvchi tugma
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📸 INSTAGRAM Ochish", 
            web_app=WebAppInfo(url=WEBHOOK_HOST)
        )]
    ])
    
    await message.answer(
        f"Salom, {message.from_user.first_name}!\n\n"
        "Instagram obunachilarini tozalash uchun pastdagi tugmani bosing yoki chap pastdagi menyudan foydalaning.",
        reply_markup=kb
    )

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Telegram'dan kelayotgan xabarlarni qabul qilish"""
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    """Render ishga tushganda Telegram'ga Webhook o'rnatadi"""
    webhook_url = f"{WEBHOOK_HOST}/webhook"
    await bot.set_webhook(webhook_url)
    print(f"Webhook muvaffaqiyatli o'rnatildi: {webhook_url}")

# ==========================================
# 3. WEBAPP VA API QISMI (O'ZGARTIRILMAYDI)
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    """HTML faylni ochish"""
    with open("index.html", "r", encoding="utf-8") as file:
        return file.read()

class UnfollowRequest(BaseModel):
    session_id: str
    count: int

def process_unfollow(session_id: str, count: int):
    """Orqa fonda Instagram'da ishlaydigan qism"""
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
                time.sleep(2) # 2 soniya kutish
            except Exception as e:
                print(f"Xatolik: {e}")
                continue
        print(f"Jami {unfollowed_count} ta obuna bekor qilindi.")
    except Exception as e:
        print(f"Instagram'ga ulanishda xatolik: {e}")

@app.post("/api/unfollow")
async def start_unfollow(request: UnfollowRequest, background_tasks: BackgroundTasks):
    """WebApp'dagi tugma bosilganda ishlaydigan API"""
    if request.count < 1 or request.count > 10000:
        raise HTTPException(status_code=400, detail="Xato! Son 1 dan 10,000 gacha bo'lishi kerak.")
    if not request.session_id:
        raise HTTPException(status_code=400, detail="Session ID kiritilmadi!")

    background_tasks.add_task(process_unfollow, request.session_id, request.count)
    return {"status": "success", "message": f"{request.count} ta obunani bekor qilish boshlandi."}
