from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from image_bot.config import Config

config = Config()
db_config = config.database

DATABASE_URL = db_config.url

engine = create_async_engine(DATABASE_URL, echo=True)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def init_db():
    """Инициализирует базу данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    """Возвращает сессию для работы с базой данных"""
    return Session()
