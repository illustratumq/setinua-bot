import calendar
import locale
from datetime import datetime, timedelta

from app.keyboards.inline.base import *
from app.misc.utils import now

days_cb = CallbackData('day', 'd', 'm', 'y')
choose_day_cb = CallbackData('choose', 'd', 'm', 'y')
none_cb = CallbackData('sleep')
back_cb = CallbackData('back')


def create_calendar_kb(current_day: datetime):
    current_day_copy = current_day
    inline_keyboard = [
        [
            InlineKeyboardButton('Календар ' + current_day.strftime('%B').lower(), callback_data=none_cb.new())
        ]
    ]
    w, monthrange = calendar.monthrange(current_day.year, current_day.month)
    week_days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']
    week_keyboard = [
        InlineKeyboardButton(day, callback_data=none_cb.new()) for day in week_days
    ]
    first_month_day = current_day.replace(day=1).strftime('%a').capitalize()
    index_first_day = week_days.index(first_month_day)
    days_keyboard = []
    num = index_first_day
    cash_list = [InlineKeyboardButton(' ', callback_data=none_cb.new()) for i in range(index_first_day)]
    if current_day.day > 1 and current_day.month == now().month:
        first_week_day = now().strftime('%a').capitalize()
        index_week_day = week_days.index(first_week_day)
        cash_list = [InlineKeyboardButton(' ', callback_data=none_cb.new()) for i in range(index_week_day)]
        num = index_week_day
    end_range = monthrange + 1
    marker = '✓'
    if current_day.day > 15 and current_day.month == now().month:
        end_range = monthrange + 15
    day = 1
    for i in range(1, end_range):
        date = current_day.replace(day=day)
        if date >= now():
            if date.strftime('%d.%m.%y') == current_day.strftime('%d.%m.%y'):
                if marker == '':
                    day_name = f'{day}{marker}'
                else:
                    day_name = f'{marker}'
            else:
                day_name = f'{day}'
            cash_list.append(
                InlineKeyboardButton(day_name, callback_data=days_cb.new(
                    y=date.year, m=date.month, d=date.day
                ))
            )
            num += 1
            if num == 7:
                days_keyboard.append(cash_list)
                cash_list = []
                num = 0
        day += 1
        if day == monthrange + 1:
            day = 1
            marker = ''
            current_day = current_day.replace(day=monthrange) + timedelta(days=1)
    if num <= 7:
        for d in [InlineKeyboardButton(' ', callback_data=none_cb.new()) for i in range(7-num)]:
            cash_list.append(d)
        days_keyboard.append(cash_list)
    inline_keyboard += [week_keyboard, *days_keyboard]
    current_day = current_day_copy
    next_month_date = current_day.replace(day=monthrange) + timedelta(days=1)
    if current_day.month - now().month == 1:
        previous_month_date = (current_day.replace(day=1) - timedelta(days=1)).replace(day=now().day)
    else:
        previous_month_date = (current_day.replace(day=1) - timedelta(days=1)).replace(day=1)
    inline_keyboard.append([
        InlineKeyboardButton('⬅', callback_data=days_cb.new(
            y=previous_month_date.year, m=previous_month_date.month, d=previous_month_date.day)),
        InlineKeyboardButton('Назад', callback_data=back_cb.new()),
        InlineKeyboardButton('➡', callback_data=days_cb.new(
            y=next_month_date.year, m=next_month_date.month, d=1))
    ])
    return InlineKeyboardMarkup(row_width=7, inline_keyboard=inline_keyboard), InlineKeyboardMarkup(
        row_width=1, inline_keyboard=[
            [
                InlineKeyboardButton('Обрати цю дату 👌', callback_data=choose_day_cb.new(
                    y=current_day.year, m=current_day.month, d=current_day.day
                ))
            ]
        ]
    )


def no_times_kb(current_day: datetime):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton('Обрати час 🗓', callback_data=choose_day_cb.new(
                y=current_day.year, m=current_day.month, d=current_day.day
                ))
            ]
        ]
    )