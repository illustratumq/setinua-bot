import logging
from datetime import datetime, timedelta

import numpy as np
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery
from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.keyboards.reply.back import back_kb
from app.keyboards.reply.events import choose_sub_kb
from app.states.inputs import NameSG
from data.googlecalendar.calendar_api import GoogleCalendar
from app.handlers.private.start import start_cmd
from app.keyboards.inline.calendar import days_cb, create_calendar_kb, none_cb, choose_day_cb, no_times_kb
import locale
import time

from app.keyboards.inline.pay import pay_kb, pay_cb
from app.keyboards.reply.calendar import calendar_kb, confirm_event_kb, subs_kb
from app.keyboards.reply.menu import orenda_kb, menu_kb
from app.keyboards.reply.times import generic_available_times
from app.misc.enums import EventStatusEnum, SubStatusEnum, UserStatusEnum, SubTypeEnum
from app.misc.utils import now, localize, amount_solution
from app.models import User
from app.models.event import Event
from app.models.subscribe import Subscribe
from app.services.fondy import FondyAPIWrapper
from app.services.repos import CalendarRepo, EventRepo, UserRepo, SubRepo
from app.states.calendar import EventSG
from data.googlesheets.sheets_api import GoogleSheet

format_time = '%A, %d %B'
locale.setlocale(locale.LC_ALL, 'uk_UA.UTF8')
log = logging.getLogger(__name__)


async def reserved_times_list(calendar: GoogleCalendar, calendar_db: CalendarRepo, day: datetime):
    inputs = []
    outputs = []
    courts = await calendar_db.get_all()
    for court in courts:
        inputs.append(calendar.reserved_time(court.google_id, day))
    start = now().replace(hour=7, minute=0, second=0)
    end = start.replace(hour=22)
    size = int((end - start) / timedelta(minutes=30)) + 1
    base_date_signal = [(start + timedelta(minutes=30 * i)).strftime('%H:%M') for i in range(size)]
    for input_signal in inputs:
        output_signal = np.zeros(size)
        for date in input_signal:
            start_date, end_date = date.split(' - ')
            if start_date in base_date_signal:
                index_start = base_date_signal.index(start_date)
                index_end = base_date_signal.index(end_date)
                output_signal[index_start:index_end + 1] = 1
                outputs.append(output_signal)
    out = sum(outputs)
    if isinstance(out, int):
        return []
    reserved_times = []
    cache = []
    for i in range(size):
        if out[i] >= len(courts):
            cache.append((start + timedelta(minutes=30 * i)).strftime('%H:%M'))
            if i != size and out[i+1] <= len(courts):
                reserved_times.append(cache)
                cache = []
            elif i == size:
                reserved_times.append(cache)
    return [f'{lst[0]} - {lst[-1]}' for lst in reserved_times]


async def choose_type(msg: Message, user_db: UserRepo, state: FSMContext):
    user = await user_db.get_user(msg.from_user.id)
    if user.phone_number is None:
        await msg.answer('Для початку заповніть інформацію про себе.\n\nНадішліть ваше повне ім\'я (П.І.Б)')
        await NameSG.Input.set()
        await state.update_data(to_event=True)
        return
    if user.status == UserStatusEnum.TRAINER:
        await choose_date(msg, state)
        return
    await msg.answer('Оберіть тип оренди 👇', reply_markup=orenda_kb)


async def choose_date(msg: Message, state: FSMContext):
    now_date = ', '.join([w.capitalize() for w in now().strftime(format_time).split(', ')])
    text = (
        f'Обрана дата - <i><b>Сьогодні ({now_date})</b></i>.\nНатисніть <b>"Обрати цю дату 👌"</b> '
        f'або оберіть іншу.'
    )
    await state.update_data(reserved_times=[])
    await msg.answer('Будь-ласка оберіть дату бронювання корту', reply_markup=back_kb)
    date_kb, choose_kb = create_calendar_kb(now())
    cal_msg = await msg.answer('Натисніть на потрібну дату в календарі ⬇', reply_markup=date_kb)
    lst_msg = await msg.answer(text, reply_markup=choose_kb)
    await state.update_data(last_msg_id=lst_msg.message_id, calendar_msg_id=cal_msg.message_id, now_date=now_date)


