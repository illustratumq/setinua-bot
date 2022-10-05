import logging
from datetime import datetime, timedelta


from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery
from apscheduler_di import ContextSchedulerDecorator

from app.config import Config
from app.keyboards.reply.events import choose_sub_kb
from app.models.calendar import Calendar
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

format_time = '%B, %d, %A'
locale.setlocale(locale.LC_ALL, 'uk_UA.UTF8')
log = logging.getLogger(__name__)


async def reserved_times_list(calendar: GoogleCalendar, calendar_db: CalendarRepo, day: datetime):
    answer_times = []
    res_times_cache = []
    courts = len(await calendar_db.get_all())
    if courts == 0:
        return []
    for court in await calendar_db.get_all():
        res_times = calendar.reserved_time(court.google_id, day)
        for t in res_times:
            res_times_cache.append(t)
    for t in res_times_cache:
        if res_times_cache.count(t) == courts:
            answer_times.append(t)
    return list(set(answer_times))


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
        f'<b>1)</b> 🗓 Оберіть дату оренди\n\n'
        f'Поточна дата: {now_date}\n'
    )
    await state.update_data(reserved_times=[])
    await msg.answer(text, reply_markup=create_calendar_kb(now()))


async def pagination_calendar(call: CallbackQuery, callback_data: dict, state: FSMContext,
                              calendar: GoogleCalendar, calendar_db: CalendarRepo):
    current_day = now().replace(
        year=int(callback_data['y']),
        month=int(callback_data['m']),
        day=int(callback_data['d']),
    )
    if localize(current_day).replace(hour=22, minute=0) < now():
        await call.answer('Вибрана дата вже недоступна', show_alert=True)
        return
    await call.answer()
    await call.message.delete_reply_markup()
    now_date = ', '.join([w.capitalize() for w in current_day.strftime(format_time).split(', ')])
    text = (
        f'<b>1)</b> 🗓 Ви обрали дату: {now_date}\n'
        f'<b>2)</b> Оберіть час оренди 👇\n\nкнопка "Обрати час 🗓"'
    )
    reserved_times = await reserved_times_list(calendar, calendar_db, current_day)
    await state.update_data(reserved_times=reserved_times, now_date=now_date)
    await call.message.edit_text(text, reply_markup=create_calendar_kb(current_day))


async def none_callback_answer(call: CallbackQuery):
    await call.answer('Цікаво, а що буде якщо сюди тицнюти...')


