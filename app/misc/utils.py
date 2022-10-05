from _ast import Sub
from datetime import datetime

import pytz

from app.config import Config
from app.misc.enums import UserStatusEnum, EventStatusEnum, SubStatusEnum
from app.models import User
from app.models.event import Event
from app.models.subscribe import Subscribe


def now():
    config = Config.from_env()
    return datetime.now().replace(second=0, microsecond=0).astimezone(pytz.timezone(config.misc.timezone))


def localize(date: datetime):
    config = Config.from_env()
    return date.replace(second=0, microsecond=0).astimezone(pytz.timezone(config.misc.timezone))


def construct_user_text(user: User, subs: list[Subscribe]):
    phone_number = user.phone_number if user.phone_number is not None else 'Не вказано'
    status = construct_user_status(user)
    text = (
        f'<b>Ім\'я</b>: {user.full_name}\n'
        f'<b>Статус</b>: {status}\n'
        f'<b>Номер телефону</b>: {phone_number}\n'
        f'<b>Замовлених годин</b>: {user.hours}\n'
    )
    if subs:

        subs_text = '\n\n<b>Абонементи</b>:\n\n'
        subs_text += '\n\n'.join(
            [
                f'<b>Абонемент #{sub.sub_id}</b>\n{sub.description}\nЗалишилось годин: {sub.total_hours}'
                for sub in subs if sub.status == SubStatusEnum.ACTIVE
            ]
        )
        text += subs_text
    return text


def construct_user_status(user: User) -> str:
    if user.status == UserStatusEnum.COMMON:
        return 'Новий клієнт'
    if user.status == UserStatusEnum.REGULAR:
        return 'Постійний клієнт'
    if user.status == UserStatusEnum.TRAINER:
        return 'Тренер'
    if user.status == UserStatusEnum.VIP:
        return 'VIP'


def get_status(event: Event) -> str:
    if event.status == EventStatusEnum.RESERVED:
        return f'Зарезервовано на 15 хв'
    if event.status == EventStatusEnum.PAID:
        return f'Заброньовано'
    if event.status == EventStatusEnum.CONFIRM:
        return f'Заброньовано і підтвержено'
    if event.status == EventStatusEnum.DELETED:
        return 'Скасовано'


def get_status_sub(sub: Subscribe) -> str:
    if sub.status == SubStatusEnum.ACTIVE:
        return 'Оплачена'
    if sub.status == SubStatusEnum.PASSED:
        return 'Нактивна'


def amount_solution(user: User, event: Event | str):
    price_list = {
        '1.0': {
            'weekdays': {
                '7:00-16:30': [700, 630, 560],
                '16:30': [850, 765, 680],
                '17:00-22:00': [1000, 900, 800],
            },
            'weekends': {
                '7:00-22:00': [1000, 900, 800]
            }
        },
        '1.5': {
            'weekdays': {
                '7:00-16:00': [1050, 945, 840],
                '16:00': [1300, 1170, 1040],
                '16:30': [1350, 1215, 1080],
                '17:00-22:00': [1500, 1350, 1200],
            },
            'weekends': {
                '7:00-22:00': [1500, 1350, 1200]
            }
        },
        '2.0': {
            'weekdays': {
                '7:00-15:30': [1400, 1260, 1120],
                '15:30': [1550, 1395, 1240],
                '16:00': [1700, 1530, 1360],
                '16:30': [1850, 1665, 1480],
                '17:00-22:00': [2000, 1800, 1600],
            },
            'weekends': {
                '7:00-22:00': [2000, 1800, 1600]
            }
        },
        '2.5': {
            'weekdays': {
                '7:00-15:00': [1750, 1575, 1400],
                '15:00': [1900, 1710, 1520],
                '15:30': [2050, 1845, 1640],
                '16:00': [2200, 1980, 1760],
                '16:30': [2350, 2115, 1880],
                '17:00-22:00': [2500, 2250, 2000]
            },
            'weekends': {
                '7:00-22:00': [2500, 2250, 2000]
            },
        },
        '3.0': {
            'weekdays': {
                '7:00-14:30': [2100, 1890, 1680],
                '14:30': [2250, 2025, 1800],
                '15:00': [2400, 2160, 1920],
                '15:30': [2550, 2295, 2040],
                '16:00': [2700, 2430, 2160],
                '16:30': [2850, 2565, 2280],
                '17:00-22:00': [3000, 2700, 2400]
            },
            'weekends': {
                '7:00-22:00': [3000, 2700, 2400]
            }
        }
    }
    if isinstance(event, Event):
        celebrates = [
            '01.01', '07.01', '08.03', '01.05', '09.05', '28.06', '24.08', '14.10', '25.12'
        ]
        hours = str(float((event.end - event.start).seconds/3600))
        if user.status in (UserStatusEnum.VIP, UserStatusEnum.COMMON):
            index = 0
        elif user.status == UserStatusEnum.REGULAR:
            index = 1
        else:
            index = 2

        if event.start.strftime('%a') in ('Сб', 'НД'):
            price = check_time(price_list[hours]['weekends'], event)[index]
        elif event.start.strftime('%d.%m') in celebrates:
            price = check_time(price_list[hours]['weekends'], event)[index]
        else:
            price = check_time(price_list[hours]['weekdays'], event)[index]

        return price
    else:
        if user.status in (UserStatusEnum.VIP, UserStatusEnum.COMMON):
            if event == 'after':
                return 10000
            else:
                return 7000
        elif user.status == UserStatusEnum.REGULAR:
            if event == 'after':
                return 9000
            else:
                return 6300


def check_time(times: dict, event: Event) -> list[int]:
    current = now().replace(microsecond=0, second=0)
    for time, prices in times.items():
        if '-' in time:
            start, end = time.split('-')
            start = current.replace(minute=int(start.split(':')[-1]), hour=int(start.split(':')[0]))
            end = current.replace(minute=int(end.split(':')[-1]), hour=int(end.split(':')[0]))
            print(start, end, localize(event.start.replace(microsecond=0, second=0)))
            if start <= localize(current.replace(hour=event.start.hour, minute=event.start.minute)) < end:
                return prices
        else:
            if event.start.strftime('%H:%M') == time:
                return prices

