from app.keyboards.inline.base import *

pay_cb = CallbackData('pay', 'type', 'event_id')
confirm_event_cb = CallbackData('confirm', 'action', 'event_id')
payback_cb = CallbackData('payback', 'card', 'price', 'action', 'user_id')


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


def confirm_payback_kb(card: str, price: int, user_id: int):
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton('Підтвердити', callback_data=payback_cb.new(
                card=card, price=price, action='true', user_id=user_id
            ))],
            [InlineKeyboardButton('Скасувати', callback_data=payback_cb.new(
                card='', price=1, action='false', user_id=user_id
            ))]
        ]
    )


