from app.keyboards.reply.back import back_bt
from app.keyboards.reply.base import *

profile_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Мої замовлення 📚')
        ],
        [
            KeyboardButton('Редагувати ім\'я'),
            KeyboardButton('Редагувати номер телефону')
        ],
        [
            back_bt
        ]
    ]
)

contact_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Номер пристрою', request_contact=True),
            KeyboardButton('Інший номер')
        ],
        [
            back_bt
        ]
    ]
)

contact_device_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Номер пристрою', request_contact=True),
        ]
    ]
)