from datetime import datetime, timedelta

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from apscheduler_di import ContextSchedulerDecorator

from app.config import Config
from app.handlers.private.event import check_order_sub_polling, amount_solution
from app.keyboards.inline.pay import pay_kb
from app.keyboards.reply.calendar import calendar_kb
from app.keyboards.reply.menu import menu_kb, subscribe_time_kb, subscribe_days_kb
from app.misc.enums import SubTypeEnum
from app.services.fondy import FondyAPIWrapper
from app.services.repos import UserRepo, SubRepo
from app.states.calendar import SubSG
from data.googlesheets.sheets_api import GoogleSheet


async def subscribe_days(msg: Message):
    text = (
        'Виберіть дні коли ви зможете використовувати абонемент'
    )
    await msg.answer(text, reply_markup=subscribe_days_kb)
    await SubSG.Days.set()


async def subscribe_times(msg: Message, state: FSMContext):
    await state.update_data(days=msg.text)
    text = (
        'Виберіть години відвідування\n\n'
        'Денний час з 8:00 до 17:00\n'
        'Вечірній час з 17:00 до 22:00\n'
    )
    await msg.answer(text, reply_markup=subscribe_time_kb)
    await SubSG.Hours.set()


async def subscribe_confirm(msg: Message, user_db: UserRepo, state: FSMContext):
    data = await state.get_data()
    user = await user_db.get_user(msg.from_user.id)
    sub = 'before' if all([msg.text == 'Денний час', data['days'] == 'Будні дні']) else 'after'
    amount = amount_solution(user, sub, sub=True)
    text = (
        f'Ви збираєтесесь купити абонемент\n\n'
        f'Дні використання: {data["days"]}\n'
        f'Години використання: {msg.text}\n'
        f'Ціна: {amount}'
    )
    await state.update_data(amount=amount, times=msg.text)
    await msg.answer(text, reply_markup=calendar_kb)
    await SubSG.Confirm.set()


async def pay_subscribe(
        msg: Message, user_db: UserRepo, sub_db: SubRepo, state: FSMContext,
        fondy: FondyAPIWrapper, scheduler: ContextSchedulerDecorator,
        sheet: GoogleSheet, config: Config
):
    data = await state.get_data()
    user = await user_db.get_user(msg.from_user.id)
    description = (
        f'Оплата абонементу оренди кортів. Дні використання: {data["days"]}, '
        f'години використання: {data["times"]}. Клієнт {user.full_name} {user.phone_number} '
        f'({user.user_id})'
    )
    sub = await sub_db.add(
        user_id=msg.from_user.id, description=f'{data["days"]} ({data["times"].lower()})'
    )
    order = await fondy.create_order(
        description=description,
        amount=data['amount'],
        user=user,
        event_id=sub.sub_id
    )
    text = (
        'Оплата абонементу оренди кортів\n\n'
        f'Час: {data["days"]} ({data["times"].lower()})\n'
        f'Ціна: {data["amount"]}'
    )
    if data['days'] == 'Будні дні':
        if data['times'] == 'Денний час':
            sub_type = SubTypeEnum.WEEKMORNING
        else:
            sub_type = SubTypeEnum.WEEKEVENING
    else:
        if data['times'] == 'Денний час':
            sub_type = SubTypeEnum.HOLMORNING
        else:
            sub_type = SubTypeEnum.HOLEVENING
    msg = await msg.answer(text, reply_markup=pay_kb(order['url'], event_id=sub.sub_id, type_='sub'))
    job = scheduler.add_job(
        name=f'Перевірка підписки №{sub.sub_id}',
        func=check_order_sub_polling, trigger='interval', seconds=6, max_instances=5,
        kwargs=dict(msg=msg, sub=sub, sub_db=sub_db, user_db=user_db, fondy=fondy, sheet=sheet, config=config)
    )
    await sub_db.update_sub(
        sub.sub_id,
        order_id=order['order_id'],
        price=int(data["amount"]),
        job_id=job.id,
        type=sub_type
    )
    sheet.write_event(sub, user, config.misc.spreadsheet)
    await msg.answer('Мої вітаннячка', reply_markup=menu_kb)
    await state.finish()


def setup(dp: Dispatcher):
    dp.register_message_handler(subscribe_days, text='Абонемент ⭐', state='*')

    dp.register_message_handler(subscribe_times, state=SubSG.Days)
    dp.register_message_handler(subscribe_confirm, state=SubSG.Hours)
    dp.register_message_handler(pay_subscribe, state=SubSG.Confirm, text='Підтведжую ✅')