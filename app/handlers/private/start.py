from pathlib import Path

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InputFile, MediaGroup, InputMedia, InputMediaPhoto

from app.config import Config
from app.keyboards.inline.calendar import back_cb
from app.keyboards.reply.back import start_kb, back_kb
from app.keyboards.reply.menu import *
from app.keyboards.reply.trainers import trainers_kb
from app.services.repos import UserRepo
from app.states.inputs import TrainersSG
from data.googlesheets.sheets_api import GoogleSheet


start_text = (
    'Вас вітає чат-бот Комплексу пляжних видів спорту "СЕТ" 👋\n'
    'Перед Вами корисний інструмент:\n'
    '- для пошуку потрібної інформації про послуги\n'
    '- для швидкої оренди кортів 24/7🏐\n'
    '- для спілкування з адміністратором👩‍⚕\n'
    '- для збереження історії відвідувань та участі в системі лояльності.\n'
    'Ми спілкуємося виключно за допомогою кнопок. Вони знаходяться внизу екрану 👇'
)


async def start_cmd(msg: Message, user_db: UserRepo,
                    state: FSMContext, sheet: GoogleSheet,
                    config: Config
):
    await state.finish()
    if not await user_db.get_user(msg.from_user.id):
        if not msg.from_user.is_bot:
            await msg.answer(start_text, reply_markup=start_kb)
            user = await user_db.add(
                user_id=msg.from_user.id,
                mention=msg.from_user.get_mention(),
                full_name=msg.from_user.full_name,
                spreadsheet_id=len(await user_db.get_all()) + 1
            )
            sheet.write_user(user, config.misc.spreadsheet)
    else:
        await msg.answer('Мої вітаннячка', reply_markup=menu_kb)


async def cancel_cmd(msg: Message, state: FSMContext):
    await state.finish()
    await msg.answer('Ви відмінили дію', reply_markup=menu_kb)


async def cancel_callback_cmd(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()
    await call.message.answer('Ви відмінили дію', reply_markup=menu_kb)


def setup(dp: Dispatcher):
    dp.register_message_handler(start_cmd, text='➡️ Натисніть тут 👍⬅', state='*')
    dp.register_message_handler(start_cmd, CommandStart(), state='*')
    dp.register_message_handler(start_cmd, text='◀ До головного меню', state='*')
    dp.register_message_handler(cancel_cmd, text='Відмінити ❌', state='*')
    dp.register_callback_query_handler(cancel_callback_cmd, back_cb.filter(), state='*')
    dp.register_message_handler(trainers, text='Тренери 🏆', state='*')
    dp.register_message_handler(show_trainers, state=TrainersSG.Input)


async def trainers(msg: Message):
    text = (
        'Запишіться на тренування із нашими тренерами 🏆🙎‍♂🙎‍♀'
    )
    await msg.answer(text, reply_markup=trainers_kb)
    await TrainersSG.Input.set()


async def show_trainers(msg: Message):

    if msg.text == 'Світлана Бабуріна 🏆🙎‍♀':
        trainer_url = 'https://t.me/+kbiEuPrEF94zNjVi'
        trainer_info = (
            '<b>Світлана Бабуріна</b>\n\n'
            '🏐 Українська пляжна волейболістка, тренерка.\n'
            '🏐 Майстер спорту України міжнародного класу.\n'
            '🏐 Дванадцятиразова чемпіонка України.\n'
            '🏐 Триразова володарка Кубка України.\n'
            '🏐 Срібна призерка «Великого шолома» \n'
            '🏐 Учасниця чемпіонату світу.\n\n'
        )
        file = InputFile(Path('data', 'trainers', '1.jpg'))
        text = trainer_info + f'<a href="{trainer_url}">Записатися на тренування - розпочати чат</a>\n'
    elif msg.text == 'Віталій Стадніков 🏆🙎‍♂':
        trainer_url = 'https://t.me/+DcTwOMLLlVcyNTAy'
        trainer_info = (
            '<b>Віталій Стадніков</b>\n\n'
            '🏐 Майстер спорту, гравець збірної України з 1996 по 2005 рік.\n'
            '🏐 Тренер команди жіночої збірної України 2021 рік.\n\n'
        )
        file = InputFile(Path('data', 'trainers', '2.jpg'))
        text = trainer_info + f'<a href="{trainer_url}">Записатися на тренування - розпочати чат</a>\n'
    elif msg.text == 'Махно Інна та Ірина 🏆🙎‍♀🙎‍♀':
        trainer_url = 'https://t.me/+vowkvgRY-4k1OWJi'
        trainer_info = (
            'Махно Ірина ( 3-разова чемпіонка України), '
            'Махно Інна (5-разова чемпіонка України) - членкині національної збірної, '
            'лідерки українського пляжного волейболу, діючі спортсменки, '
            'призерки турів світової серії, '
            'входять у топ-10 найсильніших команд Європи.\n\n'
        )
        file = MediaGroup([
            InputMediaPhoto(InputFile(Path('data', 'trainers', '4.jpg'))),
            InputMediaPhoto(InputFile(Path('data', 'trainers', '5.jpg')))
        ])
        text = trainer_info + f'<a href="{trainer_url}">Записатися на тренування - розпочати чат</a>'
        await msg.answer_media_group(file)
        await msg.answer(text, reply_markup=trainers_kb)
        return
    elif msg.text == 'Дитячі групи':
        file = MediaGroup([
            InputMediaPhoto(InputFile(Path('data', 'trainers', '6.jpg'))),
            InputMediaPhoto(InputFile(Path('data', 'trainers', '7.jpg')))
        ])
        await msg.answer_media_group(file)
        text = f'1) <a href="https://t.me/+kbiEuPrEF94zNjVi">Записатися на тренування - ' \
               f'розпочати чат (Констянтин та Світлана)</a>\n' \
               f'2) <a href="https://t.me/+vowkvgRY-4k1OWJi">Записатися на тренування - ' \
               f'розпочати чат (Інна та Ірина)</a>\n'
        await msg.answer(text=text, reply_markup=trainers_kb)
        return
    else:
        trainer_url = 'https://t.me/+kbiEuPrEF94zNjVi'
        trainer_info = (
            '<b>Костянтин Куць</b>\n\n'
            '🏐 Тренер команди національної збірної\n\n'
        )
        file = InputFile(Path('data', 'trainers', '3.jpg'))
        text = trainer_info + f'<a href="{trainer_url}">Записатися на тренування - розпочати чат</a>\n'

    await msg.answer_photo(caption=text, reply_markup=trainers_kb, photo=file)