async def pagination_calendar(call: CallbackQuery, callback_data: dict, state: FSMContext,
                              calendar: GoogleCalendar, calendar_db: CalendarRepo):
    data = await state.get_data()
    await call.bot.delete_message(call.from_user.id, data['last_msg_id'])
    await call.bot.delete_message(call.from_user.id, data['calendar_msg_id'])
    wait = await call.message.answer('Перевіряю вільні години ⌛')
    current_day = now().replace(
        year=int(callback_data['y']),
        month=int(callback_data['m']),
        day=int(callback_data['d']),
    )
    reserved_times = await reserved_times_list(calendar, calendar_db, current_day)
    answer = generic_available_times(
        start=localize(current_day).replace(hour=7, minute=0, second=0, microsecond=0),
        end=localize(current_day).replace(hour=21, minute=0, second=0, microsecond=0),
        reserved_times=reserved_times, only_keyboard=True
    )
    now_date = ', '.join([w.capitalize() for w in current_day.strftime(format_time).split(', ')])
    if len(answer[0]) == 0:
        await state.finish()
        await call.message.answer(f'❌ Немає вільних годин на {now_date}')
        await choose_date(call.message, state)
        return
    if localize(current_day).replace(hour=22, minute=0) < now():
        await call.answer('Вибрана дата вже недоступна', show_alert=True)
        return
    await call.answer()
    await wait.delete()
    await state.update_data(reserved_times=reserved_times, now_date=now_date)
    date_kb, choose_kb = create_calendar_kb(current_day)
    cal_msg = await call.message.answer('Натисніть на потрібну дату в календарі ⬇', reply_markup=date_kb)
    msg = await call.message.answer(f'Ви обрали дату: <i><b>{now_date}</b></i>.\nНатисніть <b>"Обрати цю дату 👌"</b>'
                                    f' або оберіть іншу.', reply_markup=choose_kb)
    await state.update_data(last_msg_id=msg.message_id, calendar_msg_id=cal_msg.message_id)


async def none_callback_answer(call: CallbackQuery):
    await call.answer('Цікаво, а що буде якщо сюди тицнюти...')


async def choose_event_data(call: CallbackQuery, callback_data: dict, state: FSMContext,
                            calendar: GoogleCalendar, calendar_db: CalendarRepo):
    await call.answer()
    data = await state.get_data()
    await call.message.delete()
    try:
        await call.bot.delete_message(call.from_user.id, data['calendar_msg_id'])
    except:
        pass
    current = now().replace(
        year=int(callback_data['y']),
        month=int(callback_data['m']),
        day=int(callback_data['d']),
        hour=8, minute=0, second=0
    )
    now_date = ', '.join([w.capitalize() for w in current.strftime(format_time).split(', ')])
    await state.update_data(now_date=now_date)
    reserved_times = await reserved_times_list(calendar, calendar_db, current)
    text = (
        f'<b>1)</b> 🗓 Ви обрали дату: {data["now_date"]}\n'
        f'<b>2)</b> Оберіть час початку бронювання корту 👇'
    )
    reply_markup, answer = generic_available_times(
        start=localize(current).replace(hour=7, minute=0, second=0, microsecond=0),
        end=localize(current).replace(hour=21, minute=0, second=0, microsecond=0),
        reserved_times=reserved_times
    )
    if len(answer[0]) == 0:
        await state.finish()
        await call.message.answer(f'❌ Немає вільних годин на {now_date}')
        await choose_date(call.message, state)
        return
    await call.message.answer(text=text, reply_markup=reply_markup)
    await state.update_data(current=current.isoformat(), reserved_times=reserved_times)
    await EventSG.Start.set()


async def start_date_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    current = localize(datetime.fromisoformat(data['current']))
    text = (
        f'<b>1)</b> 🗓 Ви обрали дату: {data["now_date"]}\n\n'
        '<b>2)</b> 🆕 Час\n'
        f'<b>Початок</b>: {msg.text}\n\n'
        f'Оберіть час кінця бронювання корту 👇'
    )
    await state.update_data(start_date=msg.text)
    start = current.replace(hour=int(msg.text.split(':')[0]), minute=int(msg.text.split(':')[-1]),
                            second=0, microsecond=0)
    if start.hour == 21:
        end = start + timedelta(hours=1)
    else:
        end = start + timedelta(hours=3)
    reply_markup, answer = generic_available_times(
        start=start,
        end=end,
        reserved_times=data['reserved_times'],
        remove_start=True
    )
    if answer is None:
        await state.finish()
        await msg.answer('Немає вільних годин')
        await choose_date(msg, state)
        return
    await msg.answer(text, reply_markup=reply_markup)
    await EventSG.End.set()


