from app.keyboards.reply.back import back_bt
from app.keyboards.reply.base import *
from app.models.event import Event

events_kb = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Видалити подію')
        ],
        [
            back_bt
        ]
    ]
)


def delete_event_kb(events: list[Event]):
    keyboard = [
        [KeyboardButton(f'Замовлення #{event.event_id}')] for event in events
    ]
    keyboard.append([back_bt])
    return ReplyKeyboardMarkup(
        row_width=1,
        resize_keyboard=True,
        one_time_keyboard=True,
        keyboard=keyboard
    )


choose_sub_kb = ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[
        [
            KeyboardButton('Підтведжую ✅'),
            KeyboardButton('Відмінити ❌')
        ],
        [
            KeyboardButton('Вибрати абонемент')
        ]
    ]
)