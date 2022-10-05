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
            KeyboardButton('Типові питання ❓'),
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

