import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiohttp import web 

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [877872483]
BACKEND_URL = os.getenv("BACKEND_URL", "https://my-wishlist.onrender.com")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Напиши /admin, чтобы получить ссылку на админку.")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 У тебя нет доступа.")
        return
    url = f"{BACKEND_URL}/admin?user_id={message.from_user.id}"
    await message.answer(f"👑 Вот админка:\n<a href=\"{url}\">Открыть админку</a>")

@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 У тебя нет доступа.")
        return
    import aiohttp
    async with aiohttp.ClientSession() as s:
        r = await s.post(f"{BACKEND_URL}/admin/reset", json={"user_id": message.from_user.id})
        if r.status == 200:
            await message.answer("✅ Все бронирования сброшены.")
        else:
            await message.answer("❌ Не удалось сбросить бронирования.")

async def main():
    # 🚀 Запускаем aiogram
    asyncio.create_task(dp.start_polling(bot))

    # 🌐 Фиктивный HTTP-сервер, чтобы Render видел порт
    async def hello(request):
        return web.Response(text="Bot is running.")

    app = web.Application()
    app.add_routes([web.get("/", hello)])

    # 🟢 Render слушает PORT из окружения
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Bot is up and running on port {port}")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
