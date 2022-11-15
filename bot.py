import asyncio
import locale
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.types import AllowedUpdates, ParseMode

from app import handlers, middlewares
from app.config import Config
from app.misc.executor import setup_executors
from data.googlecalendar.calendar_api import GoogleCalendar
from app.misc.bot_commands import set_default_commands
from app.misc.notify_admins import notify
from app.misc.scheduler import compose_scheduler
from app.services import create_db_engine_and_session_pool
from app.services.fondy import FondyAPIWrapper
from data.googlesheets.sheets_api import GoogleSheet

log = logging.getLogger(__name__)
locale.setlocale(locale.LC_ALL, 'uk_UA.UTF8')


async def main():
    config = Config.from_env()
    log_level = config.misc.log_level
    logging.basicConfig(
        level=log_level,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    log.info('Starting bot...')

    storage = RedisStorage2(host=config.redis.host, port=config.redis.port)
    bot = Bot(config.bot.token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(bot, storage=storage)
    db_engine, sqlalchemy_session_pool = await create_db_engine_and_session_pool(config.db.sqlalchemy_url, log_level)
    calendar = GoogleCalendar()
    sheets = GoogleSheet()
    fondy = FondyAPIWrapper(config.bot.fondy_merchant_id, config.bot.fondy_credit_key, credit_key=config.bot.fondyp2p)
    scheduler = compose_scheduler(config, bot, sqlalchemy_session_pool)

    allowed_updates = (
            AllowedUpdates.MESSAGE + AllowedUpdates.CALLBACK_QUERY +
            AllowedUpdates.EDITED_MESSAGE + AllowedUpdates.CHAT_JOIN_REQUEST +
            AllowedUpdates.PRE_CHECKOUT_QUERY + AllowedUpdates.SHIPPING_QUERY
    )
    environments = dict(
        config=config,
        calendar=calendar.env(),
        sheet=sheets,
        fondy=fondy,
        scheduler=scheduler
    )

    middlewares.setup(dp, environments, sqlalchemy_session_pool)
    handlers.setup(dp)

    await set_default_commands(bot)
    await notify(bot, config.bot.admin_ids)
    await setup_executors(scheduler)

    try:
        scheduler.start()
        await dp.skip_updates()
        await dp.start_polling(allowed_updates=allowed_updates, reset_webhook=True)
    finally:
        await storage.close()
        await storage.wait_closed()
        await (await bot.get_session()).close()
        await db_engine.dispose()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.warning('Bot stopped!')
