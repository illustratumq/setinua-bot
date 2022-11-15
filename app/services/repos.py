from datetime import datetime

from app.misc.enums import EventStatusEnum
from app.misc.utils import localize
from app.models import *
from app.models.calendar import Calendar
from app.models.event import Event
from app.models.subscribe import Subscribe
from app.services.db_ctx import BaseRepo


class UserRepo(BaseRepo[User]):
    model = User

    async def get_user(self, user_id: int) -> User:
        return await self.get_one(self.model.user_id == user_id)

    async def update_user(self, user_id: int, **kwargs) -> None:
        return await self.update(self.model.user_id == user_id, **kwargs)


class CalendarRepo(BaseRepo[Calendar]):
    model = Calendar

    async def get_calendar(self, calendar_id: int) -> Calendar:
        return await self.get_one(self.model.calendar_id == calendar_id)

    async def update_calendar(self, calendar_id: int, **kwargs) -> None:
        return await self.update(self.model.calendar_id == calendar_id, **kwargs)

    async def get_calendar_by_google_id(self, google_id: str) -> Calendar:
        return await self.get_one(self.model.google_id == google_id)


class EventRepo(BaseRepo[Event]):
    model = Event

    async def get_event(self, event_id: int) -> Event:
        return await self.get_one(self.model.event_id == event_id)

    async def update_event(self, event_id: int, **kwargs) -> None:
        return await self.update(self.model.event_id == event_id, **kwargs)

    async def delete_event(self, event_id: int) -> None:
        await self.delete(self.model.event_id == event_id)

    async def get_events(self, user_id: int) -> list[Event]:
        return await self.get_all(self.model.user_id == user_id, self.model.status != EventStatusEnum.DELETED)

    async def get_event_paid(self):
        return await self.get_all(
            self.model.status == EventStatusEnum.PAID
        )

    async def get_free_kort(self, calendar_ids: list[str]):
        events = [event.calendar_id for event in await self.get_all()]
        calendars = [events.count(calendar) for calendar in calendar_ids]
        return events[calendars.index(min(calendars))]


class SubRepo(BaseRepo[Subscribe]):
    model = Subscribe

    async def get_sub(self, sub_id: int) -> Subscribe:
        return await self.get_one(self.model.sub_id == sub_id)

    async def get_subs_by_user_id(self, user_id: int) -> list[Subscribe]:
        return await self.get_all(self.model.user_id == user_id)

    async def update_sub(self, sub_id: int, **kwargs) -> None:
        return await self.update(self.model.sub_id == sub_id, **kwargs)

    async def delete_sub(self, sub_id: int) -> None:
        await self.delete(self.model.sub_id == sub_id)


__all__ = (
    'UserRepo',
    'CalendarRepo',
    'EventRepo',
    'SubRepo'
)
