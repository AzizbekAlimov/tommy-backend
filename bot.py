import os
import logging
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web

# Tokenni Render'dagi Environment Variables'dan oladi
TOKEN = os.environ.get("TOKEN", "8872275906:AAEoOfscxqWv1ckizOb2z9P7T6MgPGfY6ng")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 45 TA VIDEOLAR RO'YXATI (Siz yuborgan linklar)
# ==========================================
LESSONS = {
    1: "https://t.me/termux_tutoril/3",
    2: "https://t.me/termux_tutoril/4",
    3: "https://t.me/termux_tutoril/5",
    4: "https://t.me/termux_tutoril/6",
    5: "https://t.me/termux_tutoril/7",
    6: "https://t.me/termux_tutoril/8",
    7: "https://t.me/termux_tutoril/9",
    8: "https://t.me/termux_tutoril/10",
    9: "https://t.me/termux_tutoril/11",
    10: "https://t.me/termux_tutoril/12",
    11: "https://t.me/termux_tutoril/13",
    12: "https://t.me/termux_tutoril/14",
    13: "https://t.me/termux_tutoril/15",
    14: "https://t.me/termux_tutoril/16",
    15: "https://t.me/termux_tutoril/17",
    16: "https://t.me/termux_tutoril/18",
    17: "https://t.me/termux_tutoril/19",
    18: "https://t.me/termux_tutoril/20",
    19: "https://t.me/termux_tutoril/21",
    20: "https://t.me/termux_tutoril/22",
    21: "https://t.me/termux_tutoril/23",
    22: "https://t.me/termux_tutoril/24",
    23: "https://t.me/termux_tutoril/25",
    24: "https://t.me/termux_tutoril/26",
    25: "https://t.me/termux_tutoril/27",
    26: "https://t.me/termux_tutoril/28",
    27: "https://t.me/termux_tutoril/29",
    28: "https://t.me/termux_tutoril/30",
    29: "https://t.me/termux_tutoril/31",
    30: "https://t.me/termux_tutoril/32",
    31: "https://t.me/termux_tutoril/33",
    32: "https://t.me/termux_tutoril/34",
    33: "https://t.me/termux_tutoril/35",
    34: "https://t.me/termux_tutoril/36",
    35: "https://t.me/termux_tutoril/37",
    36: "https://t.me/termux_tutoril/38",
    37: "https://t.me/termux_tutoril/39",
    38: "https://t.me/termux_tutoril/40",
    39: "https://t.me/termux_tutoril/41",
    40: "https://t.me/termux_tutoril/42",
    41: "https://t.me/termux_tutoril/43",
    42: "https://t.me/termux_tutoril/44",
    43: "https://t.me/termux_tutoril/45",
    44: "https://t.me/termux_tutoril/46",
    45: "https://t.me/termux_tutoril/47",
}

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Xatolik yuz berdi:", exc_info=context.error)

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = (
        "👋 **Assalomu alaykum!**\n\n"
        "Men **Termux va Dasturlash** bo'yicha yordamchi botman.\n\n"
        "🤖 **Men nima qila olaman?**\n"
        "Men sizga quyidagi mavzularni 100% o'rgataman:\n"
        "📱 **Termux** - Androidda Linux muhitini sozlash\n"
        "🐍 **Python** - Dasturlash tili va bot yasash\n"
        "📂 **MT Manager** - Termux fayllari bilan ishlash\n"
        "☕ **Java** - Dasturlash muhitini o'rnatish\n\n"
        "📚 **45 ta video darslik** tayyor. Ko'rish uchun pastdagi tugmani bosing:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎥 Videodarsliklarni ko'rish", callback_data="page_1")],
        [InlineKeyboardButton("📢 Kanalga o'tish", url="https://t.me/termux_tutoril")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')

# Sahifalarni yaratish funksiyasi (10 tadan)
def get_lessons_keyboard(page=1):
    keyboard = []
    items_per_page = 10
    
    start_idx = (page - 1) * items_per_page + 1
    end_idx = min(page * items_per_page, 45)
    
    # 2 tadan qilib tugma yasaymiz
    row = []
    for i in range(start_idx, end_idx + 1):
        row.append(InlineKeyboardButton(f"🎬 {i}-darslik", url=LESSONS[i]))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    # Sahifalash tugmalari
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"page_{page-1}"))
    if end_idx < 45:
        nav_row.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"page_{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    # Orqaga qaytish
    keyboard.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="back_to_start")])
    
    return InlineKeyboardMarkup(keyboard)

# Tugmalar bosilganda ishlaydigan qism
async def button_tap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("page_"):
        page = int(data.split("_")[1])
        text = f"📚 **Videodarsliklar ro'yxati**\n\nSahifa: {page} / 5\nO'zingizga kerakli darslikni tanlang:"
        await query.edit_message_text(text=text, reply_markup=get_lessons_keyboard(page), parse_mode='Markdown')
        
    elif data == "back_to_start":
        info_text = (
            "👋 **Assalomu alaykum!**\n\n"
            "Men **Termux va Dasturlash** bo'yicha yordamchi botman.\n\n"
            "🤖 **Men nima qila olaman?**\n"
            "Men sizga quyidagi mavzularni 100% o'rgataman:\n"
            "📱 **Termux** - Androidda Linux muhitini sozlash\n"
            "🐍 **Python** - Dasturlash tili va bot yasash\n"
            "📂 **MT Manager** - Termux fayllari bilan ishlash\n"
            "☕ **Java** - Dasturlash muhitini o'rnatish\n\n"
            "📚 **45 ta video darslik** tayyor. Ko'rish uchun pastdagi tugmani bosing:"
        )
        keyboard = [
            [InlineKeyboardButton("🎥 Videodarsliklarni ko'rish", callback_data="page_1")],
            [InlineKeyboardButton("📢 Kanalga o'tish", url="https://t.me/termux_tutoril")]
        ]
        await query.edit_message_text(text=info_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# --- VEB SERVER QISMI ---
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
    application.add_handler(CallbackQueryHandler(button_tap))
    application.add_error_handler(error_handler)
    
    print("Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
