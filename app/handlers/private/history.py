import re
from datetime import timedelta

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery

from app.config import Config
from app.keyboards.inline.pay import confirm_payback_kb, payback_cb
from app.keyboards.reply.back import back_kb
from app.keyboards.reply.menu import payback_kb, menu_kb
from app.misc.utils import get_status, now, localize
from app.services.fondy import FondyAPIWrapper
from app.states.inputs import PaybackSG
from data.googlecalendar.calendar_api import GoogleCalendar
from app.handlers.private.start import start_cmd
from app.keyboards.reply.calendar import calendar_kb
from app.keyboards.reply.events import events_kb, delete_event_kb
from app.misc.enums import EventStatusEnum, SubStatusEnum, SubTypeEnum
from app.services.repos import EventRepo, CalendarRepo, UserRepo, SubRepo
from app.states.calendar import DeleteSG
from data.googlesheets.sheets_api import GoogleSheet
format_time = '%A %d, %B'


async def event_history(
        msg: Message, event_db: EventRepo, calendar_db: CalendarRepo,
        user_db: UserRepo, state: FSMContext, sheet: GoogleSheet, config: Config
):
    events = await event_db.get_events(msg.from_user.id)
    events.sort(key=lambda e: e.event_id)
    if not events:
        await msg.answer('У вас ще немає бронювань')
        await start_cmd(msg, user_db, state, sheet, config)
    time_format = '%H:%M'
    date_format = '%d.%m.%y'
    events_str = ''
    for event in events:
        calendar = await calendar_db.get_calendar_by_google_id(event.calendar_id)
        if len(events_str) >= 4000:
            await msg.answer(events_str, reply_markup=events_kb)
            events_str = ''
        if localize(event.end) < now():
            status_event = '<b>Подія минула</b>'
        else:
            status_event = '<b>Нова 🟢</b>'
        events_str += (
            f'📌 Замовлення #{event.event_id} [{status_event}]\n'
            f'Адреса: {calendar.location} (Корт {calendar.name})\n'
            f'Час: {localize(event.start).strftime(time_format)} - {localize(event.end).strftime(time_format)} '
            f'({localize(event.end).strftime(date_format)})\n'
            f'Статус замовлення: {get_status(event)}\n\n'
        )
    if len(events_str) > 2:
        await msg.answer(events_str, reply_markup=events_kb)


async def delete_event_list(msg: Message,  event_db: EventRepo):
    events = await event_db.get_events(msg.from_user.id)
    await msg.answer('Оберіть оренду яку ви бажаєте відмінити або прибрати зі списку',
                     reply_markup=delete_event_kb(events))
    await DeleteSG.Delete.set()


async def confirm_delete_event(msg: Message, state: FSMContext, event_db: EventRepo):
    event_id = int(msg.text.split('#')[-1])
    event = await event_db.get_event(event_id)
    await state.update_data(event_id=event_id)
    await msg.answer(
        f'Ви бажаєте видалити замовлення №{event_id} на {localize(event.start).strftime(format_time)}. '
        f'Підтвердіть свій вибір.',
        reply_markup=calendar_kb
    )
    await DeleteSG.Confirm.set()


async def delete_event(
        msg: Message, event_db: EventRepo,  calendar_db: CalendarRepo, sub_db: SubRepo, calendar:
        GoogleCalendar, state: FSMContext, user_db: UserRepo, sheet: GoogleSheet, config: Config,
):
    event_id = int((await state.get_data())['event_id'])
    event = await event_db.get_event(event_id)
    court = await calendar_db.get_calendar_by_google_id(event.calendar_id)
    user = await user_db.get_user(event.user_id)

    if event.status == EventStatusEnum.RESERVED:
        try:
            calendar.delete_event(event.calendar_id, event.google_id)
        except:
            pass
        await event_db.delete_event(event_id)
        await msg.answer(f'Ваше замовлення номер №{event.event_id} успішно видалено',
                         reply_markup=events_kb)

    if event.status in (EventStatusEnum.PAID, EventStatusEnum.CONFIRM):
        if now() + timedelta(hours=8) < localize(event.end) < now():
            await msg.answer('❌ Видалення оренди відхилено\n\n'
                             'Ви можете скасувати оренду не пізніше ніж <b>за 8 годин до початку.</b>\n\n')
            await event_history(msg, event_db, calendar_db, user_db, state, sheet, config)
        elif localize(event.end) < now():
            await event_db.delete_event(event_id)
            await event_history(msg, event_db, calendar_db, user_db, state, sheet, config)
        else:
            for admin_id in config.bot.admin_ids:
                event_link = 'https://docs.google.com/spreadsheets/d/{}/edit#gid=1781353891&range=A{}:D{}'.format(
                    config.misc.spreadsheet, event.event_id + 1, event.event_id + 1
                )
                text = (
                    f'❌ Скасування оренди №{event.event_id}\n\n'
                    f'Користувач: {user.full_name}, {user.phone_number}\n\n'
                    f'📌 Дата: {event.start.strftime("%A %d, %B")} з {event.start.strftime("%H:%M")} по '
                    f'{event.end.strftime("%H:%M")}\n\n'
                    f'📚 <a href="{event_link}">Ця подія в таблиці</a>'
                )
                hours = (event.end - event.start).seconds / 3600
                if event.end.strftime('%A') in ('Сб', 'Нд'):
                    if event.end.hour > 17:
                        event_type = SubTypeEnum.HOLEVENING
                    else:
                        event_type = SubTypeEnum.HOLMORNING
                else:
                    if event.end.hour > 17:
                        event_type = SubTypeEnum.WEEKEVENING
                    else:
                        event_type = SubTypeEnum.WEEKMORNING
                sub = await sub_db.add(
                    user_id=msg.from_user.id,
                    description=f'Години скасованної оплати №{event_id}',
                    total_hours=hours,
                    status=SubStatusEnum.ACTIVE,
                    type=event_type
                )
                if event.price == 0:
                    await msg.answer(f'Замовлення №{event_id} скасовано.\n\n'
                                     'Ми нарахували Вам скасовані години до Вашого абонементу. '
                                     'Ви можете використати його будь-коли наступний раз для бронювання корту.\n\n',
                                     reply_markup=menu_kb)
                    sheet.write_event(event, user, config.misc.spreadsheet, court)
                    await state.finish()
                    return
                await state.update_data(sub_id=sub.sub_id, price=event.price, evet_id=event_id,
                                        mention=msg.from_user.id)
                await msg.bot.send_message(admin_id, text)
            await msg.answer(f'Замовлення №{event_id} скасовано.\n\n'
                             'Ми нарахували Вам скасовані години до Вашого абонементу. '
                             'Ви можете використати його будь-коли наступний раз для бронювання корту.\n\n'
                             '↪️💳 Для повернення коштів натисніть "Повернути кошти", '
                             'після чого нарахований абонемент видалиться, а кошти будуть '
                             'нараховані після попереднього схвалення адміністрацією.', reply_markup=payback_kb)
            await event_db.update_event(event_id, status=EventStatusEnum.DELETED)
            await PaybackSG.Card.set()
    sheet.write_event(event, user, config.misc.spreadsheet, court)


