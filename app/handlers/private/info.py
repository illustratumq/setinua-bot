from pathlib import Path

from aiogram import Dispatcher
from aiogram.types import Message, InputFile

from app.keyboards.reply.back import back_kb


async def typical_question(msg: Message):
    text = (
        '<b>Знижка для постійних клієнтів - 10% від вартості оренди кортів.</b> '
        'Нараховується автоматично при наявності 20+ годин оренди через чат-бот.\n\n'
        'Для Вашої зручності оплата також здійснюється через чат-бот💙. '
        'Це цілком надійно, дані Вашої платіжної карти не зберігаються.\n\n'
        'В розділі «Мій профіль🙎‍♂️🙍‍♀️» можна:\n'
        '1- переглянути Вашу історію з оренди кортів\n'
        '2- скасувати візит та повернути кошти.Гроші можна зачислити в свій абонемент або повернути на платіжну карту.'
    )
    await msg.answer_photo(photo=InputFile(Path('data', 'prices.jpg')), caption=text, reply_markup=back_kb)
    # await msg.answer(text, reply_markup=back_kb)


async def about_complex(msg: Message):
    text = (
        '<b>СЕТ - центр пляжних видів спорту 🇺🇦.</b>\n\n'
        'Тренуйся, грай, відпочивай на теплому піску цілий рік.\n'
        '«СЕТ», бери друзів, сім\'ю і до нас – тренуйся, грай, відпочивай на теплому піску цілий рік.🏖\n'
        '✔️ 1200 квадратних метрів піску з подігрівом.\n'
        '✔️ 4 критих кортів.\n'
        '✔️ 6 видів спорту.\n'
        '✔️ групові та індивідуальні тренування.\n'
        '✔️ температура повітря та піску на кортах 16-19 градусів.\n'
        '✔️ роздягальні\n'
        '✔️ душ🚿\n'
        '✔️тренажери\n'
        '✔️ лаунж\n'
        '✔️ кафе\n\n'
        '🕐 Працюємо з 7:00 до 22:00\n'
        '📍м. Київ, Х парк. ➡ <a href="https://maps.app.goo.gl/nvXPj6183aoYF9Dq5?g_st=ic">Посилання на карту</a>\n'
        '📲 098 522 69 68\n\n'
        '<b>Instagram:</b> https://instagram.com/set.in.ua\n\n'
        'https://set.in.ua/\n\n'
        'СЕТ - завжди гарна погода!☀\n\n'
        '‼️Правила‼️\n\n'
        '1. Відмінити бронювання можна не пізніше ніж за 8 годин.⏳\n'
        '2. Потрібно мати змінні капці або ж придбати одноразові на рецепції.\n'
        '3. Не можна виносити їжу на пісок.\n'
        '4. Не можна виносити напої окрім води у пластмасовій пляшці на пісок.\n'
        '5. Не можна перебувати на корті з голим торсом.\n'
        '6. Треба вирівняти корт після себе(почати за 5хв до кінця броні).\n'
        '7. Обов‘язково мати при собі гарний настрій!☺\n'
    )
    await msg.answer(text, reply_markup=back_kb)


async def others(msg: Message):
    text = (
        '<b>Інші послуги</b>:\n\n'
        '1. Оренда кортів\n'
        '2. Оренда м‘ячів\n'
        '3. Тренування та турніри\n'
        '4. Дитячі свята\n'
        '5. Дні народження / Корпоративи\n'
        '6. Аренда бару\n'
        '7. Масажний кабінет\n'
    )
    await msg.answer(text, reply_markup=back_kb)


def setup(dp: Dispatcher):
    dp.register_message_handler(typical_question, text='Ціни 💸', state='*')
    dp.register_message_handler(about_complex, text='Про комплекс 🏐', state='*')
    dp.register_message_handler(others, text='Інші послуги ℹ', state='*')
