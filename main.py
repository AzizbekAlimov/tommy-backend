import os
import time
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, UserNotFound

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
    # Versiya xatosini tuzatuvchi yangilangan skript
    script = """from instagrapi import Client
import sys

print("\\n--- Instagram Session ID Olish ---")
u = input("Username: ")
p = input("Parol: ")

c = Client()
# Instagram versiyasini yangilash (xatolikni oldini oladi)
c.set_device({"app_version": "269.0.0.18.75"})

try:
    c.login(u, p)
except Exception as e:
    if "two_factor" in str(e).lower():
        print("\\n[!] 2FA (Ikki bosqichli himoya) talab qilinmoqda.")
        code = input("2FA kodini kiriting: ")
        try:
            c.login(u, p, verification_code=code)
        except Exception as e2:
            print("\\n❌ Xatolik:", e2)
            sys.exit()
    else:
        print("\\n❌ Kirishda xatolik:", e)
        print("Maslahat: Instagram versiyasi xatosi bo'lsa, 10 daqiqadan so'ng qayta urinib ko'ring.")
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

# --- Session ID ni tekshirish va Orqa fonda Unfollow qilish ---
def process_unfollow(session_id: str, count: int):
    try:
        cl = Client()
        # 1. Avval Session ID to'g'riligini tekshiramiz
        cl.login_by_sessionid(session_id)
        user_id = cl.user_id # Agar ID xato bo'lsa, shu yerda xato beradi
        
        following = cl.user_following(user_id)
        unfollowed_count = 0

        for user_id in list(following.keys()):
            if unfollowed_count >= count:
                break
            try:
                cl.user_unfollow(user_id)
                unfollowed_count += 1
                time.sleep(2) # 2 soniya xavfsiz kutish
            except Exception as e:
                print(f"Bitta odamni unfollow qilishda xato: {e}")
                continue
        print(f"Jami {unfollowed_count} ta obuna bekor qilindi.")
    except LoginRequired:
        print("Sessiya eskirgan yoki noto'g'ri.")
    except Exception as e:
        print(f"Ulanishda xatolik: {e}")

@app.post("/api/unfollow")
async def start_unfollow(request: UnfollowRequest, background_tasks: BackgroundTasks):
    if request.count < 1 or request.count > 10000:
        raise HTTPException(status_code=400, detail="Xato! Son 1 dan 10,000 gacha bo'lishi kerak.")
    if not request.session_id or len(request.session_id) < 20:
        raise HTTPException(status_code=400, detail="Session ID juda qisqa yoki noto'g'ri kiritilgan!")

    # Session ID ni API qabul qilishdan oldin tekshirib ko'ramiz
    try:
        test_cl = Client()
        test_cl.login_by_sessionid(request.session_id)
        test_cl.get_timeline_feed() # Haqiqatan ham ishlayaptimi tekshirish
    except Exception as e:
        raise HTTPException(status_code=401, detail="Session ID xato yoki eskirgan. Iltimos, qaytadan oling!")

    # Agar ID to'g'ri bo'lsa, orqa fonga yuboramiz
    background_tasks.add_task(process_unfollow, request.session_id, request.count)
    return {"status": "success", "message": f"{request.count} ta obunani bekor qilish boshlandi."}
