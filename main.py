import os
import time
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, RateLimitError

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
    await message.answer("Instagram obunachilarini tozalash uchun pastdagi tugmani bosing.", reply_markup=kb)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    if BOT_TOKEN:
        await bot.set_webhook(f"{WEBHOOK_HOST}/webhook")

# ==========================================
# 3. WEBAPP VA API QISMI
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Xatolik: index.html topilmadi!"

@app.get("/get_id.py", response_class=PlainTextResponse)
async def serve_python_script():
    # Termux uchun yangilangan versiya
    script = """from instagrapi import Client
import sys

print("\\n--- Instagram Session ID Olish ---")
u = input("Username: ")
p = input("Parol: ")

c = Client()
c.set_device({"app_version": "269.0.0.18.75"})

try:
    c.login(u, p)
except Exception as e:
    if "two_factor" in str(e).lower():
        print("\\n[!] 2FA talab qilinmoqda.")
        code = input("2FA kodini kiriting: ")
        try:
            c.login(u, p, verification_code=code)
        except Exception as e2:
            print("\\n❌ Xatolik:", e2)
            sys.exit()
    else:
        print("\\n❌ Kirishda xatolik:", e)
        sys.exit()

print("\\n✅ Muvaffaqiyatli kirdingiz!")
print("Sizning Session ID'ingiz (nusxalab oling):\\n")
print(c.sessionid)
print("\\n")
"""
    return script

class UnfollowRequest(BaseModel):
    session_id: str
    count: int

def process_unfollow(session_id: str, count: int):
    try:
        cl = Client()
        cl.login_by_sessionid(session_id)
        print("Instagram'ga ulandi. Obunalar olinmoqda...")
        
        following = cl.user_following(cl.user_id)
        unfollowed_count = 0

        for user_id in list(following.keys()):
            if unfollowed_count >= count:
                break
            try:
                cl.user_unfollow(user_id)
                unfollowed_count += 1
                print(f"O'chirildi: {unfollowed_count}/{count}")
                
                # Vaqt 3 soniyadan 1.5 soniyaga tushirildi (1000 ta ~ 25 daqiqa)
                time.sleep(1.5) 
                
            except RateLimitError:
                print("⚠️ Instagram blokladi! 15 daqiqa kutish...")
                time.sleep(900) # 15 daqiqa kutish
            except Exception as e:
                print(f"Xatolik: {e}")
                continue
                
        print(f"Jami {unfollowed_count} ta obuna bekor qilindi.")
    except LoginRequired:
        print("Sessiya eskirgan yoki xato.")
    except Exception as e:
        print(f"Ulanishda xatolik: {e}")

@app.post("/api/unfollow")
async def start_unfollow(request: UnfollowRequest, background_tasks: BackgroundTasks):
    # Maksimal limit 1000 qilib qat'iy belgilandi
    if request.count < 1 or request.count > 1000:
        raise HTTPException(status_code=400, detail="Xavfsizlik uchun bir martada maksimal 1000 ta odamni o'chirish mumkin!")
    if not request.session_id or len(request.session_id) < 20:
        raise HTTPException(status_code=400, detail="Session ID noto'g'ri kiritilgan!")

    try:
        test_cl = Client()
        test_cl.login_by_sessionid(request.session_id)
        test_cl.get_timeline_feed() 
    except Exception as e:
        raise HTTPException(status_code=401, detail="Session ID xato yoki eskirgan!")

    background_tasks.add_task(process_unfollow, request.session_id, request.count)
    return {"status": "success", "message": f"{request.count} ta obunani bekor qilish boshlandi."}
