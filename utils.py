from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import ReplyKeyboardBuilder

bot = Bot(token='7645556829:AAHO6ZJby1m9hdMZITwdHHO25WljLCBz6Wc')


status_for_user = {
        'complete': 'Виконано',
        'pending': 'В очікуванні',
        'canceled': 'Скасовано',
        'failed': 'Виникла помилка'}

async def call_admin(admins_id, product, user_id):
    print(admins_id)
    for admin_id in admins_id:
        print(user_id)
        profile_link = f"tg://user?id={user_id}"
        text = f"[Користувач]({profile_link}) замовив {product.flavor}, розмір: {product.size} мл, ціна: {product.price}"
        await bot.send_message(chat_id=admin_id, text=text, parse_mode=ParseMode.MARKDOWN)


def make_flavor_choose(flavors, columns=3):
    kb = ReplyKeyboardBuilder()
    for flavor in flavors:
        kb.button(text=str(flavor))
    kb.adjust(columns)
    return kb.as_markup(resize_keyboard=True)

def default_user_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text='/shop')
    kb.button(text='/my_orders')
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def make_size_choose(Products):
    kb = ReplyKeyboardBuilder()
    sizes = {product.size for product in Products}
    for size in sizes:
        kb.button(text=str(size))
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True)

def make_bool_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Так✅")
    kb.button(text="Ні❌")
    return kb.as_markup(resize_keyboard=True)