async def end_date_save(msg: Message, state: FSMContext, user_db: UserRepo, sub_db: SubRepo,
                        calendar_db: CalendarRepo, calendar: GoogleCalendar):
    data = await state.get_data()
    user = await user_db.get_user(msg.from_user.id)
    subs = await sub_db.get_subs_by_user_id(user.user_id)
    start_date = data['start_date']
    end_date = msg.text
    current_day = localize(datetime.fromisoformat(data['current']))
    start = current_day.replace(hour=int(start_date.split(':')[0]), minute=int(start_date.split(':')[-1]))
    end = current_day.replace(hour=int(end_date.split(':')[0]), minute=int(end_date.split(':')[-1]))
    if start.strftime('%a').capitalize() in ('Сб', 'Нд'):
        if start.hour >= 17:
            sub_type = SubTypeEnum.HOLEVENING
        else:
            sub_type = SubTypeEnum.HOLMORNING
    else:
        if start.hour >= 17:
            sub_type = SubTypeEnum.WEEKEVENING
        else:
            sub_type = SubTypeEnum.WEEKMORNING
    reply_markup = calendar_kb
    subs = [sub for sub in subs if sub.type in (sub_type, SubTypeEnum.ALL) and all(
        [sub.status == SubStatusEnum.ACTIVE, sub.total_hours > 0]
    )]
    if subs:
        reply_markup = confirm_event_kb
        await state.update_data(subs=[sub.sub_id for sub in subs])
    await msg.answer('Перевіряю вільні місця')
    await msg.answer('⏳')
    court, times, reserved_times = await check_time_is_free(calendar_db, calendar, start, end)
    if court is None:
        await msg.answer(f'Цей час вже зайнятий\n{times}\n\nОберіть інший час 👇', reply_markup=no_times_kb(current_day))
        await state.update_data(reserved_times=reserved_times)
        await EventSG.Start.set()
        return
    else:
        await state.update_data(calendar_id=court.calendar_id)
    amount = amount_solution(user, time=(start, end))
    text = (
        f'🗓 Ви обрали дату: <b>{data["now_date"]}</b>\n\n'
        f'⏰Початок: <b>{start_date}</b>\n'
        f'⏰Кінець: <b>{msg.text}</b>\n'
        f'💸Ціна: <b>{amount}</b>\n'
        f'📍Корт: <b>{court.name}</b>, {court.location}\n\n'
        f'Підтвердіть свій вибір 👇'
    )
    await msg.answer(text, reply_markup=reply_markup)
    await state.update_data(end_date=msg.text)
    await EventSG.Confirm.set()


async def user_sub_choose(msg: Message, sub_db: SubRepo, state: FSMContext):
    text = ''
    data = await state.get_data()
    subs = [await sub_db.get_sub(int(sub_id)) for sub_id in data['subs']]
    for sub in subs:
        text += f'🎟 Абонемент №{sub.sub_id} ({sub.description})\nЗалишилось годин: {sub.total_hours}\n\n'
    await msg.answer(text, reply_markup=subs_kb([sub for sub in subs if sub.status == SubStatusEnum.ACTIVE]))
    await EventSG.Confirm.set()


