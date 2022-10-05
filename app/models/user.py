import sqlalchemy as sa
from sqlalchemy import Sequence
from sqlalchemy.dialects.postgresql import ENUM

from app.misc.enums import UserStatusEnum
from app.models.base import TimedBaseModel

EVENT_ID_SEQUENCE = Sequence('event_id_sq')
EVENT_ID_SEQUENCE.start = 2


class User(TimedBaseModel):
    user_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=False, index=True)
    spreadsheet_id = sa.Column(sa.BIGINT, EVENT_ID_SEQUENCE, server_default=EVENT_ID_SEQUENCE.next_value())
    full_name = sa.Column(sa.VARCHAR(255), nullable=False)
    mention = sa.Column(sa.VARCHAR(300), nullable=False)
    phone_number = sa.Column(sa.VARCHAR(15), nullable=True)

    status = sa.Column(ENUM(UserStatusEnum), default=UserStatusEnum.COMMON, nullable=False)
    hours = sa.Column(sa.INTEGER, nullable=False, default=0)
