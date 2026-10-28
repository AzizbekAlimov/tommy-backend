import os
import logging
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from aiohttp import web

# Render'dagi Environment Variables'dan tokenni oladi
TOKEN = os.environ.get("TOKEN", "SIZNING_TOKENINGIZNI_SHU_YERGA_YOZING")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- BOT QISMI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Botning o'zi haqida to'liq ma'lumot beruvchi matn
    info_text = (
        "👋 **Assalomu alaykum!**\n\n"
        "Men **Termux va Dasturlash** bo'yicha yordamchi botman.\n\n"
        "🤖 **Men nima qila olaman?**\n"
        "Men sizga quyidagi mavzularni 100% o'rgataman:\n"
        "📱 **Termux** - Androidda Linux muhitini sozlash\n"
        "🐍 **Python** - Dasturlash tili va bot yasash\n"
        "📂 **MT Manager** - Termux fayllari bilan ishlash\n"
        "☕ **Java** - Dasturlash muhitini o'rnatish\n\n"
        "📚 Barcha darsliklar bitta qulay **Web sahifada** jamlangan. "
        "Quyidagi tugma orqali to'liq qo'llanmani ochishingiz mumkin:"
    )
    
    # Faqatgina HTML darslikka olib o'tuvchi bitta tugma
    keyboard = [
        [InlineKeyboardButton("📚 Termux Tutorial (Web)", url="https://termux-bot-89xq.onrender.com/tutorial")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        info_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# --- VEB SERVER QISMI (HTML faylni ochish uchun) ---

async def handle_index(request):
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Bot ishlayapti!")

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
    
    # Faqat /start buyrug'ini tinglaydi
    application.add_handler(CommandHandler("start", start))

    print("Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
