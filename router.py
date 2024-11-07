from aiogram import Router, F, Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from models import Product, SessionLocal, Transaction
from sqlalchemy import select, text, insert, exists, desc
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import asyncio
from models import init_db


bot = Bot(token='7645556829:AAHO6ZJby1m9hdMZITwdHHO25WljLCBz6Wc')
MainRouter = Router()
AdminRouter = Router()


class AddProduct(StatesGroup):
    flavor = State()
    size = State()
    price = State()
    count = State()


class ChooseProduct(StatesGroup):
    flavor = State()
    size = State()
    confirm = State()


class ChangeProduct(StatesGroup):
    product_flavor = State()
    product_size = State()
    property_ = State()
    flavor = State()
    size = State()
    price = State()
    count = State()



ADMIN_IDS = {678120082, 586311998}

class AdminFilter(BaseFilter):
    async def __call__(self, message) -> bool:
        return message.from_user.id in ADMIN_IDS


AVAIBLE_FLAVORS = set()
def make_flavor_choose(flavors, columns=3):
    kb = ReplyKeyboardBuilder()
    for flavor in flavors:
        kb.button(text=str(flavor))
    kb.adjust(columns)
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








AdminRouter.message.filter(AdminFilter())


@AdminRouter.message(Command('admin'))
async def admin(message):
    await message.answer('Список команд: '+
                         '\nДодати продукт /add_products'+
                         '\nЗмінити продукт /change_product'+
                         '\nТранзакції /transactions', reply_markup=make_flavor_choose(['/add_products', '/change_product', '/transactions'],1))

@AdminRouter.message(Command('add_products'))
async def add_products(message, state: FSMContext):
    await message.answer("Введіть назву смаку. Або введіть /cancel щоб скасувати")
    await state.set_state(AddProduct.flavor)

@AdminRouter.message(Command('cancel'))
async def cancel(message, state: FSMContext):
    await message.answer("Скасовано")
    await state.clear()


@AdminRouter.message(AddProduct.flavor)
async def set_flavor(message, state: FSMContext):
    flavor = message.text.lower()
    await state.update_data(flavor=flavor)
    await message.answer("Виберіть розмір (мл)")
    await state.set_state(AddProduct.size)

@AdminRouter.message(AddProduct.size)
async def set_size(message, state: FSMContext):
    try:
        size = int(message.text)
        product = await state.get_data()
        flavor = product['flavor']
        async with SessionLocal() as session:
            query = select(
                exists().where(Product.flavor == flavor, Product.size == size))
            result = await session.scalar(query)
            if result:
                await message.answer(
                    "Такий смак з таким об'ємом вже існує, перейдіть в редагування щоб змінити ціну та кількість")
                await state.clear()
                return
        await state.update_data(size=size)
        await message.answer("Введіть ціну")
        await state.set_state(AddProduct.price)
    except ValueError:
        await message.answer("Введіть ціле число")


@AdminRouter.message(AddProduct.price)
async def set_price(message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price=price)
        await message.answer("Введіть кількість в наявності")
        await state.set_state(AddProduct.count)
    except ValueError:
        await message.answer("Введіть ціле число")




@AdminRouter.message(AddProduct.count)
async def set_count(message, state: FSMContext):
    count = int(message.text)
    product_data = await state.get_data()
    async with SessionLocal() as session:
        query = select(exists().where(Product.flavor == product_data['flavor'], Product.size == product_data['size']))
        result = await session.scalar(query)
        if result:
            await message.answer("Такий смак з таким об'ємом вже існує, перейдіть в редагування щоб змінити ціну та кількість")
            await state.clear()
            return
        product = Product(flavor=product_data['flavor'], size=product_data['size'], price=product_data['price'], count=count)
        session.add(product)
        await session.commit()
        await message.answer("Успішно додано")
    await message.answer(str(product_data))
    await state.clear()


@AdminRouter.message(Command('change_product'))
async def change_product(message, state: FSMContext):
    msg = "Введіть смак товару який хочете змінити\nСписок товарів:"
    async with SessionLocal() as session:
        query = select(Product).limit(25)
        result = await session.scalars(query)
        product_list = result.all()
        for product in product_list:
            msg +=f'\nСмак {product.flavor}, Розмір: {product.size}мл, Ціна: {product.price}грн, Кількість: {product.count}'
        flavors = list({product.flavor for product in product_list})
        kb = make_flavor_choose(flavors)

    await state.update_data(product_list=product_list, available_flavors=flavors)
    await state.set_state(ChangeProduct.product_flavor)
    await message.answer(msg, reply_markup=kb)