async def card_input(msg: Message):
    await msg.answer('Будь ласка надішліть номер вашої банківської карти в форматі\n\n4444555566661111',
                     reply_markup=back_kb)
    await PaybackSG.Input.set()


async def payback(msg: Message, state: FSMContext, config: Config, user_db: UserRepo, sub_db: SubRepo):
    if not _check_card(msg.text):
        await msg.answer('Невірний формат карти. Спробуйте ще раз')
        return
    data = await state.get_data()
    await sub_db.delete_sub(sub_id=int(data["sub_id"]))
    user = await user_db.get_user(int(data["mention"]))
    await msg.answer(f'Заявка на повернення коштів за скасовану оплату №{data["event_id"]} у сумі {data["price"]} була '
                     f'відправленна на розгялд адміністрації.', reply_markup=menu_kb)
    for chat_id in config.bot.admin_ids:
        try:
            if chat_id == config.bot.admin_ids[-1]:
                reply_markup = confirm_payback_kb(msg.text, int(data["price"]), user_id=user.user_id)
            else:
                reply_markup = None
            await msg.bot.send_message(
                chat_id,
                '↪💳 Заявка на повернення коштів\n\n'
                f'Користувач: {user.full_name}, {user.phone_number}\n'
                f'Скасована оренда номер №{data["event_id"]}: {data["price"]} грн.\n'
                f'Банківська карта: <code>{msg.text}</code>\n\n'
                f'Підтвердіть або скасуйте повернення коштів',
                reply_markup=reply_markup
             )
        except:
            pass
    await state.finish()


async def pay_true(call: CallbackQuery, fondy: FondyAPIWrapper, callback_data: dict):
    price = int(callback_data['price'])
    card = callback_data['card']
    user_id = callback_data['user_id']
    await call.message.delete_reply_markup()
    if callback_data['action'] == 'true':
        if await fondy.withdraw(amount=price, receiver_card_number=card, user_id=call.from_user.id):
            try:
                await call.message.answer('Виплата пройшла успішно')
                await call.bot.send_message(user_id,
                                            f'Виплата по скасованій оплаті у розмірі {price} грн. пройшла успішно')
            except:
                pass
    else:
        await call.message.answer('Виплата відмінена')


def setup(dp: Dispatcher):
    dp.register_message_handler(event_history, text='Мої замовлення 📚', state='*')
    dp.register_message_handler(delete_event_list, text='Видалити подію', state='*')
    dp.register_message_handler(confirm_delete_event, state=DeleteSG.Delete)
    dp.register_message_handler(delete_event, text='Підтведжую ✅', state=DeleteSG.Confirm)
    dp.register_message_handler(card_input, text='Повернути кошти', state=PaybackSG.Card)
    dp.register_message_handler(payback, state=PaybackSG.Input)
    dp.register_callback_query_handler(pay_true, payback_cb.filter())


def _check_card(card: str):
    if len(card) != 16:
        return False
    a = [card[:4], card[4:8], card[8:12], card[12:]]
    if len(a) != 4:
        return False
    for b in a:
        if len(b) != 4:
            return False
        p = re.search("[456][0-9]{15}", card)
        card = card.replace("-", "")
        q = re.search(".*([0-9])\\1{3}.*", card)
        if p and not q:
            return True
        else:
            return False