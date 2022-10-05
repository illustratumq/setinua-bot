import logging

from aiogram import Bot

from app.keyboards.reply.menu import menu_kb

log = logging.getLogger(__name__)


async def notify(bot: Bot, admin_ids: tuple[int, ...]) -> None:
    for admin in admin_ids:
        try:
            await bot.send_message(admin, 'Бот запущен', reply_markup=menu_kb)
        except Exception as err:
            log.exception(err)
