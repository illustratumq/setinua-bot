import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM
from app.misc.enums import EventStatusEnum
from app.models.base import TimedBaseModel


class Event(TimedBaseModel):
    event_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    user_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id'), nullable=False)
    sub_id = sa.Column(sa.BIGINT, sa.ForeignKey('subscribes.sub_id'), nullable=True)
    google_id = sa.Column(sa.VARCHAR(100), nullable=True)
    calendar_id = sa.Column(sa.VARCHAR(100), nullable=True)
    start = sa.Column(sa.DateTime, nullable=True)
    end = sa.Column(sa.DateTime, nullable=True)
    status = sa.Column(ENUM(EventStatusEnum), default=EventStatusEnum.RESERVED)
    order_id = sa.Column(sa.VARCHAR(100), nullable=True)
    price = sa.Column(sa.BIGINT, nullable=True)
    job_id = sa.Column(sa.VARCHAR(100), nullable=True)

