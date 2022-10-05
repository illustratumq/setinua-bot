from app.keyboards.inline.base import *

pay_cb = CallbackData('pay', 'type', 'event_id')
confirm_event_cb = CallbackData('confirm', 'action', 'event_id')


def pay_kb(url: str, event_id: int, type_: str = 'event'):
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [
                InlineKeyboardButton('Оплатити 💳', url=url),
            ],
            [
                InlineKeyboardButton('Скасувати ❌', callback_data=pay_cb.new(
                    event_id=event_id, type=type_
                ))
            ]
        ]
    )


def confirm_event_kb(event_id: int):
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    'Дякую, що нагадали 👌',
                    callback_data=confirm_event_cb.new(event_id=event_id, action='true')
                )
            ],
            [
                InlineKeyboardButton(
                    'Відмінити замовлення',
                    callback_data=confirm_event_cb.new(event_id=event_id, action='false')
                )
            ]
        ]
    )