async def confirm_event(msg: Message, calendar: GoogleCalendar, calendar_db: CalendarRepo,
                        state: FSMContext, fondy: FondyAPIWrapper, event_db: EventRepo,
                        user_db: UserRepo, scheduler: ContextSchedulerDecorator, sub_db: SubRepo,
                        sheet: GoogleSheet, config: Config):
    await msg.answer('Резервую ваш час')
    await msg.answer('⏳')
    format_hours = '%H:%M'
    data = await state.get_data()
    end_date = data['end_date']
    start_date = data['start_date']
    current_day = localize(datetime.fromisoformat(data['current']))
    end = current_day.replace(hour=int(end_date.split(':')[0]), minute=int(end_date.split(':')[-1]))
    start = current_day.replace(hour=int(start_date.split(':')[0]), minute=int(start_date.split(':')[-1]))
    user = await user_db.get_user(msg.from_user.id)
    court = await calendar_db.get_calendar(data['calendar_id'])
    hours = int((end - start).seconds / 3600)
    sub = False
    if msg.text.startswith('Абонемент'):
        sub_id = int(msg.text.split('#')[-1])
        sub = await sub_db.get_sub(sub_id)
        if sub.total_hours >= hours:
            await sub_db.update_sub(sub_id, total_hours=sub.total_hours-hours)
            if sub.total_hours-hours == 0:
                await sub_db.update_sub(sub.sub_id, status=SubStatusEnum.PASSED)
        else:
            await msg.answer(f'Не вистачає годин для вашого абонементу (Залишилось {sub.total_hours})\n'
                             f'Оплатити замовлення?',
                             reply_markup=choose_sub_kb)
            return
    event = await event_db.add(
        user_id=msg.from_user.id,
        calendar_id=court.google_id,
        start=start.replace(tzinfo=None),
        end=end.replace(tzinfo=None)
    )
    amount = amount_solution(user, event)
    log.warning('CREATE CALENDAR EVENT')
    calendar_event = calendar.create_event(
        name=f'(№{event.event_id}) {user.full_name} ({court.name})', calendar_id=court.google_id,
        start=start, end=end, user=user
    )
    text = (
        f'<b>3)</b>🧾 Замовлення оренди корту №{event.event_id}\n\n'
        f'🗓Дата: <b>{start.strftime(format_time)}</b>\n'
        f'⏰Час: <b>з {start.strftime(format_hours)} до {end.strftime(format_hours)}</b>\n'
        f'💸Ціна: <b>{amount} грн.</b>\n'
        f'📍Корт: {court.location} (<b>{court.name}</b>)\n'
    )
    add_text = (
        f'\n\nℹ Ми зарезервували цей час для вас на 15 хв. '
        f'Оплатіть послугу для підтверження замовлення.\n\n'
    )
    if user.status == UserStatusEnum.VIP:
        text += 'Ваше замовленя заброньовано без передоплати'
        await msg.answer(text)
        await event_db.update_event(event.event_id, google_id=calendar_event['id'], status=EventStatusEnum.PAID)
        sheet.write_event(event, user, config.misc.spreadsheet, court)
        await start_cmd(msg, user_db, state, sheet, config)
        return
    if sub:
        text += f'Години списані з вашого абонементу'
        await msg.answer(text)
        calendar.event_paid(court.google_id, calendar_event['id'], user)
        await event_db.update_event(event.event_id, google_id=calendar_event['id'], status=EventStatusEnum.PAID,
                                    price=0)
        await start_cmd(msg, user_db, state, sheet, config)
        sheet.write_event(event, user, config.misc.spreadsheet, court)
        for admin_id in config.bot.admin_ids:
            try:
                event_link = 'https://docs.google.com/spreadsheets/d/{}/edit#gid=1781353891&range=A{}:D{}'.format(
                    config.misc.spreadsheet, event.event_id + 1, event.event_id + 1
                )
                text = (
                    f'🆕 (№{event.event_id}) Нова оренда корту заброньована користувачем {user.full_name}\n\n'
                    f'Тип оплати: Абонементn\n'
                    f'📌 Дата: {event.start.strftime("%A %d, %B")} з {event.start.strftime("%H:%M")} по '
                    f'{event.end.strftime("%H:%M")}\n\n'
                    f'📚 <a href="{event_link}">Ця подія в таблиці</a>'
                )
                await msg.bot.send_message(admin_id, text)
            except:
                pass
        return
    text += add_text
    # ORDER CREATION
    description = (
        f'№{event.event_id} Оплата оренди корту {court.name} {start.strftime(format_time)} '
        f'з {start.strftime(format_hours)} до {end.strftime(format_hours)}. Користувач'
        f'{user.full_name} ({user.user_id}), тел. {user.phone_number}'
    )
    order = await fondy.create_order(description=description, amount=amount, user=user, event_id=event.event_id)
    msg = await msg.answer(text, reply_markup=pay_kb(order['url'], event_id=event.event_id))
    job = scheduler.add_job(
        name=f'Перевірка оплати №{event.event_id}', func=check_order_polling,
        trigger='interval', seconds=6, max_instances=5,
        kwargs=dict(
            msg=msg, event=event, user_db=user_db, event_db=event_db, fondy=fondy,
            calendar=calendar, hours=hours, calendar_db=calendar_db,
            sheet=sheet
        )
    )
    await event_db.update_event(
        event.event_id,
        order_id=order['order_id'],
        google_id=calendar_event['id'],
        price=amount,
        job_id=job.id
    )
    log.warning('CREATE SHEET EVENT')
    sheet.write_event(event, user, config.misc.spreadsheet, court)
    await state.finish()


