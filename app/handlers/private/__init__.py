from aiogram import Dispatcher

from app.handlers.private import start, profile, admin, event, history, info, sub


def setup(dp: Dispatcher):
    start.setup(dp)
    profile.setup(dp)
    admin.setup(dp)
    event.setup(dp)
    sub.setup(dp)
    history.setup(dp)
    info.setup(dp)