async def choose_event_data(call: CallbackQuery, callback_data: dict, state: FSMContext,
                            calendar: GoogleCalendar, calendar_db: CalendarRepo):
    await call.answer()
    await call.message.delete()
    current = now().replace(
        year=int(callback_data['y']),
        month=int(callback_data['m']),
        day=int(callback_data['d']),
        hour=8, minute=0, second=0
    )
    now_date = ', '.join([w.capitalize() for w in current.strftime(format_time).split(', ')])
    await state.update_data(now_date=now_date)
    data = await state.get_data()
    reserved_times = await reserved_times_list(calendar, calendar_db, current)
    text = (
        f'<b>1)</b> 🗓 Ви обрали дату: {data["now_date"]}\n'
        f'<b>2)</b> Оберіть час початку бронювання корту 👇'
    )
    reply_markup = generic_available_times(
        start=localize(current.replace(hour=7, minute=0, second=0, microsecond=0)),
        end=localize(current.replace(hour=21, minute=0, second=0, microsecond=0)),
        reserved_times=reserved_times
    )
    if reply_markup is None:
        await state.finish()
        await call.message.answer('Немає вільних годин')
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
    reply_markup = generic_available_times(
        start=start,
        end=end,
        reserved_times=data['reserved_times'],
        remove_start=True
    )
    if reply_markup is None:
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
    subs = [sub for sub in subs if sub.type in (sub_type, SubTypeEnum.ALL) and sub.status == SubStatusEnum.ACTIVE]
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
    text = (
        f'<b>1)</b> 🗓 Ви обрали дату: {data["now_date"]}\n\n'
        '<b>2)</b> 🆕 Нове бронювання\n'
        f'<b>Початок</b>: {start_date}\n'
        f'<b>Кінець</b>: {msg.text}\n'
        f'📍 Корт: {court.location} (Корт {court.name})\n\n'
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
        text += f'Підписка #{sub.sub_id}\n{sub.description}\nЗалишилось годин: {sub.total_hours}\n\n'
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
        f'Дата: {start.strftime(format_time)}\n'
        f'Час: {start.strftime(format_hours)} - {end.strftime(format_hours)}\n'
        f'Ціна: {amount} грн.\n'
        f'📍 Корт: {court.location} ({court.name})\n'

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
        return
    text += add_text
    # ORDER CREATION
    description = (
        f'(№{event.event_id}) Оплата оренди корту #{court.calendar_id} '
        f'{court.location} {user.full_name} ({user.user_id})'
    )
    order = await fondy.create_order(description=description, amount=amount, user=user, event_id=event.event_id)
    msg = await msg.answer(text, reply_markup=pay_kb(order['url'], event_id=event.event_id))
    job = scheduler.add_job(
        name=f'Перевірка оплати №{event.event_id}', func=check_order_polling,
        trigger='interval', seconds=3600, next_run_time=datetime.now() + timedelta(seconds=5), max_instances=5,
        kwargs=dict(msg=msg, event=event, user_db=user_db, event_db=event_db, fondy=fondy,
                    calendar=calendar, hours=hours, timeout=5, calendar_db=calendar_db,
                    sheet=sheet)
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
        await call.message.answer(f'Абонемент #{sub.sub_id} скасовано', reply_markup=menu_kb)
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
        timeout: float,
        hours: int,
        sheet: GoogleSheet, config: Config,
):
    try:
        now_date = now()
        check = False
        while not check:
            check = await fondy.check_order(event.order_id)
            # log.warning(check)
            if (now() - now_date).seconds > 60*15:
                await delete_event(msg, event, event_db, user_db, calendar_db, sheet, calendar, config)
            if await event_db.get_event(event.event_id) is None:
                break
            if check:
                log.info(f'Успішна оплата #{event.event_id}')
                await msg.delete_reply_markup()
                user = await user_db.get_user(event.user_id)
                court = await calendar_db.get_calendar_by_google_id(event.calendar_id)
                await user_db.update_user(user.user_id, hours=user.hours + hours)
                await check_user_status(user, msg, user_db)
                await event_db.update_event(event.event_id, status=EventStatusEnum.PAID)
                await msg.reply(f'Замовлення №{event.event_id} успішно оплачено', reply_markup=menu_kb)
                calendar.event_paid(event.calendar_id, event.google_id, user)
                sheet.write_event(await event_db.get_event(event.event_id), user, config.misc.spreadsheet, court)
                break
    except Exception as Error:
        log.warning(f'Помилка оплати #{event.event_id}\n\n{Error}\n')
        # time.sleep(timeout)


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
        timeout: float = 0.5,
):
    now_date = now()
    check = False
    while not check:
        await sub_db.get_sub(sub.sub_id)
        check = await fondy.check_order(sub.order_id)
        log.info(check)
        if (now() - now_date).seconds > 60*15:
            await delete_sub(msg, sub, sub_db, user_db, sheet, config)
        if check:
            user = await user_db.get_user(sub.user_id)
            await user_db.update_user(user.user_id, hours=user.hours + 10)
            await check_user_status(user, msg, user_db)
            await sub_db.update_sub(sub.sub_id, total_hours=sub.total_hours, status=SubStatusEnum.ACTIVE)
            await msg.delete_reply_markup()
            await msg.reply(f'Оплата абонементу №{sub.sub_id} успішно оплачено', reply_markup=menu_kb)
            sheet.write_event(await sub_db.get_sub(sub.sub_id), user, config.misc.spreadsheet)
            break
        time.sleep(timeout)


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
        print(court.name, court.google_id)
        reserved_times = calendar.reserved_time(court.google_id, start)
        times += f'\nКорт №{court.calendar_id}:'
        times += ''.join([f'\n▫ {t}' for t in reserved_times]) if reserved_times else ' Відсутні'
        reserved_times_date = []

        for t in reserved_times:
            print(t)
            reserved_times_answer_cache.append(t)
            start_str, end_str = t.split(' - ')
            start_date = start.replace(hour=int(start_str.split(':')[0]), minute=int(start_str.split(':')[1]))
            end_date = start.replace(hour=int(end_str.split(':')[0]), minute=int(end_str.split(':')[1]))
            reserved_times_date.append((start_date, end_date))

        check = []
        for t in reserved_times_date:
            reserved_start, reserved_end = t
            print(reserved_start, reserved_end)
            if reserved_start < end < reserved_end:
                check.append(False)
            elif reserved_start < start < reserved_end:
                check.append(False)
            elif start == reserved_start or end == reserved_end:
                check.append(False)
            else:
                check.append(True)
        print(check)
        if all(check):
            return court, '', []
    reserved_times_answer = []

    for t in list(set(reserved_times_answer_cache)):
        if reserved_times_answer_cache.count(t) > 1:
            reserved_times_answer.append(t)
    return None, times, list(reserved_times_answer)
