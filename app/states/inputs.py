from app.states.base import *


class NameSG(StatesGroup):
    Input = State()


class ContactSG(StatesGroup):
    Choose = State()
    Input = State()


class ImportSG(StatesGroup):
    Input = State()


class TrainersSG(StatesGroup):
    Input = State()


class UserStatusSG(StatesGroup):
    User = State()
    Actions = State()
    Hours = State()
    Status = State()