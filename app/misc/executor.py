from datetime import timedelta

from aiogram import Bot
from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.keyboards.inline.pay import confirm_event_kb
from app.misc.utils import now, localize
from app.services.repos import UserRepo, EventRepo


async def setup_executors(scheduler:  ContextSchedulerDecorator):
    scheduler.add_job(confirm_user_event, trigger='cron', hour=16, minute=20)


async def confirm_user_event(session: sessionmaker, bot: Bot, config: Config):
    session: AsyncSession = session()
    user_db = UserRepo(session)
    event_db = EventRepo(session)
    events = await event_db.get_event_paid()
    format_time_check = '%d.%m.%y'
    for event in events:
        if (now() + timedelta(days=1)).strftime(format_time_check) == localize(event.start).strftime(format_time_check):
            format_time = '%H:%M'
            format_time_day = '%A, %d %B'
            text = (
                f'🔔 Ваш запис на завтра <b>{event.start.strftime(format_time_day)}</b> з '
                f'{event.start.strftime(format_time)} по {event.end.strftime(format_time)}\n\n'
            )
            user = await user_db.get_user(event.user_id)
            try:
                await bot.send_message(chat_id=user.user_id, text=text, reply_markup=confirm_event_kb(event.event_id))
            except:
                for chat_id in config.bot.admin_ids:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f'Користувач {user.full_name}, {user.phone_number} ({user.user_id}) '
                             f'видалив чат з ботом але має активне бронювання №{event.event_id}'
                    )
    await session.commit()
    await session.close()