@AdminRouter.message(ChangeProduct.product_flavor)
async def change_product_choose_flavor(message, state: FSMContext):
    flavor = message.text
    user_data = await state.get_data()
    available_flavors = user_data['available_flavors']
    product_list = user_data['product_list']

    if flavor not in available_flavors: #check
        kb = make_flavor_choose(available_flavors)
        await message.answer("Виберіть смак зі списку", reply_markup=kb)
        return

    sizes = {product.size for product in product_list if product.flavor == flavor}
    kb = make_flavor_choose(sizes)
    await state.update_data(flavor=flavor, available_sizes=sizes)
    await message.answer("Виберіть розмір", reply_markup=kb)
    await state.set_state(ChangeProduct.product_size)


@AdminRouter.message(ChangeProduct.product_size)
async def change_product_choose_size(message, state: FSMContext):
    size = message.text
    user_data = await state.get_data()
    available_sizes = user_data['available_sizes']
    product_list = user_data['product_list']
    flavor = user_data['flavor']

    try:
        size = int(size)
    except ValueError:
        await message.answer("Введіть правильний розмір")
        return
    if size not in available_sizes:
        await message.answer('Введіть правильний розмір')
        return
    product = None
    for product_ in product_list:
        if product_.size == size and product_.flavor == flavor:
            product = product_

    if product is None:
        await message.answer("Cталася помилка", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    await state.update_data(size=size)
    await state.set_state(ChangeProduct.property_)
    await message.answer('Виберіть властивіть для зміни', reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість"], 2))


@AdminRouter.message(ChangeProduct.property_)
async def property_change(message, state: FSMContext):
    property_ = message.text
    if property_ not in ["Смак", "Об'єм", "Ціна", "Кількість"]:
        await message.answer("Виберіть правильну властивість")

    if property_ == "Смак":
        await state.set_state(ChangeProduct.flavor)
        await message.answer("Встановіть новий смак")
    elif property_ == "Об'єм":
        await state.set_state(ChangeProduct.size)
        await message.answer("Встановіть новий об'єм")
    elif property_ == "Ціна":
        await state.set_state(ChangeProduct.price)
        await message.answer("Встановіть нову ціну")
    elif property_ == "Кількість":
        await state.set_state(ChangeProduct.count)
        await message.answer("Встановіть нову кількість", reply_markup=make_flavor_choose(range(16),4))


@AdminRouter.message(ChangeProduct.flavor)
async def change_product_flavor(message, state: FSMContext):
    flavor = message.text
    user_data = await state.get_data()
    async with SessionLocal() as session:
        query = select(Product).where(Product.flavor == user_data['flavor'], Product.size == user_data['size'])
        result = await session.scalar(query)
        try:
            result.flavor = flavor
            await session.commit()
        except:
            await message.answer("Сталася помилка, можливо через те що товар з такою комбінацією смаку та об'єму вже існує", reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість"], 2))
            await state.set_state(ChangeProduct.property_)
            return
        await message.answer("Успішно зміненно, ви можете далі змінювати цей товар", reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість"], 2))
        await state.set_state(ChangeProduct.property_)


@AdminRouter.message(ChangeProduct.size)
async def change_product_size(message, state: FSMContext):
    size = message.text
    try:
        size = int(size)
    except ValueError:
        await message.answer("Введіть правильний об'єм")
        return

    user_data = await state.get_data()
    async with SessionLocal() as session:
        query = select(Product).where(Product.flavor == user_data['flavor'], Product.size == user_data['size'])
        result = await session.scalar(query)
        try:
            result.size = size
            await session.commit()
        except:
            await message.answer("Сталася помилка, можливо через те що товар з такою комбінацією смаку та об'єму вже існує", reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість"], 2))
            await state.set_state(ChangeProduct.property_)
            return
    await message.answer("Успішно зміненно, ви можете далі змінювати цей товар",
                         reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість"], 2))
    await state.set_state(ChangeProduct.property_)


@AdminRouter.message(ChangeProduct.price)
async def change_product_price(message, state: FSMContext):
    price = message.text
    user_data = await state.get_data()
    try:
        price = int(price)
    except ValueError:
        await message.answer("Введіть дійсне число")
        return

    async with SessionLocal() as session:
        query = select(Product).where(Product.flavor == user_data['flavor'], Product.size == user_data['size'])
        result = await session.scalar(query)
        result.price = price
        await session.commit()

    await state.set_state(ChangeProduct.property_)
    await message.answer("Успішно зміненно, ви можете далі змінювати цей товар",
                         reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість"], 2))



@AdminRouter.message(ChangeProduct.count)
async def change_product_count(message, state: FSMContext):
    count = message.text
    user_data = await state.get_data()
    try:
        count = int(count)
    except ValueError:
        await message.answer("Введіть дійсне число")
        return

    async with SessionLocal() as session:
        query = select(Product).where(Product.flavor == user_data['flavor'], Product.size == user_data['size'])
        result = await session.scalar(query)
        result.count = count
        await session.commit()

    await state.set_state(ChangeProduct.property_)
    await message.answer("Успішно зміненно, ви можете далі змінювати цей товар",
                         reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість"], 2))



@AdminRouter.message(Command('transactions'))
async def see_transactions(message, state: FSMContext):
    await message.answer("Список 10 останніх транзакцій /all_transactions"+
                         "\nСписок 10 останніх очікуваних транзакцій /pending_transactions"+
                         "\nСписок 10 останніх виконаних транзакцій /complete_transactions"+
                         "\nСписок 10 останніх скасованих транзакцій /canceled_transactions"+
                         "\nСписок 10 останніх невдалих транзакцій /failed_transactions", reply_markup=make_flavor_choose(['/pending_transactions', '/complete_transactions',
                                                                                                                           '/canceled_transactions', '/failed_transactions', '/all_transactions'],2))


@AdminRouter.message(Command('all_transactions'))
@AdminRouter.message(Command('failed_transactions'))
@AdminRouter.message(Command('canceled_transactions'))
@AdminRouter.message(Command('complete_transactions'))
@AdminRouter.message(Command('pending_transactions'))
async def see_transactions_with_status(message, state: FSMContext):
    msg = 'Список 10 останніх транзакцій'
    status = 'Any'
    if message.text == '/pending_transactions':
        msg = 'Список 10 останніх очікуваних транзакцій'
        status = 'pending'
    elif message.text == '/complete_transactions':
        msg = 'Список 10 останніх виконаних транзакцій'
        status = 'complete'
    elif message.text == '/canceled_transactions':
        msg = 'Список 10 останніх скасованих транзакцій'
        status = 'canceled'
    elif message.text == '/failed_transactions':
        msg = 'Список 10 останніх невдалих транзакцій'
        status = 'failed'
    async with SessionLocal() as session:
        if status == 'Any':
            query = select(Transaction).order_by(desc(Transaction.created_at)).limit(10)
        else:
            query = select(Transaction).where(Transaction.status == status).order_by(
                desc(Transaction.created_at)).limit(10)
        result = await session.scalars(query)
        transactions = result.all()
    for transaction in transactions:
        profile_link = f"tg://user?id={transaction.telegram_user_id}"
        if transaction.telegram_user_last_name:
            fullname = transaction.telegram_user_first_name + ' ' + transaction.telegram_user_last_name
        else:
            fullname = transaction.telegram_user_first_name
        msg += f"\nid: {transaction.id}, Смак: {transaction.flavor}, Об'єм: {transaction.size}, Ціна: {transaction.price}, Час: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}, [Користувач]({profile_link}), tg_id: {transaction.telegram_user_id}, username: @{transaction.telegram_user_username}, Ім'я: {fullname}, Статус: {transaction.status}\n"

    await message.answer(msg ,parse_mode=ParseMode.MARKDOWN)


@MainRouter.message(Command('start'))
async def start(message):
    await message.answer("початок", reply_markup=make_flavor_choose(['/shop']))
    await shop(message)


@MainRouter.message(Command('shop'))
async def shop(message, state: FSMContext):
    msg = 'Є в наявності:'
    async with SessionLocal() as session:
        query = select(Product).where(Product.count>0).limit(15)
        result = await session.scalars(query)

        product_list = result.all()
        flavors = {product.flavor for product in product_list}
        for product in product_list:
            msg += f'\nСмак {product.flavor}, Розмір: {product.size}мл, Ціна: {product.price}грн'
        kb = make_flavor_choose(flavors)
    await state.set_state(ChooseProduct.flavor)
    await state.update_data(AVAIBLE_FLAVORS=flavors, product_list=product_list)
    await message.answer(msg, reply_markup=kb)


@MainRouter.message(ChooseProduct.flavor)
async def flavor_choose(message, state: FSMContext):
    flavor = message.text
    msg = "Виберіть Об'єм: "
    user_data = await state.get_data()
    print("user_data: ",user_data)
    AVAIBLE_FLAVORS = user_data['AVAIBLE_FLAVORS']
    product_list = user_data['product_list']

    if flavor not in AVAIBLE_FLAVORS:
        await message.answer("Такого смаку немає, виберіть правильний смак: ")
        return
    await state.update_data(flavor=flavor)

    current_flavor_products = [product for product in product_list if product.flavor == flavor]
    AVAIBLE_SIZE = [product.size for product in current_flavor_products]
    await state.update_data(flavor=flavor, AVAIBLE_SIZE=AVAIBLE_SIZE)
    for product in current_flavor_products:
        msg += f"\nОб'єм: {product.size}, Ціна: {product.price}"
    kb = make_size_choose(product_list)
    await message.answer(msg,  reply_markup=kb)
    await state.set_state(ChooseProduct.size)


@MainRouter.message(ChooseProduct.size)
async def size(message, state: FSMContext):
    size = message.text.lower()
    try:
        size = int(size)
    except ValueError:
        await message.answer("Виберіть правильний розмір")
        return

    user_data = await state.get_data()
    AVAIBLE_SIZE = user_data['AVAIBLE_SIZE']
    flavor = user_data['flavor']
    product_list = user_data['product_list']

    if size not in AVAIBLE_SIZE: #check
        await message.answer('Виберіть правильний розмір')
        return

    price = -1
    for product in product_list:
        if product.flavor == flavor and product.size == size:
            price = product.price
            break

    await state.update_data(size=size)
    await message.answer(f"Ви вибрали смак: {flavor}, розмір: {size} за ціною: {price}. Підтвердити замовлення?", reply_markup=make_bool_kb())
    await state.set_state(ChooseProduct.confirm)






@MainRouter.message(ChooseProduct.confirm)
async def confirm(message, state: FSMContext):
    ans = message.text[:3]
    if ans != 'Так':
        await message.answer('Скасовано')
        await state.clear()
        return
    user_data = await state.get_data()
    print("confirm:user_data: ", user_data)
    flavor = user_data['flavor']
    size = user_data['size']
    user_id = message.from_user.id
    name = message.from_user.first_name
    if message.from_user.last_name:
        name += ' '+ message.from_user.last_name

    async with SessionLocal() as session:
        query = select(Product).where(Product.flavor == flavor, Product.size == size, Product.count > 0)
        result = await session.scalar(query)
        if result is None:
            await message.answer("На жаль, товару не залишилось, виберіть інший")
            await state.clear()
        transaction = Transaction(flavor=result.flavor, size=result.size, price=result.price,
                                  telegram_user_id=user_id, telegram_user_first_name=message.from_user.first_name,
                                  telegram_user_last_name=message.from_user.last_name, telegram_user_username=message.from_user.username,
                                  status='pending')
        result.count -= 1
        session.add(transaction)
        # await call_admin(ADMIN_IDS, result, user_id)
        await session.commit()


        await message.answer("Успішно прийнято, @nicce_nik напише до вас у найближчій час.\nЯкщо у вас не встановленно user_name то напишіть до нього.")

        await state.clear()



async def call_admin(admins_id, product, user_id):
    print(admins_id)
    for admin_id in admins_id:
        print(user_id)
        profile_link = f"tg://user?id={user_id}"
        text = f"[Користувач]({profile_link}) замовив {product.flavor}, розмір: {product.size} мл, ціна: {product.price}"
        await bot.send_message(chat_id=admin_id, text=text, parse_mode=ParseMode.MARKDOWN)


async def run_bot():
    dp = Dispatcher()
    dp.include_router(AdminRouter)
    dp.include_router(MainRouter)
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(run_bot())














