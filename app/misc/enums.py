from enum import Enum


class UserStatusEnum(Enum):
    COMMON = 'COMMON'
    TRAINER = 'TRAINER'
    REGULAR = 'REGULAR'
    VIP = 'VIP'


class EventStatusEnum(Enum):
    RESERVED = 'RESERVED'
    PAID = 'PAID'
    CONFIRM = 'CONFIRM'
    DELETED = 'DELETED'


class SubStatusEnum(Enum):
    PASSED = 'PASSED'
    ACTIVE = 'ACTIVE'


class SubTypeEnum(Enum):
    WEEKMORNING = 'WEEKMORNING'
    WEEKEVENING = 'WEEKEVENING'
    HOLMORNING = 'HOLMORNING'
    HOLEVENING = 'HOLEEVENING'
    ALL = 'ALL'


__all__ = (
    'UserStatusEnum',
    'EventStatusEnum',
    'SubStatusEnum',
    'SubTypeEnum'
)
