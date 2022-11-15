from app.keyboards.reply.back import back_bt
from app.keyboards.reply.base import *

menu_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Нова оренда  ➕'),
        ],
        [
            KeyboardButton('Мій профіль 🙎‍♂️🙍‍♀️'),
            KeyboardButton('Тренери 🏆')
        ],
        [
            KeyboardButton('Про комплекс 🏐'),
            KeyboardButton('Ціни 💸'),
        ],
        [
            KeyboardButton('Інші послуги ℹ'),
            KeyboardButton('Передзвоніть мені 📞')
        ]
    ]
)

orenda_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Оренда годин 🕜')
        ],
        [
            KeyboardButton('Абонемент ⭐')
        ]
    ]
)

subscribe_days_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [KeyboardButton('Вихідні дні')],
        [KeyboardButton('Будні дні')]
    ]
)

subscribe_time_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [KeyboardButton('Денний час')],
        [KeyboardButton('Вечірній час')]
    ]
)

payback_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [KeyboardButton('Повернути кошти')],
        [back_bt]
    ]
)