async def non_state(msg: Message):
    await msg.answer('Будь ласка оплатіть бронювання')


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(pagination_calendar, days_cb.filter(), state='*')
    dp.register_callback_query_handler(none_callback_answer, none_cb.filter(), state='*')
    dp.register_callback_query_handler(choose_event_data, choose_day_cb.filter(), state='*')
    dp.register_callback_query_handler(decline_event, pay_cb.filter(), state='*')

    dp.register_message_handler(choose_type, text='Нова оренда  ➕', state='*')
    dp.register_message_handler(choose_date, text='Оренда годин 🕜', state='*')
    dp.register_message_handler(choose_date, state=EventSG.Calendar)
    dp.register_message_handler(start_date_save, state=EventSG.Start)
    dp.register_message_handler(end_date_save, state=EventSG.End)
    dp.register_message_handler(user_sub_choose, state='*', text='Використати абонемент')
    dp.register_message_handler(confirm_event, state=EventSG.Confirm)


async def decline_event(
    call: CallbackQuery, callback_data: dict,
    event_db: EventRepo,
    user_db: UserRepo,
    calendar_db: CalendarRepo,
    calendar: GoogleCalendar,
    sub_db: SubRepo,
    scheduler: ContextSchedulerDecorator,
    sheet: GoogleSheet, config: Config
):
    await call.answer()
    await call.message.delete_reply_markup()
    event_id = int(callback_data.get('event_id'))
    if callback_data.get('type') == 'event':
        event = await event_db.get_event(event_id)
        await call.message.answer(f'Замовленя #{event.event_id} скасовано', reply_markup=menu_kb)
        user = await user_db.get_user(event.user_id)
        court = await calendar_db.get_calendar_by_google_id(event.calendar_id)
        if scheduler.get_job(event.job_id):
            scheduler.remove_job(event.job_id)
        calendar.delete_event(event.calendar_id, event.google_id)
        await event_db.update_event(event.event_id, status=EventStatusEnum.DELETED)
        sheet.write_event(event, user, config.misc.spreadsheet, court)
        await event_db.delete_event(event.event_id)
    else:
        sub = await sub_db.get_sub(event_id)
        await call.message.answer(f'Абонемент №{sub.sub_id} скасовано', reply_markup=menu_kb)
        user = await user_db.get_user(sub.sub_id)
        if scheduler.get_job(sub.job_id):
            scheduler.remove_job(sub.job_id)
        await sub_db.update_sub(sub.sub_id, status=SubStatusEnum.PASSED)
        sheet.write_event(sub, user, config.misc.spreadsheet)
        await sub_db.delete_sub(event_id)


