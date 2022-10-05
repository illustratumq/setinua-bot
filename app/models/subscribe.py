import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM
from app.misc.enums import SubStatusEnum, SubTypeEnum
from app.models.base import TimedBaseModel


class Subscribe(TimedBaseModel):
    sub_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    user_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id'), nullable=False)
    description = sa.Column(sa.VARCHAR(120), nullable=False)
    total_hours = sa.Column(sa.FLOAT, nullable=False, default=10)
    order_id = sa.Column(sa.VARCHAR(120), nullable=True)
    status = sa.Column(ENUM(SubStatusEnum), default=SubStatusEnum.PASSED)
    type = sa.Column(ENUM(SubTypeEnum), default=SubTypeEnum.ALL)
    price = sa.Column(sa.BIGINT, nullable=True)
    job_id = sa.Column(sa.VARCHAR(100), nullable=True)


