from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils import make_flavor_choose, make_size_choose, make_bool_kb, status_for_user, default_user_kb
from models import SessionLocal, Product, Transaction
from sqlalchemy import select, desc

MainRouter = Router()
class ChooseProduct(StatesGroup):
    flavor = State()
    size = State()
    confirm = State()

class UserTransactions(StatesGroup):
    transaction_type = State()
    complete = State()
    canceled = State()
    failed = State()
    pending = State()
    select_trx_id = State()

@MainRouter.message(Command('cancel'))
async def cancel(message, state):
    await message.answer("Скасовано", reply_markup=make_flavor_choose(['/shop', '/my_orders']))
    await state.clear()

@MainRouter.message(Command('start'))
async def start(message, state:FSMContext):
    await message.answer("початок", reply_markup=make_flavor_choose(['/shop']))
    await shop(message, state)

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
        await message.answer('Скасовано', reply_markup=make_flavor_choose(['/shop']))
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


        await message.answer("Успішно прийнято, @nicce_nik напише до вас у найближчій час.\nЯкщо у вас не встановленно user_name то напишіть до нього."
                             ,reply_markup=make_flavor_choose(['/shop']))

        await state.clear()

@MainRouter.message(Command('my_orders'))
async def my_orders(message, state: FSMContext):
    user_id = message.from_user.id
    msg = 'Останні 7 замовлень:'
    status_for_user = {
        'complete': 'Виконано',
        'pending': 'В очікуванні',
        'canceled': 'Скасовано',
        'failed': 'Виникла помилка'}

    async with SessionLocal() as session:
        query = select(Transaction).where(Transaction.telegram_user_id == user_id).limit(7).order_by(desc(Transaction.created_at))
        result = await session.scalars(query)
        result_list = result.all()
        for result in result_list:
            msg += f"\n\nНомер замовлення: {result.id}, Дата: {result.created_at.strftime('%Y-%m-%d %H:%M:%S')}, Смак: {result.flavor}, Об'єм: {result.size}мл, Ціна: {result.price}грн, Cтатус: {str(status_for_user.get(result.status))}"
    msg += '\n\nВиберіть статус замовлення. Якщо хочете скасувати замовлення перейдіть в розділ "В очікуванні"'

    await message.answer(msg, reply_markup=make_flavor_choose(['Виконані', "Скасовані", "В очікуванні", "З помилкою", "Усі", "Скасувати"],2))
    await state.set_state(UserTransactions.transaction_type)


@MainRouter.message(UserTransactions.transaction_type)
async def trx_type(message, state: FSMContext):
    if message.text not in ['Виконані', "Скасовані", "В очікуванні", "З помилкою", "Усі", "Скасувати"]:
        await message.answer("Введіть правильний тип або Скасувати")
        return
    msg = ''
    if message.text == 'Скасувати':
        await cancel(message,state)
        return

    if message.text == 'Виконані':
        msg += 'Список виконаних замовлень'
        async with SessionLocal() as session:
            query = select(Transaction).where(Transaction.telegram_user_id == message.from_user.id, Transaction.status == 'complete')
            result = await session.scalars(query)
            result_list = result.all()
            for result in result_list:
                msg += f"\n\nНомер замовлення: {result.id}, Дата: {result.created_at.strftime('%Y-%m-%d %H:%M:%S')}, Смак: {result.flavor}, Об'єм: {result.size}мл, Ціна: {result.price}грн, Cтатус: {str(status_for_user.get(result.status))}"

    if message.text == 'Скасовані':
        msg += 'Список скасованих замовлень'
        async with SessionLocal() as session:
            query = select(Transaction).where(Transaction.telegram_user_id == message.from_user.id, Transaction.status == 'canceled')
            result = await session.scalars(query)
            result_list = result.all()
            for result in result_list:
                msg += f"\n\nНомер замовлення: {result.id}, Дата: {result.created_at.strftime('%Y-%m-%d %H:%M:%S')}, Смак: {result.flavor}, Об'єм: {result.size}мл, Ціна: {result.price}грн, Cтатус: {str(status_for_user.get(result.status))}"

    if message.text == 'В очікуванні':
        msg += 'Список замовлень в очікуванні'
        async with SessionLocal() as session:
            query = select(Transaction).where(Transaction.telegram_user_id == message.from_user.id, Transaction.status == 'pending')
            result = await session.scalars(query)
            result_list = result.all()
            trxs = []
            for result in result_list:
                trxs.append(result.id)
                msg += f"\n\nНомер замовлення: {result.id}, Дата: {result.created_at.strftime('%Y-%m-%d %H:%M:%S')}, Смак: {result.flavor}, Об'єм: {result.size}мл, Ціна: {result.price}грн, Cтатус: {str(status_for_user.get(result.status))}"
            msg += '\n\n**Виберіть номер транзакції які хочете скасувати**'
            await message.answer(msg, reply_markup = make_flavor_choose(trxs))
            await state.update_data(avaible_ids=trxs, result_list=result_list)
            await state.set_state(UserTransactions.select_trx_id)
            return

    if message.text == 'З помилкою':
        msg += 'Список виконаних замовлень'
        async with SessionLocal() as session:
            query = select(Transaction).where(Transaction.telegram_user_id == message.from_user.id, Transaction.status == 'failed')
            result = await session.scalars(query)
            result_list = result.all()
            for result in result_list:
                msg += f"\n\nНомер замовлення: {result.id}, Дата: {result.created_at.strftime('%Y-%m-%d %H:%M:%S')}, Смак: {result.flavor}, Об'єм: {result.size}мл, Ціна: {result.price}грн, Cтатус: {str(status_for_user.get(result.status))}"

    if message.text == 'Усі':
        msg += 'Список ваших замовлень'
        async with SessionLocal() as session:
            query = select(Transaction).where(Transaction.telegram_user_id == message.from_user.id)
            result = await session.scalars(query)
            result_list = result.all()
            for result in result_list:
                msg += f"\n\nНомер замовлення: {result.id}, Дата: {result.created_at.strftime('%Y-%m-%d %H:%M:%S')}, Смак: {result.flavor}, Об'єм: {result.size}мл, Ціна: {result.price}грн, Cтатус: {str(status_for_user.get(result.status))}"

    await message.answer(msg, reply_markup = default_user_kb())

@MainRouter.message(UserTransactions.select_trx_id)
async def select_trx_id(message, state: FSMContext):
    user_data = await state.get_data()
    try:
        trx_id = int(message.text)
        if trx_id not in user_data['avaible_ids']:
            await message.answer('Введіть номер замовлення зі списку', reply_markup = make_flavor_choose(user_data['avaible_ids']))
            return
    except ValueError:
        await message.answer('Введіть номер замовлення зі списку',
                             reply_markup=make_flavor_choose(user_data['avaible_ids']))
        return



