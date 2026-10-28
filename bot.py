import os
import logging
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web

# Render'dagi Environment Variables'dan tokenni oladi
TOKEN = os.environ.get("TOKEN", "SIZNING_TOKENINGIZNI_SHU_YERGA_YOZING")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- BOT QISMI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 Termux Asoslari", callback_data='termux')],
        [InlineKeyboardButton("🐍 Python va Termux", callback_data='python')],
        [InlineKeyboardButton("📂 MT Manager bilan ishlash", callback_data='mtmanager')],
        [InlineKeyboardButton("☕ Java o'rnatish", callback_data='java')],
        [InlineKeyboardButton("🌙 Lua bilan ishlash", callback_data='lua')],
        [InlineKeyboardButton("🤖 Termux uchun Bot yasash", callback_data='bot_yasash')],
        [InlineKeyboardButton("📚 To'liq Qo'llanma (Web)", url="https://tommy-backend-2.onrender.com/tutorial")] # O'zingizning Render havolangizni qo'ying
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Assalomu alaykum! Men Termux va Dasturlash bo'yicha to'liq qo'llanma botiman.\n"
        "Kerakli bo'limni tanlang:", 
        reply_markup=reply_markup
    )

async def button_tap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'termux':
        text = ("📱 **Termux Asoslari**\n\n"
                "Termux — Android uchun Linux muhiti.\n"
                "1. O'rnatish: F-Droid yoki GitHub'dan yuklang.\n"
                "2. Xotiraga ulanish: `termux-setup-storage`\n"
                "3. Yangilash: `pkg update && pkg upgrade`\n"
                "4. Paket o'rnatish: `pkg install <nom>`\n"
                "5. Matn muharriri: `nano` yoki `vim`")
    elif query.data == 'python':
        text = ("🐍 **Python va Termux**\n\n"
                "1. O'rnatish: `pkg install python`\n"
                "2. Kod yozish: `nano test.py`\n"
                "3. Kodni ishga tushirish: `python test.py`\n"
                "4. Kutubxona o'rnatish: `pip install <nom>` (masalan: `pip install requests`)\n\n"
                "💡 *Maslahat:* Python kodini yozishda xatolik bo'lsa, `pkg install clang` o'rnatib ko'ring.")
    elif query.data == 'mtmanager':
        text = ("📂 **MT Manager bilan Termux integratsiyasi**\n\n"
                "Termux fayllarini MT Managerda ko'rish uchun:\n"
                "1. Termuxda `termux-setup-storage` buyrug'ini bering va ruxsat bering.\n"
                "2. MT Managerda chap menyudan 'Add local storage' ni bosing.\n"
                "3. `/storage/emulated/0` manzilini tanlang.\n"
                "4. Endi Termuxning ichki fayllari (`/data/data/com.termux/files/home`) MT Manager orqali ko'rinadi.")
    elif query.data == 'java':
        text = ("☕ **Java o'rnatish**\n\n"
                "Termuxda Java (OpenJDK) o'rnatish:\n"
                "`pkg install openjdk-17`\n\n"
                "Tekshirish uchun:\n"
                "`java -version`\n\n"
                "💡 *Eslatma:* Agar xatolik bersa, `pkg install openjdk-21` ni sinab ko'ring.")
    elif query.data == 'lua':
        text = ("🌙 **Lua bilan ishlash**\n\n"
                "Lua — yengil dasturlash tili.\n"
                "1. O'rnatish: `pkg install lua`\n"
                "2. Kod yozish: `nano test.lua`\n"
                "3. Ishga tushirish: `lua test.lua`\n\n"
                "Lua odatda o'yinlar va kichik skriptlar uchun ishlatiladi.")
    elif query.data == 'bot_yasash':
        text = ("🤖 **Termuxda Telegram Bot yasash**\n\n"
                "1. Python o'rnating: `pkg install python`\n"
                "2. Kutubxona: `pip install python-telegram-bot`\n"
                "3. BotFather'dan token oling.\n"
                "4. Kod yozing va `python bot.py` bilan ishga tushiring.\n\n"
                "💡 *Maslahat:* Bot 24/7 ishlashi uchun Render.com kabi bepul serverlardan foydalaning yoki `termux-wake-lock` buyrug'ini bering.")
    
    await query.edit_message_text(text=text, parse_mode='Markdown')

# --- VEB SERVER QISMI ---

async def handle_index(request):
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Bot ishlayapti! (index.html topilmadi)")

async def handle_tutorial(request):
    try:
        with open('tutorial.html', 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Tutorial sahifasi topilmadi.")

def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/tutorial', handle_tutorial)
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host='0.0.0.0', port=port)

# --- ASOSIY ISHGA TUSHIRISH ---

def main():
    threading.Thread(target=run_web_server, daemon=True).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_tap))

    print("Bot muvaffaqiyatli ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
