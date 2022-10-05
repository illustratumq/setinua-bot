import re

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, ContentType, CallbackQuery

from app.config import Config
from app.handlers.private.event import choose_type
from app.keyboards.inline.pay import confirm_event_cb
from app.keyboards.inline.setting import call_me_kb
from app.keyboards.reply.profile import contact_kb, profile_kb, contact_device_kb
from app.misc.enums import EventStatusEnum
from app.misc.utils import construct_user_text
from app.services.repos import UserRepo, SubRepo, CalendarRepo, EventRepo
from app.states.inputs import NameSG, ContactSG
from data.googlecalendar.calendar_api import GoogleCalendar
from data.googlesheets.sheets_api import GoogleSheet

PHONE_REGEX = re.compile(r'^[+]380[0-9]*$')


async def profile_info(msg: Message, user_db: UserRepo, sub_db: SubRepo, state: FSMContext):
    user = await user_db.get_user(msg.from_user.id)
    subs = await sub_db.get_subs_by_user_id(msg.from_user.id)
    text = (
        '🗂 [Ваш профіль]\n\n' + construct_user_text(user, subs)
    )
    await state.update_data(to_event=False)
    await msg.answer(text, reply_markup=profile_kb)


async def rewrite_full_name(msg: Message):
    await msg.answer('Надішліть ваше повне ім\'я (П.І.Б)')
    await NameSG.Input.set()


async def save_full_name(msg: Message, state: FSMContext,
                         user_db: UserRepo, sub_db: SubRepo, sheet: GoogleSheet, config: Config):
    user = await user_db.get_user(msg.from_user.id)
    await user_db.update_user(msg.from_user.id, full_name=msg.text)
    sheet.write_user(user, config.misc.spreadsheet)
    if user.phone_number is None:
        await input_number_phone(msg)
    else:
        await state.finish()
        await msg.answer('Успішно змінено')
        await profile_info(msg, user_db, sub_db, state)


async def input_number_phone(msg: Message):
    await msg.answer('Вкажіть номер телефону в форматі +380XXXXXXXXX', reply_markup=contact_device_kb)
    await ContactSG.Input.set()


async def save_number_phone(msg: Message, user_db: UserRepo, state: FSMContext, sub_db: SubRepo,
                            sheet: GoogleSheet, config: Config, calendar: GoogleCalendar,
                            calendar_db: CalendarRepo):
    await msg.answer('Успішно змінено')
    user = await user_db.get_user(msg.from_user.id)
    await user_db.update_user(msg.from_user.id, phone_number=msg.contact.phone_number)

    sheet.write_user(user, config.misc.spreadsheet)
    data = await state.get_data()
    if data.get('to_event'):
        await choose_type(msg, user_db, state)
    else:
        await state.finish()
        await profile_info(msg, user_db, sub_db, state)


async def save_custom_number_phone(msg: Message, user_db: UserRepo, state: FSMContext, sub_db: SubRepo,
                                   sheet: GoogleSheet, config: Config, calendar: GoogleCalendar,
                                   calendar_db: CalendarRepo):
    if len(msg.text) != len('+380XXXXXXXXX'):
        await msg.answer('Перевірте правильність набору. Будь ласка, вкажіть номер повторно в форматі +380XXXXXXXXX')
        return
    await msg.answer('Успішно зімнено')
    user = await user_db.get_user(msg.from_user.id)
    await user_db.update_user(msg.from_user.id, phone_number=msg.text)
    data = await state.get_data()
    sheet.write_user(user, config.misc.spreadsheet)
    if data['to_event']:
        await choose_type(msg, user_db, state)
    else:
        await profile_info(msg, user_db, sub_db, state)
        await state.finish()


async def choose_number_phone(msg: Message):
    await msg.answer('Оберіть один із доступних варінатів', reply_markup=contact_kb)
    await ContactSG.Choose.set()


async def confirm_user_event(call: CallbackQuery, event_db: EventRepo, user_db: UserRepo, calendar_db: CalendarRepo,
                             callback_data, calendar: GoogleCalendar, sheet: GoogleSheet, config: Config):
    await call.answer('😉 Гарного дня!')
    event_id = callback_data.get('event_id')
    action = callback_data.get('action')
    event = await event_db.get_event(int(event_id))
    user = await user_db.get_user(event.user_id)
    court = await calendar_db.get_calendar_by_google_id(event.calendar_id)
    if action == 'true':
        await event_db.update_event(event.event_id, status=EventStatusEnum.CONFIRM)
        calendar.event_confirm(event.calendar_id, event.google_id, user)
        sheet.write_event(event, user, config.misc.spreadsheet, court)
    else:
        for chat_id in config.bot.admin_ids:
            await call.bot.send_message(chat_id, f'Користувач {user.full_name}, {user.phone_number}, ({user.user_id} '
                                        f'скасував замовлення №{event.event_id} на {event.start.strftime("%H:%M")}')
        await event_db.update_event(event.event_id, status=EventStatusEnum.DELETED)
        calendar.delete_event(event.calendar_id, event.google_id)
    sheet.write_event(event, user, config.misc.spreadsheet, court)
    await call.message.delete_reply_markup()


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(confirm_user_event, confirm_event_cb.filter(), state='*')
    dp.register_message_handler(profile_info, text='Мій профіль 🙎‍♂️🙍‍♀️', state='*')
    dp.register_message_handler(call_me, text='Передзвоніть мені 📞', state='*')
    dp.register_message_handler(choose_number_phone, text='Редагувати номер телефону', state='*')
    dp.register_message_handler(rewrite_full_name, text='Редагувати ім\'я', state='*')
    dp.register_message_handler(save_full_name, state=NameSG.Input)

    dp.register_message_handler(input_number_phone, text='Інший номер', state=ContactSG.Choose)
    dp.register_message_handler(save_number_phone, content_types=ContentType.CONTACT, state='*')
    dp.register_message_handler(save_custom_number_phone, regexp=PHONE_REGEX, state=ContactSG.Input)


async def call_me(msg: Message, user_db: UserRepo, config: Config):
    user = await user_db.get_user(msg.from_user.id)
    if user.phone_number is None:
        await msg.answer('Спочатку додайте номер телефону')
        await choose_number_phone(msg)
        return
    await msg.answer('Заявка на зворотній зв\'язок відправлена адміністрації. '
                     'Ми передзвонимо вам найближчим часом 😉')
    for chat_id in config.bot.admin_ids:
        await msg.bot.send_message(
            chat_id=chat_id, text=f'📱 Передзвоніть мені\n'
                                  f'<b>Користувач</b>: {user.full_name}\n'
                                  f'<b>Номер</b>: {user.phone_number}',
            reply_markup=call_me_kb(msg.from_user.id)
        )
