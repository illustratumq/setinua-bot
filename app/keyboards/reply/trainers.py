from app.keyboards.reply.back import back_bt
from app.keyboards.reply.base import *

trainers_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [KeyboardButton('Світлана Бабуріна 🏆🙎‍♀')],
        [KeyboardButton('Віталій Стадніков 🏆🙎‍♂')],
        [KeyboardButton('Костянтин Куць 🏆🙎‍♂')],
        [KeyboardButton('Махно Інна та Ірина 🏆🙎‍♀🙎‍♀')],
        [KeyboardButton('Дитячі групи')],
        [back_bt]
    ]
)