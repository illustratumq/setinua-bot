from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message

from app.config import Config
from app.misc.utils import get_status
from data.googlecalendar.calendar_api import GoogleCalendar
from app.handlers.private.start import start_cmd
from app.keyboards.reply.calendar import calendar_kb
from app.keyboards.reply.events import events_kb, delete_event_kb
from app.misc.enums import EventStatusEnum
from app.services.repos import EventRepo, CalendarRepo, UserRepo
from app.states.calendar import DeleteSG
from data.googlesheets.sheets_api import GoogleSheet


async def event_history(
        msg: Message, event_db: EventRepo, calendar_db: CalendarRepo,
        user_db: UserRepo, state: FSMContext, sheet: GoogleSheet, config: Config
):
    events = await event_db.get_events(msg.from_user.id)
    if not events:
        await msg.answer('У вас ще немає бронювань')
        await start_cmd(msg, user_db, state, sheet, config)
    time_format = '%H:%M'
    date_format = '%d.%m.%y'
    events_str = ''
    long = False
    for event in events:
        calendar = await calendar_db.get_calendar_by_google_id(event.calendar_id)
        if len(events_str) >= 4000:
            long = True
            await msg.answer(events_str, reply_markup=events_kb)
            events_str = ''
        events_str += (
            f'📌 Замовлення #{event.event_id}\n'
            f'Адреса: {calendar.location} (Корт {calendar.name})\n'
            f'Час: {event.start.strftime(time_format)} - {event.end.strftime(time_format)} '
            f'({event.end.strftime(date_format)})\n'
            f'Статус замовлення: {get_status(event)}\n\n'
        )
    if len(events_str) > 2:
        await msg.answer(events_str, reply_markup=events_kb)


async def delete_event_list(msg: Message,  event_db: EventRepo):
    events = await event_db.get_events(msg.from_user.id)
    await msg.answer('Оберіть замовлення для видалення', reply_markup=delete_event_kb(events))
    await DeleteSG.Delete.set()


async def confirm_delete_event(msg: Message, state: FSMContext):
    event_id = int(msg.text.split('#')[-1])
    await state.update_data(event_id=event_id)
    await msg.answer(
        f'Ви бажаєте видалити замовлення #{event_id}. Підтвердіть свій вибір.',
        reply_markup=calendar_kb
    )
    await DeleteSG.Confirm.set()


async def delete_event(
        msg: Message, event_db: EventRepo, calendar_db: CalendarRepo, calendar:
        GoogleCalendar, state: FSMContext, user_db: UserRepo, sheet: GoogleSheet, config: Config,
):
    event_id = int((await state.get_data())['event_id'])
    event = await event_db.get_event(event_id)
    if event.status == EventStatusEnum.RESERVED:
        try:
            calendar.delete_event(event.calendar_id, event.google_id)
        except:
            pass
    if event.status in (EventStatusEnum.PAID, EventStatusEnum.CONFIRM):
        await event_db.update_event(event_id, status=EventStatusEnum.DELETED)
    else:
        await event_db.delete_event(event_id)
    await msg.answer(f'Замовлення №{event_id} видалено')
    await event_history(msg, event_db, calendar_db, user_db, state, sheet, config)


def setup(dp: Dispatcher):
    dp.register_message_handler(event_history, text='Мої замовлення 📚', state='*')
    dp.register_message_handler(delete_event_list, text='Видалити подію', state='*')
    dp.register_message_handler(confirm_delete_event, state=DeleteSG.Delete)
    dp.register_message_handler(delete_event, text='Підтведжую ✅', state=DeleteSG.Confirm)


