import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [877872483]

BACKEND_URL = "https://my-wishlist.onrender.com"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()


@dp.message(Command("start"))
async def handle_start(message: Message):
    await message.answer("👋 Привет! Этот бот пока ничего не делает публично.\nЕсли ты админ, напиши /admin.")


@dp.message(Command("admin"))
async def handle_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 У тебя нет доступа к админке.")
        return
    url = f"{BACKEND_URL}/admin?user_id={message.from_user.id}"
    await message.answer(f"👑 Админ-панель:\n<a href='{url}'>Открыть админку</a>")


@dp.message(Command("reset"))
async def handle_reset(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 Нет доступа.")
        return

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BACKEND_URL}/admin/reset", json={"user_id": message.from_user.id}) as resp:
            if resp.status == 200:
                await message.answer("✅ Все бронирования сброшены.")
            else:
                await message.answer("❌ Не удалось сбросить бронирования.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
