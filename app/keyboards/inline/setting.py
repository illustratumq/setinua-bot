from app.keyboards.inline.base import *


def call_me_kb(user_id: int):
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [
                InlineKeyboardButton('Відкрити чат 💬', url=f'tg://user?id={user_id}')
            ]
        ]
    )