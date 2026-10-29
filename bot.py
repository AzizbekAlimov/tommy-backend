import os
import logging
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from aiohttp import web

# Tokenni Render'dagi Environment Variables'dan oladi
TOKEN = os.environ.get("TOKEN", "SIZNING_TOKENINGIZNI_SHU_YERGA_YOZING")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Xatolik yuz berdi:", exc_info=context.error)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bot faqat nima qila olishi haqida ma'lumot beradi
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
    
    # DIQQAT: Bu yerga o'zingizning Render havolangizni qo'ying! Oxirida /tutorial bo'lishi shart.
    keyboard = [
        [InlineKeyboardButton("📚 Termux Tutorial (Web)", url="https://loyihangiz-nomi.onrender.com/tutorial")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')

# --- VEB SERVER QISMI (HTML faylni ochish uchun) ---
async def handle_index(request):
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Bot muvaffaqiyatli ishlayapti!")

async def handle_tutorial(request):
    try:
        with open('tutorial.html', 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Xatolik: tutorial.html topilmadi!")

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
    application.add_error_handler(error_handler)
    print("Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
