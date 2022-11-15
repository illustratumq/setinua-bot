import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.misc.utils import construct_user_status, localize, get_status, get_status_sub
from app.models import User
from app.models.calendar import Calendar
from app.models.event import Event
from app.models.subscribe import Subscribe

if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    import collections

    setattr(collections, "MutableMapping", collections.abc.MutableMapping)


class GoogleSheet:
    credentials = Path('data', 'googlesheets', 'credentials.json')
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self):
        self.service = self.authorization

    @classmethod
    def env(cls):
        return GoogleSheet()

    @property
    def authorization(self):
        credentials = service_account.Credentials.from_service_account_file(self.credentials, scopes=self.scopes)
        return build('sheets', 'v4', credentials=credentials)

    def update_cells(self, coordinates: str, values, spreadsheet_id: str):
        data = [{
            'range': coordinates,
            'values': values
        }]
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }
        return self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()

    def write_user(self, user: User, spreadsheet_id: str):
        self.update_cells(
            spreadsheet_id=spreadsheet_id,
            coordinates=f'Users!A{user.spreadsheet_id+1}:D{user.spreadsheet_id+1}',
            values=[
                [
                    user.user_id,
                    user.full_name,
                    user.phone_number,
                    construct_user_status(user)
                ]
            ]
        )

    def delete_user(self, user: User, spreadsheet_id: str):
        self.update_cells(
            spreadsheet_id=spreadsheet_id,
            coordinates=f'Users!A{user.spreadsheet_id+1}:D{user.spreadsheet_id+1}',
            values=['', '', '', '']
        )

    def write_event(self, event: Event | Subscribe, user: User, spreadsheet_id: str,
                    court: Calendar = None):
        if isinstance(event, Event):
            start, end = localize(event.start).strftime('%H:%M'), localize(event.end).strftime('%H:%M')
            date = localize(event.end).strftime('%A %d %B')
            values = [
                f'№{event.event_id}',
                f'{court.name}',
                f'{date} з {start} по {end}, {event.start.year}',
                f'{get_status(event)}',
                f'{user.phone_number}',
                f'{user.full_name}',
                f'{user.user_id}',
                f'{event.price}'
            ]
        else:
            date = localize(event.created_at).strftime('%A %d %B')
            values = [
                f'№{event.sub_id}',
                f'Абонемент',
                f'Придбаний {date}',
                f'{get_status_sub(event)}',
                f'{user.phone_number}',
                f'{user.full_name}',
                f'{user.user_id}',
                f'{event.price}'
            ]
        event_id = event.event_id if isinstance(event, Event) else event.sub_id
        self.update_cells(
            spreadsheet_id=spreadsheet_id,
            coordinates=f'Events!A{event_id+1}:H{event_id+1}',
            values=[values]
        )

    def delete_event(self, event: Event | Subscribe, spreadsheet_id: str):
        self.update_cells(
            spreadsheet_id=spreadsheet_id,
            coordinates=f'Events!A{event.event_id}:H{event.event_id}',
            values=[['', '', '', '', '', '']]
        )