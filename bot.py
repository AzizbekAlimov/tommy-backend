import os
import logging
import threading
import http.server
import socketserver
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# Render'dagi Environment Variables'dan yangi tokenni oladi
TOKEN = os.environ.get("TOKEN", "8872275906:AAEoOfscxqWv1ckizOb2z9P7T6MgPGfY6ng")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Xatolik yuz berdi:", exc_info=context.error)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = (
        "👋 **Assalomu alaykum!**\n\n"
        "Men **Termux va Dasturlash** bo'yicha yordamchi botman.\n\n"
        "🤖 **Men nima qila olaman?**\n"
        "📱 **Termux** - Linux muhitini sozlash\n"
        "🐍 **Python** - Dasturlash va bot yasash\n"
        "📂 **MT Manager** - Fayllar bilan ishlash\n"
        "☕ **Java** - Dasturlash muhiti\n\n"
        "📚 Barcha darsliklar bitta qulay **Web sahifada** jamlangan. "
        "Quyidagi tugma orqali to'liq qo'llanmani ochishingiz mumkin:"
    )
    
    # DIQQAT: Render'dan olgan havolangizni shu yerga qo'ying
    keyboard = [
        [InlineKeyboardButton("📚 Termux Tutorial (Web)", url="https://sizning-havolangiz.onrender.com/tutorial")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')

# --- VEB SERVER QISMI (Python'ning o'zidagi server) ---
def run_web_server():
    PORT = int(os.environ.get("PORT", 8080))
    
    class MyHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            # Agar /tutorial so'ralsa, tutorial.html ni ko'rsatadi
            if self.path == '/tutorial' or self.path == '/tutorial/':
                self.path = '/tutorial.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    # Serverni ishga tushirish
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Veb-server {PORT}-portda ishga tushdi!")
        httpd.serve_forever()

# --- ASOSIY ISHGA TUSHIRISH ---
def main():
    # Veb serverni orqa fonda ishga tushirish
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # Botni ishga tushirish
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_error_handler(error_handler)
    
    print("Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