async def check_order_polling(
        msg: Message,
        event: Event,
        user_db: UserRepo,
        event_db: EventRepo,
        calendar_db: CalendarRepo,
        fondy: FondyAPIWrapper,
        calendar: GoogleCalendar,
        hours: int,
        sheet: GoogleSheet, config: Config,
        scheduler: ContextSchedulerDecorator,
):
    try:
        now_date = event.created_at
        check = await fondy.check_order(event.order_id)
        if (now() - now_date).seconds > 60*15:
            await delete_event(msg, event, event_db, user_db, calendar_db, sheet, calendar, config)
            scheduler.get_job(event.job_id).remove()
        if await event_db.get_event(event.event_id) is None:
            return
        if check:
            log.info(f'Замовлення №{event.event_id} успішно оплчено')
            await msg.delete_reply_markup()
            user = await user_db.get_user(event.user_id)
            court = await calendar_db.get_calendar_by_google_id(event.calendar_id)
            scheduler.get_job(event.job_id).remove()
            await user_db.update_user(user.user_id, hours=user.hours + hours)
            await check_user_status(user, msg, user_db)
            await event_db.update_event(event.event_id, status=EventStatusEnum.PAID)
            await msg.reply(f'Замовлення №{event.event_id} успішно оплачено ✅', reply_markup=menu_kb)
            await msg.answer(guide_text)
            calendar.event_paid(event.calendar_id, event.google_id, user)
            sheet.write_event(await event_db.get_event(event.event_id), user, config.misc.spreadsheet, court)
            for admin_id in config.bot.admin_ids:
                try:
                    event_link = 'https://docs.google.com/spreadsheets/d/{}/edit#gid=1781353891&range=A{}:D{}'.format(
                        config.misc.spreadsheet, event.event_id + 1, event.event_id + 1
                    )
                    text = (
                        f'🆕 (№{event.event_id}) Нова оренда корту заброньована користувачем {user.full_name}\n\n'
                        f'📌 Дата: {event.start.strftime("%A %d, %B")} з {event.start.strftime("%H:%M")} по '
                        f'{event.end.strftime("%H:%M")}\n\n'
                        f'📚 <a href="{event_link}">Ця подія в таблиці</a>'
                    )
                    await msg.bot.send_message(admin_id, text=text)
                except:
                    pass
    except Exception as Error:
        error = str(Error).replace('<', '').replace('>', '')
        user = await user_db.get_user(event.user_id)
        log.warning(f'Помилка оплати #{event.event_id}\n\n{error}\n')
        await msg.answer(f'❌ Оплата оренди №{event.event_id} не була зафіксована через помилку\n\n{error}\n\n'
                         f'Будь-ласка зв\'яжіться з адміністрацією для уточнення.')
        for admin_id in config.bot.admin_ids:
            await msg.bot.send_message(admin_id, f'❌ Оплата від користувача {user.full_name} (№{event.event_id}) '
                                                 f'була не зарахована через помилку\n\n{Error}\n\n'
                                                 f'Номер телефону: {user.phone_number}')
        scheduler.get_job(event.job_id).remove()


async def delete_event(msg: Message, event: Event, event_db: EventRepo,  user_db: UserRepo, calendar_db: CalendarRepo,
                       sheet: GoogleSheet,  calendar: GoogleCalendar, config: Config,):
    calendar.delete_event(event.calendar_id, event.google_id)
    user = await user_db.get_user(event.user_id)
    court = await calendar_db.get_calendar_by_google_id(event.calendar_id)
    sheet.write_event(event, user, config.misc.spreadsheet, court)
    await event_db.delete_event(event.event_id)
    await msg.answer(f'Ваше бронювання №{event.event_id} було видалено, через неоплату', reply_markup=menu_kb)


async def check_order_sub_polling(
        msg: Message,
        sub: Subscribe,
        sub_db: SubRepo,
        user_db: UserRepo,
        fondy: FondyAPIWrapper,
        sheet: GoogleSheet, config: Config,
        scheduler: ContextSchedulerDecorator
):
    try:
        now_date = sub.created_at
        await sub_db.get_sub(sub.sub_id)
        check = await fondy.check_order(sub.order_id)
        log.info(check)
        if (now() - now_date).seconds > 60*15:
            await delete_sub(msg, sub, sub_db, user_db, sheet, config)
            scheduler.get_job(sub.job_id).remove()
        if check:
            user = await user_db.get_user(sub.user_id)
            scheduler.get_job(sub.job_id).remove()
            await user_db.update_user(user.user_id, hours=user.hours + 10)
            await check_user_status(user, msg, user_db)
            await sub_db.update_sub(sub.sub_id, total_hours=sub.total_hours, status=SubStatusEnum.ACTIVE)
            await msg.delete_reply_markup()
            await msg.reply(f'Оплата абонементу №{sub.sub_id} успішно оплачено', reply_markup=menu_kb)
            sheet.write_event(await sub_db.get_sub(sub.sub_id), user, config.misc.spreadsheet)
            for admin_id in config.bot.admin_ids:
                try:
                    text = (
                        f'🆕⭐ (№{sub.sub_id}) Новий абонемент придбаний користувачем {user.full_name}\n\n'
                        f'📌 Дата: {localize(sub.created_at).strftime("%A %d, %B")}\n'
                        f'Додаткова інформація: {sub.description}'
                    )
                    await msg.bot.send_message(admin_id, text=text)
                except:
                    pass
    except Exception as Error:
        error = str(Error).replace('<', '').replace('>', '')
        user = await user_db.get_user(sub.user_id)
        log.warning(f'Помилка оплати #{sub.sub_id}\n\n{Error}\n')
        await msg.answer(f'❌ Оплата абонементу №{sub.sub_id} не була зафіксована через помилку\n\n{error}\n\n'
                         f'Будь-ласка зв\'яжіться з адміністрацією для уточнення.')
        for admin_id in config.bot.admin_ids:
            await msg.bot.send_message(admin_id, f'❌ Оплата від користувача {user.full_name} (№{sub.sub_id}) '
                                                 f'була не зарахована через помилку\n\n{error}\n\n'
                                                 f'Номер телефону: {user.phone_number}')
        scheduler.get_job(sub.job_id).remove()


