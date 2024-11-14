from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import os
from jinja2 import Environment, FileSystemLoader


current_dir = os.path.dirname(__file__)


env = Environment(loader=FileSystemLoader(current_dir))

def render_template(trxs):
    template = env.get_template('report_template.html')
    return template.render(transactions=trxs)

bot = Bot(token='7645556829:AAHO6ZJby1m9hdMZITwdHHO25WljLCBz6Wc')

ADMIN_IDS = {678120082, 586311998}

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
        text = f"[Користувач]({profile_link}) замовив {product.flavor}, розмір: {product.size} мл, ціна: {product.price}грн"
        await bot.send_message(chat_id=admin_id, text=text, parse_mode=ParseMode.MARKDOWN)

async def call_user(user_id, msg):
    await bot.send_message(chat_id=user_id, text=msg, parse_mode=ParseMode.MARKDOWN)


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

def default_admin_kb():
    kb = ReplyKeyboardBuilder()
    for i in ['/my_orders', '/shop', '/transactions', '/delete_product']:
       kb.button(text=i)
    kb.adjust(1)
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
