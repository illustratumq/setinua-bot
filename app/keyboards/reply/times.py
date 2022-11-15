from datetime import datetime, timedelta

from app.keyboards.reply.back import back_bt
from app.keyboards.reply.base import *
from app.misc.utils import localize, now


def generic_available_times(
        start: datetime, end: datetime,
        reserved_times: list[str], remove_start: bool = False, only_keyboard: bool = False
):
    available_times = []
    reserved_times_date = []

    for time in reserved_times:
        start_str, end_str = time.split(' - ')
        start_date = localize(start).replace(hour=int(start_str.split(':')[0]), minute=int(start_str.split(':')[1]))
        end_date = localize(start).replace(hour=int(end_str.split(':')[0]), minute=int(end_str.split(':')[1]))
        reserved_times_date.append((start_date, end_date))
    if remove_start:
        if start.hour == 21:
            hours = 1
            if start.minute == 30:
                hours = 2
        else:
            hours = 5
        for minutes in range(0, hours * 30, 30):
            time = localize(start) + timedelta(hours=1, minutes=minutes)
            available_times.append(time)
    else:
        hours = int((end - start) / timedelta(minutes=30)) + 1
        for minutes in range(0, hours * 30, 30):
            time = localize(start) + timedelta(minutes=minutes)
            available_times.append(time)
    to_remove = []
    for reserved_time in reserved_times_date:
        reserved_start, reserved_end = reserved_time
        hours = int((reserved_end - reserved_start)/timedelta(minutes=30))
        if remove_start:
            to_remove += [reserved_start + timedelta(minutes=minutes) for minutes in range(30, (hours+1)*30, 30)]
        else:
            to_remove.append(reserved_start - timedelta(minutes=30))
            to_remove += [reserved_start + timedelta(minutes=minutes) for minutes in range(0, hours*30, 30)]

    if start.strftime('%d.%m.%y') == now().strftime('%d.%m.%y'):
        hours = int((now() - start)/timedelta(minutes=30))
        to_remove += [start + timedelta(minutes=minutes) for minutes in range(0, hours*30, 30)]
    for time in list(set(to_remove)):
        if time in available_times:
            available_times.remove(time)
    for time in list(set(available_times)):
        if time > end.replace(hour=22, minute=0) and time in available_times:
            available_times.remove(time)
    if len(available_times) > 0:
        if available_times[0] < now():
            available_times.remove(available_times[0])

    available_times = [time.strftime('%H:%M') for time in available_times]
    num = 0
    keyboard = []
    cache = []
    for time in available_times:
        cache.append(
            KeyboardButton(time)
        )
        num += 1
        if num == 4:
            keyboard.append(cache)
            cache = []
            num = 0
    if num <= 4:
        keyboard.append(cache)
    if len(keyboard) == 0:
        return
    answer = keyboard
    if only_keyboard:
        return keyboard
    keyboard.append([back_bt])
    return ReplyKeyboardMarkup(
        row_width=4,
        resize_keyboard=True,
        one_time_keyboard=True,
        keyboard=keyboard
    ), answer
