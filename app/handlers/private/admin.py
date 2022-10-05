from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import Message

from app.config import Config
from app.filters.admin import IsAdminFilter
from app.keyboards.reply.admin import admin_kb, status_kb, user_actions_kb
from app.keyboards.reply.back import cancel_kb
from app.keyboards.reply.calendar import calendar_kb
from app.misc.enums import UserStatusEnum, SubStatusEnum
from app.misc.utils import construct_user_status, get_status
from app.services.repos import CalendarRepo, UserRepo, SubRepo, EventRepo
from app.states.calendar import CalendarSG
from data.googlecalendar.calendar_api import GoogleCalendar
from app.states.inputs import ImportSG, UserStatusSG
from data.googlesheets.sheets_api import GoogleSheet


async def admin_menu(msg: Message):
    await msg.answer('Ви увійшли до панелі адміністратора', reply_markup=admin_kb)


async def create_calendar(msg: Message):
    text = (
        'Введіть назву календарю до 150 символів (зверніть увагу, що назва календаря '
        'відображається для користувачів при виборі аренди)'
    )
    await msg.answer(text, reply_markup=cancel_kb)
    await CalendarSG.Name.set()


async def save_calendar_name(msg: Message, state: FSMContext):
    if len(msg.text) > 150:
        return await msg.answer(f'Ваша назва календаря має містити до 150 символів, замість {len(msg.text)}')
    text = (
        'Введіть опис календаря до 500 символів (зверніть увагу, що опис календаря '
        'відображається для користувачів при виборі аренди)'
    )
    await msg.answer(text, reply_markup=cancel_kb)
    await state.update_data(name=msg.text)
    await CalendarSG.Description.set()


async def save_calendar_description(msg: Message, state: FSMContext):
    if len(msg.text) > 300:
        return await msg.answer(f'Ваш опис календаря має містити до 500 символів, замість {len(msg.text)}')
    text = (
        'Введіть локацію до 300 символів (зверніть увагу, що локація календаря '
        'відображається для користувачів при виборі аренди)'
    )
    await msg.answer(text, reply_markup=cancel_kb)
    await state.update_data(description=msg.text)
    await CalendarSG.Location.set()


async def save_calendar_location(msg: Message, state: FSMContext):
    if len(msg.text) > 300:
        return await msg.answer(f'Ваша локаія календаря має містити до 300 символів, замість {len(msg.text)}')
    await state.update_data(location=msg.text)
    data = await state.get_data()
    google_calendar_link = 'https://calendar.google.com/calendar'
    text = (
        f'📆 Календар\n\n'
        f'Назва: {data["name"]}\n'
        f'Опис: {data["description"]}\n'
        f'Локація: {msg.text}\n\n'
        f'Додайте ідентифікатор календаря.\n\n'
        f'1️⃣ Перейдіть в <a href="{google_calendar_link}">Гугл календар.</a>\n'
        f'2️⃣ Виберіть календар який хочете додати в бота із списка ліворуч. '
        f'Оберіть "Налаштування і доступ".\n'
        f'3️⃣ У розділі доступ окремих користувачів натисніть "Додати людей"\n'
        f'4️⃣ Введіть пошту сервісного акаунту* та у вкладці "Доступ" оберіть '
        f'"Вносити зміни й керувати спільним доступом"\n'
        f'5️⃣ У вкладці "Інтеграція календаря" скопіюйте Ідентифікатор календаря та наділшіть мені.\n\n'
        f'* - setcalendar@setinuacalendar.iam.gserviceaccount.com'
    )
    await msg.answer(text, reply_markup=cancel_kb)
    await CalendarSG.Mail.set()


async def save_calendar_mail(msg: Message, state: FSMContext, calendar: GoogleCalendar):
    await msg.delete()
    await state.update_data(mail=msg.text)
    try:
        await msg.answer('⏳')
        await msg.answer('Перевіряю календар')
        calendar.get(msg.text)
    except Exception as Error:
        await msg.answer(f'Не зміг підключитись. Помилка: {str(Error).replace("<", "").replace(">", "")}')
        return
    await msg.answer('✅ Календар знайдено')
    await msg.answer('Підтвердіть додавання календарю', reply_markup=calendar_kb)
    await CalendarSG.Confirm.set()


async def save_calendar(
        msg: Message, state: FSMContext, calendar_db: CalendarRepo,
        calendar: GoogleCalendar
):
    await msg.answer('⏳')
    msg = await msg.answer('Підключаюсь до Гугл')
    data = await state.get_data()
    calendar.insert_calendar(data['mail'])
    calendar = calendar.update_calendar(
        calendar_id=data['mail'],
        summary=data['name'],
        description=data['description'],
        location=data['location']
    )
    msg = await msg.edit_text('⏳ Створюю календар')
    calendar = await calendar_db.add(
        name=data['name'],
        description=data['description'],
        location=data['location'],
        google_id=calendar['id']
    )
    await msg.edit_text(f'Створено календар #{calendar.calendar_id}')
    await state.finish()
    await calendar_list(msg, calendar_db)


