import logging

from aiogram import Dispatcher

from app.handlers import error, group, private

log = logging.getLogger(__name__)


def setup(dp: Dispatcher):
    error.setup(dp)
    private.setup(dp)
    log.info('Handlers are successfully configured')
