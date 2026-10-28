import os
import logging
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web

# Tokenni Render'dagi Environment Variables'dan oladi
TOKEN = os.environ.get("TOKEN", "SIZNING_TOKENINGIZNI_SHU_YERGA_YOZING")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- BOT QISMI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        # BU YERGA O'ZINGIZNING RENDER HAVOLANGIZNI YOZING
        [InlineKeyboardButton("📚 Termux Tutorial (Web)", url="https://termux-bot-89xq.onrender.com/tutorial")], 
        [InlineKeyboardButton("📱 Termux haqida", callback_data='termux')],
        [InlineKeyboardButton("🐍 Python haqida", callback_data='python')],
        [InlineKeyboardButton("📂 MT Manager haqida", callback_data='mtmanager')],
        [InlineKeyboardButton("☕ Java haqida", callback_data='java')],
        [InlineKeyboardButton("🌙 Lua haqida", callback_data='lua')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Assalomu alaykum! Men Termux va Dasturlash o'quv botiman.\n"
        "Kerakli bo'limni tanlang:", 
        reply_markup=reply_markup
    )

async def button_tap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'termux':
        text = "📱 **Termux** - Android uchun Linux.\n\n`pkg update`\n`pkg install python`\n`termux-setup-storage`"
    elif query.data == 'python':
        text = "🐍 **Python**\n\nO'rnatish: `pkg install python`\nKutubxona: `pip install python-telegram-bot`"
    elif query.data == 'mtmanager':
        text = "📂 **MT Manager**\n\nTermux fayllarini ko'rish uchun MT Managerda 'Add local storage' ni bosib, Termux papkasini tanlang."
    elif query.data == 'java':
        text = "☕ **Java**\n\n`pkg install openjdk-17`\nTekshirish: `java -version`"
    elif query.data == 'lua':
        text = "🌙 **Lua**\n\n`pkg install lua`\nKod yozish: `nano test.lua`\nIshga tushirish: `lua test.lua`"
    
    await query.edit_message_text(text=text, parse_mode='Markdown')

# --- VEB SERVER QISMI (HTML fayllarni o'qiydi) ---

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
        return web.Response(text="Xatolik: tutorial.html fayli topilmadi!")

def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/tutorial', handle_tutorial)
    port = int(os.environ.get("PORT", 8080))
    print(f"Veb-server {port}-portda ishga tushdi!")
    web.run_app(app, host='0.0.0.0', port=port)

# --- ASOSIY ISHGA TUSHIRISH ---

def main():
    threading.Thread(target=run_web_server, daemon=True).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_tap))

    print("Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
