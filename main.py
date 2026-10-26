import os
import time
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadPassword, TwoFactorRequired

# Aiogram (Telegram Bot) libraries
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# ==========================================
# 1. SETTINGS (Read from Render Environment)
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN") 
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST") 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# ==========================================
# 2. TELEGRAM BOT SECTION
# ==========================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    """Handles the /start command from users"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📸 OPEN INSTAGRAM", 
            web_app=WebAppInfo(url=WEBHOOK_HOST)
        )]
    ])
    
    await message.answer(
        f"Hello, {message.from_user.first_name}!\n\n"
        "Click the button below to clean up your Instagram following.",
        reply_markup=kb
    )

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive incoming messages from Telegram"""
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    """Set Telegram Webhook when Render starts"""
    if BOT_TOKEN:
        webhook_url = f"{WEBHOOK_HOST}/webhook"
        await bot.set_webhook(webhook_url)
        print(f"Webhook successfully set to: {webhook_url}")

# ==========================================
# 3. WEBAPP AND API SECTION
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    """Serve the HTML file"""
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Error: index.html file not found!"

# --- Models (Data coming from Frontend) ---
class LoginRequest(BaseModel):
    username: str
    password: str

class UnfollowRequest(BaseModel):
    session_id: str
    count: int

# --- 1-API: Login to Instagram via Password ---
@app.post("/api/login")
async def login_instagram(request: LoginRequest):
    """Validates the username and password and gets the session"""
    try:
        cl = Client()
        # Attempt to log in to Instagram
        cl.login(request.username, request.password)
        
        # If successful, get the sessionid
        session_id = cl.sessionid
        
        return {
            "status": "success", 
            "session_id": session_id, 
            "message": "Successfully logged into the account!"
        }
    except BadPassword:
        raise HTTPException(status_code=400, detail="Incorrect password or username!")
    except TwoFactorRequired:
        raise HTTPException(status_code=400, detail="Two-factor authentication (2FA) is enabled on your account. Please disable it temporarily.")
    except Exception as e:
        # If Instagram blocks the login attempt or throws another error
        print(f"Login error: {e}")
        raise HTTPException(status_code=400, detail="Login error. Instagram might have blocked the login attempt.")

# --- 2-API: Unfollow in the background ---
def process_unfollow(session_id: str, count: int):
    """Function that runs in the background and unfollows users"""
    try:
        cl = Client()
        # Reconnect to Instagram using the obtained session_id
        cl.login_by_sessionid(session_id)
        
        # Get following list
        following = cl.user_following(cl.user_id)
        unfollowed_count = 0

        for user_id in list(following.keys()):
            if unfollowed_count >= count:
                break
            try:
                cl.user_unfollow(user_id)
                unfollowed_count += 1
                time.sleep(3) # Wait 3 seconds for safety
            except Exception as e:
                print(f"Error unfollowing a user: {e}")
                continue
                
        print(f"Total {unfollowed_count} accounts unfollowed.")
    except LoginRequired:
        print("Session expired. Need to log in again.")
    except Exception as e:
        print(f"Error during unfollow process: {e}")

@app.post("/api/unfollow")
async def start_unfollow(request: UnfollowRequest, background_tasks: BackgroundTasks):
    """API to start the unfollow process"""
    if request.count < 1 or request.count > 10000:
        raise HTTPException(status_code=400, detail="Error! Number must be between 1 and 10,000.")
    if not request.session_id:
        raise HTTPException(status_code=400, detail="Session not found, please log in again!")

    # Send the process to background (to prevent API from freezing)
    background_tasks.add_task(process_unfollow, request.session_id, request.count)
    
    return {"status": "success", "message": f"Process to unfollow {request.count} accounts has started."}
