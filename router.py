from aiogram import Router, F, Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from sqlalchemy.sql.functions import count
import io
from UserRoutes import MainRouter
from models import Product, SessionLocal, Transaction
from sqlalchemy import select, text, insert, exists, desc
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import asyncio
from utils import bot, call_admin, make_flavor_choose, ADMIN_IDS, default_user_kb, make_bool_kb, call_user, \
    default_admin_kb, render_template
from models import init_db
from datetime import datetime



AdminRouter = Router()


class AddProduct(StatesGroup):
    flavor = State()
    size = State()
    price = State()
    count = State()


class ChangeProduct(StatesGroup):
    product_flavor = State()
    product_size = State()
    property_ = State()
    flavor = State()
    size = State()
    price = State()
    count = State()


class AdminTransactions(StatesGroup):
    transaction_type = State()
    select_user = State()
    select_trx_id = State()
    select_trx_action = State()
    send_message_to_user = State()
    confirm = State()
    get_all_trx = State()

class DeleteProduct(StatesGroup):
    id = State()
    confirm = State()


class AdminFilter(BaseFilter):
    async def __call__(self, message) -> bool:
        return message.from_user.id in ADMIN_IDS

AVAIBLE_FLAVORS = set()

AdminRouter.message.filter(AdminFilter())

@AdminRouter.message(Command('admin'))
async def admin(message):
    await message.answer('Список команд: '+
                         '\nДодати продукт /add_products'+
                         '\nЗмінити продукт /change_product'+
                         '\nТранзакції /transactions', reply_markup=default_admin_kb())

@AdminRouter.message(Command('add_products'))
async def add_products(message, state: FSMContext):
    await message.answer("Введіть назву смаку. Або введіть /cancel щоб скасувати")
    await state.set_state(AddProduct.flavor)

@AdminRouter.message(Command('cancel'))
async def cancel(message, state: FSMContext):
    await message.answer("Скасовано", reply_markup=make_flavor_choose(['/shop']))
    await state.clear()

