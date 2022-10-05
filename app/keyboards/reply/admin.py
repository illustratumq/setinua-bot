from app.keyboards.reply.base import *

admin_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Додати календар ➕'),
            KeyboardButton('Існуючі 🗓')
        ],
        [
            KeyboardButton('Користувачі')
        ]
    ]
)


user_actions_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Змінити статус')
        ],
        [
            KeyboardButton('Додати години')
        ]
    ]
)


status_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Новий клієнт'),
            KeyboardButton('Постійний клієнт')
        ],
        [
            KeyboardButton('Тренер'),
            KeyboardButton('ВІП')
        ]
    ]
)