from app.states.base import *


class CalendarSG(StatesGroup):
    Name = State()
    Description = State()
    Location = State()
    Mail = State()
    Confirm = State()


class EventSG(StatesGroup):
    Calendar = State()
    Start = State()
    End = State()
    Confirm = State()


class DeleteSG(StatesGroup):
    Delete = State()
    Confirm = State()


class SubSG(StatesGroup):
    Days = State()
    Hours = State()
    Confirm = State()