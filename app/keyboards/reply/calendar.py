from app.keyboards.reply.back import back_bt
from app.keyboards.reply.base import *
from app.models.subscribe import Subscribe

calendar_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Підтведжую ✅'),
            KeyboardButton('Відмінити ❌')
        ]
    ]
)

confirm_event_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Використати абонемент')
        ],
        [
            KeyboardButton('Підтведжую ✅'),
            KeyboardButton('Відмінити ❌')
        ]
    ]
)


def subs_kb(subs: list[Subscribe]):
    keyboard = [[KeyboardButton(f'Абонемент #{sub.sub_id}')] for sub in subs]
    keyboard.append([KeyboardButton('Відмінити ❌')])
    return ReplyKeyboardMarkup(
        row_width=1,
        resize_keyboard=True,
        one_time_keyboard=True,
        keyboard=keyboard
    )


def kort_kb(count: int):
    keyboard = []
    cache = []
    num = 0
    for i in range(1, count + 1):
        cache.append(KeyboardButton(f'Корт #{i}'))
        if num == 2:
            keyboard.append(cache)
            cache = []
            num = 0
    if num <= 2:
        keyboard.append(cache)
    keyboard.append([back_bt])
    return ReplyKeyboardMarkup(
        row_width=2,
        one_time_keyboard=True,
        resize_keyboard=True,
        keyboard=keyboard
    )