from datetime import datetime
from pathlib import Path

import apiclient
from google.oauth2 import service_account

from app.misc.enums import UserStatusEnum
from app.misc.utils import localize
from app.models import User

import sys

if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    import collections
    setattr(collections, "MutableMapping", collections.abc.MutableMapping)


class GoogleCalendar:
    credentials = Path('data', 'googlecalendar', 'credentials.json')
    scopes = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events.readonly'
    ]

    def __init__(self):
        self.service = self.authorization

    @classmethod
    def env(cls):
        return GoogleCalendar()

    @property
    def authorization(self):
        credentials = service_account.Credentials.from_service_account_file(self.credentials, scopes=self.scopes)
        return apiclient.discovery.build('calendar', 'v3', credentials=credentials)

    def insert_calendar(self, calendar_id: str):
        self.service.calendarList().insert(body={
            'id': calendar_id
        }).execute()

    def calendar_list(self):
        return self.service.calendarList().list().execute()

    def get(self, calendar_id: str):
        return self.service.calendars().get(calendarId=calendar_id).execute()

    def create_calendar(self, name: str, description: str, location: str):
        body = {
            'summary': name,
            'description': description,
            'location': f'{location}',
            'timeZone': 'Europe/Kiev'
        }
        return self.service.calendars().insert(body=body).execute()

    def update_calendar(self, calendar_id: str, **kwargs):
        calendar = self.get(calendar_id)
        for key, value in kwargs.items():
            calendar[key] = value
        return self.service.calendars().update(calendarId=calendar_id, body=calendar).execute()

    def create_event(
            self, name: str,
            calendar_id: str,
            start: datetime,
            end: datetime,
            user: User
    ):
        location = self.get(calendar_id)['location']
        if user.status == UserStatusEnum.COMMON:
            color_id = '4'
        elif user.status == UserStatusEnum.TRAINER:
            color_id = '9'
        elif user.status == UserStatusEnum.REGULAR:
            color_id = '2'
        else:
            color_id = '1'
        body = {
            'summary': name,
            'description': f'Цей час зарезервовано користувачем {user.full_name} {user.phone_number}\n'
                           f'({user.user_id}) але не оплачено.',
            'location': location,
            'colorId': color_id,
            'start': {
                'dateTime': localize(start).isoformat(),
                'timeZone': 'Europe/Kiev'
            },
            'end': {
                'dateTime': localize(end).isoformat(),
                'timeZone': 'Europe/Kiev'
            }
        }
        return self.service.events().insert(calendarId=calendar_id, body=body).execute()

    def update_event(self, calendar_id: str, event_id: str, **kwargs):
        event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        for key, value in kwargs.items():
            event[key] = value
        return self.service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()

    def event_paid(self, calendar_id: str, event_id: str, user: User):
        self.update_event(calendar_id, event_id, **dict(
            description=f'Цей час заброньовано та оплачено {user.full_name} {user.phone_number} ({user.user_id}).'
        ))

    def event_confirm(self, calendar_id: str, event_id: str, user: User):
        self.update_event(calendar_id, event_id, **dict(
            description=f'Підтвержено та оплачено {user.full_name} {user.phone_number} ({user.user_id}).'
        ))

    def delete_event(self, calendar_id: str, event_id: str):
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    def events_list(self, calendar_id: str):
        return self.service.events().list(calendarId=calendar_id, pageToken=None).execute()['items']

    def reserved_time(self, calendar_id: str, day: datetime):
        open_time = localize(day).replace(hour=7, minute=0, second=0, microsecond=0)
        close_time = localize(day).replace(hour=22, minute=0, second=0, microsecond=0)

        events = self.events_list(calendar_id)
        day_events = []
        for event in events:
            if open_time <= localize(datetime.fromisoformat(event['start']['dateTime'])) <= close_time:
                day_events.append(event)
        result = []
        for event in day_events:
            format_time = '%H:%M'
            start = localize(datetime.fromisoformat(event['start']['dateTime']))
            end = localize(datetime.fromisoformat(event['end']['dateTime']))
            result.append(f'{start.strftime(format_time)} - {end.strftime(format_time)}')
        return result

