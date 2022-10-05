from aiogram import Bot
from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.keyboards.inline.pay import confirm_event_kb
from app.misc.utils import now, localize
from app.services.repos import UserRepo, EventRepo


async def setup_executors(scheduler:  ContextSchedulerDecorator):
    scheduler.add_job(confirm_user_event, trigger='cron', hour=7, minute=30)


async def confirm_user_event(session: sessionmaker, bot: Bot, config: Config):
    session: AsyncSession = session()
    user_db = UserRepo(session)
    event_db = EventRepo(session)
    events = await event_db.get_event_today()
    format_time = '%d.%m.%y'
    for event in events:
        if localize(event.start).strftime(format_time) == now().strftime(format_time):
            format_time = '%H:%M'
            text = (
                f'🔔 Ваше бронювання корту сьогодні о {event.start.strftime(format_time)}\n'
            )
            user = await user_db.get_user(event.user_id)
            try:
                await bot.send_message(chat_id=user.user_id, text=text, reply_markup=confirm_event_kb(event.event_id))
            except:
                for chat_id in config.bot.admin_ids:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f'Користувач {user.full_name}, {user.phone_number} ({user.user_id}) '
                             f'видалив чат з ботом але має активне бронювання'
                    )
    await session.commit()
    await session.close()