async def delete_sub(msg: Message, sub: Subscribe, sub_db: SubRepo, user_db: UserRepo, sheet: GoogleSheet,
                     config: Config):
    await sub_db.delete_sub(sub.sub_id)
    user = await user_db.get_user(sub.user_id)
    sheet.write_event(sub, user, config.misc.spreadsheet)
    await msg.answer(f'Оплата абонементу №{sub.sub_id} скасована через неоплату', reply_markup=menu_kb)


async def check_user_status(user: User, msg: Message, user_db: UserRepo):
    if user.hours >= 20 and user.status == UserStatusEnum.COMMON:
        await user_db.update_user(user.user_id, status=UserStatusEnum.REGULAR)
        await msg.answer('🥳 Вітаємо! Сума ваших замовлених оренд перевищила 20 годин. '
                         'Ви отримали статус Постійного клієнта та знижку на аренду кортів 10%')


async def check_time_is_free(calendar_db: CalendarRepo, calendar: GoogleCalendar,
                             start: datetime, end: datetime):
    end = localize(end)
    start = localize(start)
    times = ''
    reserved_times_answer_cache = []
    for court in await calendar_db.get_all():
        calendar.insert_calendar(court.google_id)
        reserved_times = calendar.reserved_time(court.google_id, start)
        times += f'\nКорт №{court.calendar_id}:'
        times += ''.join([f'\n▫ {t}' for t in reserved_times]) if reserved_times else ' Відсутні'
        reserved_times_date = []

        for t in reserved_times:
            reserved_times_answer_cache.append(t)
            start_str, end_str = t.split(' - ')
            start_date = start.replace(hour=int(start_str.split(':')[0]), minute=int(start_str.split(':')[1]))
            end_date = start.replace(hour=int(end_str.split(':')[0]), minute=int(end_str.split(':')[1]))
            reserved_times_date.append((start_date, end_date))

        check = []
        for t in reserved_times_date:
            reserved_start, reserved_end = t
            if reserved_start < end < reserved_end:
                check.append(False)
            elif reserved_start < start < reserved_end:
                check.append(False)
            elif start == reserved_start or end == reserved_end:
                check.append(False)
            else:
                check.append(True)
        if all(check):
            return court, '', []
    reserved_times_answer = []

    for t in list(set(reserved_times_answer_cache)):
        if reserved_times_answer_cache.count(t) > 1:
            reserved_times_answer.append(t)
    return None, times, list(reserved_times_answer)


guide_text = (
    'Вартість для одночасного перебування на корті не більше 6 осіб. '
    'Доплата за кожну особу додатково - 100 грн. за годину\n\n'
    '‼️Правила‼️\n\n'
    '1. Відмінити бронювання можна не пізніше ніж за 8 годин.⏳\n'
    '2. Потрібно мати змінні капці або ж придбати одноразові на рецепції.\n'
    '3. Не можна виносити їжу на пісок.\n'
    '4. Не можна виносити напої, окрім води у пластмасовій пляшці на пісок.\n'
    '5. Не можна перебувати на корті з голим торсом.\n'
    '6. Треба вирівняти корт після себе (почати за 5хв до кінця броні).\n'
    '7. Обов‘язково мати при собі гарний настрій!☺\n'
)