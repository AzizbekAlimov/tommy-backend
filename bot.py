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
        [InlineKeyboardButton("📱 Termux haqida", callback_data='termux')],
        [InlineKeyboardButton("🐍 Python haqida", callback_data='python')],
        [InlineKeyboardButton("📂 MT Manager haqida", callback_data='mtmanager')],
        [InlineKeyboardButton("☕ Java haqida", callback_data='java')],
        [InlineKeyboardButton("🚀 GitHub va Render", callback_data='deploy')]
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
        text = "📱 **Termux** - bu Android uchun Linux muhiti.\n\nO'rnatish: F-Droid'dan yuklang.\nAsosiy buyruqlar:\n`pkg update`\n`pkg install python`\n`termux-setup-storage`"
    elif query.data == 'python':
        text = "🐍 **Python** - eng oson va ommabop dasturlash tili.\n\nTermuxda o'rnatish:\n`pkg install python`\nKutubxona o'rnatish:\n`pip install python-telegram-bot`"
    elif query.data == 'mtmanager':
        text = "📂 **MT Manager** - fayl boshqaruvchisi.\n\nTermux fayllarini ko'rish uchun:\n1. MT Managerda 'Add local storage' ni bosing.\n2. Termux papkasini tanlang.\n3. 'Use this folder' tugmasini bosing."
    elif query.data == 'java':
        text = "☕ **Java** - Termuxda o'rnatish:\n`pkg install openjdk-17`\nTekshirish:\n`java -version`"
    elif query.data == 'deploy':
        text = "🚀 **Deploy (Joylashtirish):**\n\n1. Kodni GitHub'ga yuklang.\n2. Render.com ga kiring.\n3. 'New Web Service' tanlang.\n4. GitHub repongizni ulang.\n5. Start Command: `python bot.py`"
    
    await query.edit_message_text(text=text, parse_mode='Markdown')

# --- VEB SERVER QISMI (Render uxlab qolmasligi uchun) ---

async def handle_index(request):
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return web.Response(text=html_content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Bot ishlayapti!")

def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_index)
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host='0.0.0.0', port=port)

# --- ASOSIY ISHGA TUSHIRISH ---

def main():
    # Veb serverni alohida oqimda ishga tushirish
    threading.Thread(target=run_web_server, daemon=True).start()

    # Botni ishga tushirish
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_tap))

    print("Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
