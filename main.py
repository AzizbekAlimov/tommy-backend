import os
import time
import random
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, RateLimitError, TwoFactorRequired

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import uvicorn

# ==========================================
# 1. SOZLAMALAR (Render Environment'dan o'qiydi)
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
        "Instagram obunachilarini xavfsiz va avtomatik tozalash uchun pastdagi tugmani bosing.",
        reply_markup=kb
    )

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    if BOT_TOKEN and WEBHOOK_HOST:
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

# --- TERMUX UCHUN SKRIPT (Faqat toza Session ID chiqaradi) ---
@app.get("/get_id.py", response_class=PlainTextResponse)
async def serve_python_script():
    script = """from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired
import sys

print("\\n--- Instagram Session ID Olish ---")
u = input("Instagram Username (boshida @ belgisisiz): ")
p = input("Instagram Parol: ")

c = Client()
try:
    c.login(u, p)
except TwoFactorRequired:
    print("\\n[!] Akkauntda 2FA (Ikki bosqichli himoya) yoqilgan.")
    code = input("Google Authenticator yoki SMS dan 6 xonali kodni kiriting: ")
    try:
        c.login(u, p, verification_code=code)
    except Exception as e2:
        print("\\n❌ Xatolik:", e2)
        print("Maslahat: Kodni to'g'ri kiritganingizga ishonch hosil qiling.")
        sys.exit()
except Exception as e:
    print("\\n❌ Kirishda xatolik:", e)
    sys.exit()

print("\\n✅ Muvaffaqiyatli kirdingiz!")
print("Sizning Session ID'ingiz (nusxalab oling, bu juda uzun matn):\\n")
print(c.sessionid)
print("\\n")
"""
    return script

# --- API MODELLARI ---
class UnfollowRequest(BaseModel):
    session_id: str
    count: int = Field(..., ge=1, le=1000) # Faqat 1 dan 1000 gacha qabul qiladi

# --- ASOSIY MANTIQ: ORQA FONDA ISHLAYDIGAN QISM ---
def process_unfollow(session_id: str, count: int):
    try:
        cl = Client()
        cl.login_by_sessionid(session_id)
        
        # Obunalar ro'yxatini olish
        following = cl.user_following(cl.user_id)
        unfollowed_count = 0

        for user_id in list(following.keys()):
            if unfollowed_count >= count:
                break
            try:
                cl.user_unfollow(user_id)
                unfollowed_count += 1
                print(f"O'chirildi: {unfollowed_count}/{count}")
                
                # Instagram bloklamasligi uchun tasodifiy kutish (1.2 - 2.5 soniya)
                time.sleep(random.uniform(1.2, 2.5))
                
            except RateLimitError:
                print("⚠️ Instagram vaqtincha blokladi! 15 daqiqa kutish...")
                time.sleep(900) # 15 daqiqa kutish
            except Exception as e:
                print(f"Bitta odamni o'chirishda xato: {e}")
                continue
                
        print(f"Jami {unfollowed_count} ta obuna bekor qilindi.")
    except LoginRequired:
        print("Sessiya eskirgan yoki xato.")
    except Exception as e:
        print(f"Ulanishda xatolik: {e}")

@app.post("/api/unfollow")
async def start_unfollow(request: UnfollowRequest, background_tasks: BackgroundTasks):
    
    # 1. Xavfsizlik tekshiruvi (Session ID uzunligi)
    if not request.session_id or len(request.session_id) < 20:
        raise HTTPException(status_code=400, detail="Session ID formati noto'g'ri. Iltimos, Termux orqali qaytadan oling.")

    # 2. Session ID haqiqiy ekanligini Instagram orqali tekshirish
    try:
        test_cl = Client()
        test_cl.login_by_sessionid(request.session_id)
        test_cl.get_timeline_feed() # Haqiqatan ham kira olyaptimi?
    except Exception:
        raise HTTPException(status_code=401, detail="Kiritilgan Session ID xato yoki eskirgan. Qaytadan oling!")

    # 3. Hamma narsa to'g'ri bo'lsa, orqa fonga yuboramiz
    background_tasks.add_task(process_unfollow, request.session_id, request.count)
    return {"status": "success", "message": f"{request.count} ta obunani bekor qilish boshlandi."}

# ==========================================
# 4. RENDER PORT BINDING (Status 3 xatosini oldini oladi)
# ==========================================
if __name__ == "__main__":
    # Render avtomatik beradigan portni ushlab olish
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
