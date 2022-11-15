import logging
from dataclasses import dataclass

from environs import Env
from sqlalchemy.engine import URL


@dataclass
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @property
    def sqlalchemy_url(self) -> URL:
        return URL.create(
            'postgresql+asyncpg',
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )


@dataclass
class RedisConfig:
    host: str
    port: int


@dataclass
class TgBot:
    token: str
    admin_ids: tuple[int, ...]
    payment_token: str
    fondy_credit_key: str
    fondy_merchant_id: str
    fondyp2p: str


@dataclass
class Miscellaneous:
    log_level: int
    timezone: str
    prices_path: str
    spreadsheet: str


@dataclass
class Config:
    bot: TgBot
    db: DbConfig
    redis: RedisConfig
    misc: Miscellaneous

    @classmethod
    def from_env(cls, path: str = None) -> 'Config':
        env = Env()
        env.read_env(path)

        return Config(
            bot=TgBot(
                token=env.str('BOT_TOKEN'),
                admin_ids=tuple(map(int, env.list('ADMIN_IDS'))),
                payment_token=env.str('PAYMENT_TOKEN'),
                fondy_credit_key=env.str('FONDY_CREDIT_KEY'),
                fondy_merchant_id=env.str('FONDY_MERCHANT_ID'),
                fondyp2p=env.str('P2P')
            ),
            db=DbConfig(
                host=env.str('DB_HOST', 'localhost'),
                port=env.int('DB_PORT', 5432),
                user=env.str('DB_USER', 'postgres'),
                password=env.str('DB_PASS', 'postgres'),
                database=env.str('DB_NAME', 'postgres'),
            ),
            redis=RedisConfig(
                host=env.str('REDIS_HOST', 'localhost'),
                port=env.int('REDIS_PORT', 6379),
            ),
            misc=Miscellaneous(
                log_level=env.log_level('LOG_LEVEL', logging.INFO),
                prices_path=env.str('PRICES_PATH'),
                timezone=env.str('TIMEZONE'),
                spreadsheet=env.str('SPREADSHEET'),
            )
        )
