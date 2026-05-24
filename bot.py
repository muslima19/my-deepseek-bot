import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
import aiohttp
from flask import Flask
from threading import Thread

# ==================== SOZLAMALAR ====================
# new bot token & deepseek api key:
BOT_TOKEN = "8884799336:AAGD9Sf48ZHtBhpxkyKzk-96LwOtwVb7E78"
DEEPSEEK_API_KEY = "sk-0e08f0c2b8b84e08bef07a61ee661f0b"
DEEPSEEK_URL = "https://deepseek.com"

MAX_CHARS = 500
MAX_TOKENS = 150
DAILY_LIMIT = 20

# Foydalanuvchilar statistikasi va limitlarini saqlash
user_stats = {}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==================== FLASK VEB SERVER (Render uchun) ====================
app = Flask('')

@app.route('/')
def home():
    return "Bot Render serverida 24/7 faol ishlamoqda!"

def run_flask():
    # Render avtomatik taqdim etadigan 10000-portda veb-saytni yoqamiz
    app.run(host='0.0.0.0', port=10000)


# ==================== KUNLIK LIMITLARNI YANGILASH ====================
async def reset_daily_limits():
    while True:
        await asyncio.sleep(86400)  # 24 soat kutish
        user_stats.clear()
        logging.info("Kunlik limitlar muvaffaqiyatli nollashdi.")


# ==================== DEEPSEEK API BILAN ISHLASH ====================
async def ask_deepseek(prompt: str):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7
    }
    
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(DEEPSEEK_URL, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['choices']['message']['content']
                else:
                    return f"DeepSeek xato qaytardi (Kod: {response.status})."
    except Exception as e:
        return "Tizimda xatolik yuz berdi. Birozdan so'ng urinib ko'ring."


# ==================== BOT BUYRUKLARI ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 <b>hi! Men 24/7 ishlayotgan DeepSeek ai botiman.</b>\n\n"
        "ixtiyoriy savol berishiz mumkin.\n"
        "📊 Kunlik so'rovlar limiti: <b>20 ta</b>\n"
        "📝 Max text uzunligi: <b>500 belgi</b>\n"
        "📈 Statistikani korish: /stats",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    stats = user_stats.get(user_id, {"count": 0})
    remaining = max(0, DAILY_LIMIT - stats["count"])
    
    await message.answer(
        f"📊 <b>Sizning statistikangiz:</b>\n\n"
        f"• Bugun berilgan questions: <b>{stats['count']} ta</b>\n"
        f"• Qolgan so'rovlar limiti: <b>{remaining} ta</b>",
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    
    if user_id not in user_stats:
        user_stats[user_id] = {"count": 0}
        
    stats = user_stats[user_id]
    
    # 1. Kunlik limit tekshiruvi
    if stats["count"] >= DAILY_LIMIT:
        await message.answer("❌ <b>daily limit tugadi!</b> daily limitdan foydalanib boldiz.", parse_mode=ParseMode.HTML)
        return

    # 2. Xabar uzunligi haqida ogohlantirish (Max 500 char)
    if len(text) > MAX_CHARS:
        await message.answer(f"⚠️ <b>Ogohlantirish!</b>xabaringiz {MAX_CHARS} belgidan ko'p. Javob chala chiqishi mumkin.", parse_mode=ParseMode.HTML)

    status_msg = await message.answer("⏳ <i>DeepSeek thinking...</i>", parse_mode=ParseMode.HTML)
    
    # API dan javob olish
    ai_response = await ask_deepseek(text)
    
    # Limitni 1 taga oshirish
    stats["count"] += 1
    
    # Yakuniy javobni tahrirlash (Edit text)
    await status_msg.edit_text(f"🤖 <b>DeepSeek:</b>\n\n{ai_response}", parse_mode=ParseMode.HTML)


# ==================== INTEGRATSIYA VA ISHGA TUSHIRISH ====================
async def main():
    # Fondagi limitlarni nollash taymerini faollashtiramiz
    asyncio.create_task(reset_daily_limits())
    await dp.start_polling(bot)


if name == "main":
    # Flask veb serverni alohida oqimda (Thread) fonda yoqamiz
    t = Thread(target=run_flask)
    t.start()
    
    # Telegram botni asosiy oqimda ishga tushiramiz
    asyncio.run(main())