@AdminRouter.message(AddProduct.flavor)
async def set_flavor(message, state: FSMContext):
    flavor = message.text
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
    await message.answer('Виберіть властивіть для зміни', reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість", '/cancel'], 2))

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
        await message.answer("Успішно зміненно, ви можете далі змінювати цей товар", reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість", '/cancel'], 2))
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
                         reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість", '/cancel'], 2))
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
                         reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість", '/cancel'], 2))

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
                         reply_markup=make_flavor_choose(["Смак", "Об'єм", "Ціна", "Кількість", '/cancel'], 2))

@AdminRouter.message(Command('transactions'))
async def see_transactions(message, state: FSMContext):
    await state.set_state(AdminTransactions.transaction_type)
    await message.answer('Виберіть статус замовлення. Якщо хочете скасувати замовлення перейдіть в розділ "В очікуванні"', reply_markup=make_flavor_choose(["В очікуванні", "Усі", "Скасувати"],2))

@AdminRouter.message(AdminTransactions.transaction_type)
async def see_transactions_with_status(message, state: FSMContext):
    status = 'Any'
    if message.text not in ["В очікуванні","Усі", "Скасувати"]:
        await message.answer("Виберіть правильний статус або введіть 'Скасувати'")
        return
    if message.text == 'Скасувати':
        await message.answer("Скасовано", reply_markup = make_flavor_choose(['/my_orders', '/admin', '/shop'],3))
    if message.text == 'В очікуванні':
        msg = 'Список 10 останніх очікуваних транзакцій'
        status = 'pending'
    if message.text == 'Усі':
        await state.set_state(AdminTransactions.get_all_trx)
        await get_all_trx(message, state)
        return

    async with SessionLocal() as session:
        query = (
            select(
                Transaction.telegram_user_id,
                Transaction.telegram_user_first_name,
                Transaction.telegram_user_last_name,
                Transaction.telegram_user_username,
                count(Transaction.id).label("user_trx_count")
            )
            .where(Transaction.status == status)
            .group_by(
                Transaction.telegram_user_id
            )
            .order_by(desc(Transaction.created_at))
            .limit(50)
        )
        result = await session.execute(query)
        transactions = result.all()
        for transaction in transactions:
            print(transaction)
            print(transaction.telegram_user_id)

    tg_users_ids = set()
    for transaction in transactions:

        profile_link = f"tg://user?id={transaction.telegram_user_id}"
        if transaction.telegram_user_last_name:
            fullname = transaction.telegram_user_first_name + ' ' + transaction.telegram_user_last_name
        else:
            fullname = transaction.telegram_user_first_name
        username = f"@{transaction.telegram_user_username}" if transaction.telegram_user_username else "відсутній"
        username = username.replace('_', '\\_')
        msg += f"\n[Користувач]({profile_link}), tg id: {transaction.telegram_user_id}, username: {username}, Ім'я: {fullname}\nЗамовлень: {transaction.user_trx_count}"
        tg_users_ids.add(transaction.telegram_user_id)

    await state.update_data(transactions=transactions, status=status, available_tg_ids=tg_users_ids)
    if status == 'pending':
        await state.set_state(AdminTransactions.select_user)
    await message.answer(msg, parse_mode= ParseMode.MARKDOWN, reply_markup=make_flavor_choose(tg_users_ids,2))


@AdminRouter.message(AdminTransactions.get_all_trx)
async def get_all_trx(message, state: FSMContext):
    async with SessionLocal() as session:
        query = select(Transaction)
        result = await session.scalars(query)
        trxs = result.all()
        msg = render_template(trxs)
        formatted_date = datetime.today().strftime('%Y-%m-%d')
        file = BufferedInputFile(msg.encode('utf-8'), filename=f"звіт_{formatted_date}.html")

        # Відправка файлу користувачу
        await message.answer_document(file, caption="Звіт про транзакції", reply_markup=default_admin_kb() )
        await state.clear()



@AdminRouter.message(AdminTransactions.select_user)
async def select_trx_id(message, state: FSMContext):
    user_data = await state.get_data()
    available_tg_ids = user_data['available_tg_ids']
    try:
        user_id = int(message.text)
        if user_id not in available_tg_ids:
            await message.answer("Виберіть дійсного користувача", reply_markup=make_flavor_choose(available_tg_ids,2))
            return
    except:
        await message.answer("Виберіть дійсного користувача", reply_markup=make_flavor_choose(available_tg_ids, 2))
        return

    async with SessionLocal() as session:
        query = select(Transaction).where(Transaction.telegram_user_id == user_id)
        result = await session.scalars(query)
        transactions = result.all()
    msg = f'Список транзакцій користувача {user_id}'
    if not transactions:
        msg += 'У цього користувача немає транзакцій'

    trx_ids = set()
    for transaction in transactions:
        profile_link = f"tg://user?id={transaction.telegram_user_id}"
        if transaction.telegram_user_last_name:
            fullname = transaction.telegram_user_first_name + ' ' + transaction.telegram_user_last_name
        else:
            fullname = transaction.telegram_user_first_name
        username = f"@{transaction.telegram_user_username}" if transaction.telegram_user_username else "відсутній"
        username = username.replace('_', '\\_')
        trx_ids.add(transaction.id)
        msg += f"\nid: {transaction.id}, Смак: {transaction.flavor}, Об'єм: {transaction.size}, Ціна: {transaction.price}, Час: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}, [Користувач]({profile_link}), tgid: {transaction.telegram_user_id}, username: {username}, Ім'я: {fullname}, Статус: {transaction.status}\n"
    await state.update_data(available_trx_ids=trx_ids, tg_user_id=user_id)
    await state.set_state(AdminTransactions.select_trx_id)
    await message.answer(msg, parse_mode= ParseMode.MARKDOWN, reply_markup=make_flavor_choose(trx_ids,3))

@AdminRouter.message(AdminTransactions.select_trx_id)
async def select_trx_id(message, state: FSMContext):
    user_data = await state.get_data()
    try:
        trx_id = int(message.text)
        if trx_id not in user_data['available_trx_ids']:
            await message.answer('Введіть дійсний номер транзакції', reply_markup=make_flavor_choose(user_data['available_trx_ids'],3))
            return
    except:
        await message.answer('Введіть дійсний номер транзакції',
                             reply_markup=make_flavor_choose(user_data['available_trx_ids'], 3))
        return
    await state.update_data(trx_id=trx_id)
    await state.set_state(AdminTransactions.select_trx_action)
    await message.answer("Виберіть дію", reply_markup=make_flavor_choose(['Надіслати повідомлення', 'Скасувати транзакцію'], 1))

@AdminRouter.message(AdminTransactions.select_trx_action)
async def select_trx_action(message, state: FSMContext):
    user_data = await state.get_data()
    tg_user_id = user_data['tg_user_id']
    trx_id = user_data['trx_id']
    profile_link = f"tg://user?id={tg_user_id}"
    async with SessionLocal() as session:
        query = select(Transaction).where(Transaction.id == trx_id)
        transaction = await session.scalar(query)
        if transaction is None:
            await message.answer("Транзакцію не знайдено",
                                 reply_markup=make_flavor_choose(['/my_orders', '/shop', '/transactions'], 1))
            return
        await state.update_data(transaction=transaction)
    if message.text not in ['Надіслати повідомлення', 'Скасувати транзакцію']:
        await message.answer("Виберіть дію зі списку", reply_markup=make_flavor_choose(['Надіслати повідомлення', 'Скасувати транзакцію'], 1))
    elif message.text == 'Надіслати повідомлення':
        await message.answer(f"Введіть текст повідомлення [користувачу]({profile_link}) з приводу замовлення:", parse_mode=ParseMode.MARKDOWN, reply_markup=ReplyKeyboardRemove())
        await state.set_state(AdminTransactions.send_message_to_user)
    elif message.text == 'Скасувати транзакцію':
        profile_link = f"tg://user?id={transaction.telegram_user_id}"
        if transaction.telegram_user_last_name:
            fullname = transaction.telegram_user_first_name + ' ' + transaction.telegram_user_last_name
        else:
            fullname = transaction.telegram_user_first_name
        username = f"@{transaction.telegram_user_username}" if transaction.telegram_user_username else "відсутній"
        username = username.replace('_', '\\_')

        msg = f"\nid: {transaction.id}, Смак: {transaction.flavor}, Об'єм: {transaction.size}, Ціна: {transaction.price}, Час: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}, [Користувач]({profile_link}), tgid: {transaction.telegram_user_id}, username: {username}, Ім'я: {fullname}, Статус: {transaction.status}\n"
        msg += '\nСкасувати цю транзакцію?'
        await message.answer(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=make_bool_kb())
        await state.set_state(AdminTransactions.confirm)

@AdminRouter.message(AdminTransactions.send_message_to_user)
async def send_message_to_user(message, state: FSMContext):
    user_data = await state.get_data()
    tg_user_id = user_data['tg_user_id']
    transaction = user_data['transaction']
    msg = f"Вам надіслано повідомлення з приводу замовлення №{transaction.id}, Смак: {transaction.flavor}, Об'єм: {transaction.price}мл, Ціна: {transaction.price}грн, Дата: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    msg += f'\nТекст повідомлення: {message.text}'
    await call_user(tg_user_id, msg)
    await message.answer("Надіслано", reply_markup=default_admin_kb())
    await state.clear()

@AdminRouter.message(AdminTransactions.confirm)
async def confirm(message, state: FSMContext):
    user_data = await state.get_data()
    tg_user_id = user_data['tg_user_id']
    trx_id = user_data['trx_id']
    if message.text[:3] != 'Так':
        await message.answer("Скасовано", reply_markup = default_admin_kb())

    async with SessionLocal() as session:
        query = select(Transaction).where(Transaction.id == trx_id)
        transaction = await session.scalars(query)
        if transaction is None:
            await message.answer("Сталася неочікувана помилка", reply_markup = default_admin_kb())
            await state.clear()
            return

        transaction.status = 'canceled'
        try:
            await session.commit()

        except:
            await message.answer("Сталася неочікувана помилка", reply_markup=default_admin_kb())
            await state.clear()
            return
        await message.answer("Успішно скасовано", reply_markup = default_admin_kb())

        await state.clear()
        msg = f"Ваше замовлення було скасоване. Деталі замовлення\n №{transaction.id}, Смак: {transaction.flavor}, Об'єм: {transaction.price}мл, Ціна: {transaction.price}грн, Дата: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        await call_user(tg_user_id, msg)


@AdminRouter.message(Command('delete_product'))
async def delete_product(message, state: FSMContext):
    msg = "Список продуктів. Оберіть id продукта який хочете видалити"
    ids = set()
    async with SessionLocal() as session:
        query = select(Product)
        products = await session.scalars(query)
        products_list = products.all()
        for product in products_list:
            ids.add(product.id)
            msg += f'\nid: {product.id}, Смак {product.flavor}, Розмір: {product.size}мл, Ціна: {product.price}грн, Кількість: {product.count}'
    await message.answer(msg,reply_markup=make_flavor_choose(ids,3))
    await state.set_state(DeleteProduct.id)
    await state.update_data(available_ids = ids, product_list = products_list)

@AdminRouter.message(DeleteProduct.id)
async def delete_product_id(message, state: FSMContext):
    user_data = await state.get_data()
    try:
        product_id = int(message.text)
        if product_id not in user_data['available_ids']:
            await message.answer('Виберіть id зі списку', reply_markup = make_flavor_choose(user_data['available_ids'],3))
            return
    except ValueError:
        await message.answer('Виберіть id зі списку', reply_markup=make_flavor_choose(user_data['available_ids'], 3))
        return

    product = None
    for product_ in user_data['product_list']:
        if product_.id == product_id:
            product = product_
            break
    if product is None:
        await message.answer('Сталася помилка', reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return
    msg = "Ви впевненні що хочете видалити цей продукт?"
    msg += f'\nid: {product.id}, Смак {product.flavor}, Розмір: {product.size}мл, Ціна: {product.price}грн, Кількість: {product.count}'
    await state.update_data(product_id = product_id)
    await message.answer(msg, reply_markup=make_bool_kb())
    await state.set_state(DeleteProduct.confirm)

@AdminRouter.message(DeleteProduct.confirm)
async def delete_product_confirm(message, state: FSMContext):
    user_data = await state.get_data()
    if message.text[:3] != 'Так':
        await message.answer("Скасовано", reply_markup = default_admin_kb())
        await state.clear()
        return

    async with SessionLocal() as session:
        product = await session.get(Product, user_data['product_id'])
        if product is None:
            await message.answer('Сталася помилка', reply_markup=ReplyKeyboardRemove())
            await state.clear()
            return
        await session.delete(product)
        await session.commit()
        await message.answer("Успішно видалено", reply_markup=default_admin_kb())
        await state.clear()


async def run_bot():
    dp = Dispatcher()
    dp.include_router(AdminRouter)
    dp.include_router(MainRouter)
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(run_bot())














