import sqlalchemy as sa
from app.models.base import TimedBaseModel


class Calendar(TimedBaseModel):
    calendar_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    google_id = sa.Column(sa.VARCHAR(100), nullable=False)
    name = sa.Column(sa.VARCHAR(150), nullable=True)
    description = sa.Column(sa.VARCHAR(500), nullable=True)
    location = sa.Column(sa.VARCHAR(300), nullable=True)
    photo_id = sa.Column(sa.VARCHAR(200), nullable=True)