async def calendar_list(msg: Message, calendar_db: CalendarRepo):
    calendars = await calendar_db.get_all()
    if len(calendars) == 0:
        return await msg.answer('Ви ще не додали жодного календаря')
    text = ''
    for calendar in calendars:
        text += (
            f'🗓 Календар #{calendar.calendar_id}\n'
            f'<b>Назва</b>: {calendar.name}\n'
            f'<b>Опис</b>: {calendar.description}\n'
            f'<b>Локація</b>: {calendar.location}\n'
            f'<b>GoogleId</b>: {calendar.google_id}\n\n'
        )
    await msg.answer(text, reply_markup=admin_kb)


async def import_calendar(msg: Message):
    await msg.answer('Введіть посилання на календар')
    await ImportSG.Input.set()


async def user_search(msg: Message):
    await msg.answer('Введіть id коритувача 👇')
    await UserStatusSG.User.set()


async def user_actions(msg: Message, user_db: UserRepo, event_db: EventRepo,
                       config: Config, state: FSMContext):
    user = await user_db.get_user(int(msg.text))
    if user is None:
        await msg.answer('Користувача з таким id не знайдено. Спробуйте ще раз')
        return
    else:
        user_link = 'https://docs.google.com/spreadsheets/d/{}/edit#gid=0&range=A{}:D{}'.format(
            config.misc.spreadsheet, user.spreadsheet_id, user.spreadsheet_id
        )
        events = await event_db.get_events(user.user_id)
        user_events = ''
        for event in events:
            user_events += f'Оренда №{event.event_id} ({get_status(event)})'
        text = (
            f'Ім\'я: {user.full_name}\n'
            f'Телефон: {user.phone_number}\n'
            f'Годин оренди: {user.hours}\n'
            f'Статус: <a href="{user_link}">{construct_user_status(user)}</a>\n\n'
            f'Оберіть дію 👇'
        )
        await msg.answer(text, reply_markup=user_actions_kb)
        await state.update_data(user_id=user.user_id)
        await UserStatusSG.Actions.set()


async def user_status(msg: Message):
    await UserStatusSG.Status.set()
    await msg.answer('Оберіть статус клієнта 👇', reply_markup=status_kb)


async def user_hours(msg: Message):
    await msg.answer('Введіть кількість годин 👇')
    await UserStatusSG.Hours.set()


async def user_add_hours(msg: Message, sub_db: SubRepo, state: FSMContext):
    data = await state.get_data()
    if str(msg.text).isnumeric():
        await sub_db.add(
            spreadsheet_id=len(await sub_db.get_all()) + 1,
            user_id=data['user_id'],
            description='Додані години',
            total_hours=float(msg.text),
            status=SubStatusEnum.ACTIVE,
            price=0
        )
        await msg.bot.send_message(chat_id=data['user_id'],
                                   text=f'На ваш рахунок нараховано {float(msg.text)} безкоштовних годин')
        await msg.answer('Години нараховані')
        await state.finish()
        await admin_menu(msg)


async def user_status_change(msg: Message, user_db: UserRepo, state: FSMContext, sheet: GoogleSheet, config: Config):
    data = await state.get_data()
    if msg.text == 'Новий клієнт':
        status = UserStatusEnum.COMMON
    elif msg.text == 'Постійний клієнт':
        status = UserStatusEnum.REGULAR
    elif msg.text == 'ВІП':
        status = UserStatusEnum.VIP
    else:
        status = UserStatusEnum.TRAINER
    await user_db.update_user(data['user_id'], status=status)
    user = await user_db.get_user(int(data['user_id']))
    sheet.write_user(user, config.misc.spreadsheet)
    await msg.bot.send_message(chat_id=data['user_id'], text=f'Ви отримали новий статус! {msg.text}')
    await state.finish()
    await msg.answer('Статус змінено')
    await admin_menu(msg)


def setup(dp: Dispatcher):
    dp.register_message_handler(admin_menu, Command('admin'), IsAdminFilter(), state='*')
    dp.register_message_handler(calendar_list, text='Існуючі 🗓', state='*')
    dp.register_message_handler(user_search, text='Користувачі', state='*')
    dp.register_message_handler(create_calendar, text='Додати календар ➕', state='*')

    dp.register_message_handler(save_calendar_name, state=CalendarSG.Name)
    dp.register_message_handler(save_calendar_description, state=CalendarSG.Description)
    dp.register_message_handler(save_calendar_location, state=CalendarSG.Location)
    dp.register_message_handler(save_calendar_mail, state=CalendarSG.Mail)
    dp.register_message_handler(user_actions, state=UserStatusSG.User)
    dp.register_message_handler(user_status, state=UserStatusSG.Actions, text='Змінити статус')
    dp.register_message_handler(user_hours, state=UserStatusSG.Actions, text='Додати години')
    dp.register_message_handler(user_status_change, state=UserStatusSG.Status)
    dp.register_message_handler(user_add_hours, state=UserStatusSG.Hours)

    dp.register_message_handler(save_calendar, state=CalendarSG.Confirm, text='Підтведжую ✅')


