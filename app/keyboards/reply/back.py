from app.keyboards.reply.base import *

back_bt = KeyboardButton('◀ До головного меню')

back_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [back_bt]
    ]
)

start_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('➡️ Натисніть тут 👍⬅')
        ]
    ]
)

cancel_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Відмінити ❌')
        ]
    ]
)