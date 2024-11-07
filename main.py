from aiogram import Bot, Dispatcher, types, Router, filters
import asyncio

from router import MainRouter, AdminRouter
from models import init_db




bot = Bot(token='7645556829:AAHO6ZJby1m9hdMZITwdHHO25WljLCBz6Wc')

async def call_admin(admins_id, product, user_id):
    for admin_id in admins_id:
        profile_link = f"tg://user?id={user_id}"
        text = f"[Користувач]({profile_link}) замовив {product.flavor}, розмір: {product.size} мл, ціна: {product.price}"
        await bot.send_message(chat_id=user_id, text=text)

async def run_bot():

    dp = Dispatcher()
    dp.include_router(AdminRouter)
    dp.include_router(MainRouter)
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(run_bot())
