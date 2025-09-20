from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, ForeignKey, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class User(Base):
    """Модель для хранения информации о пользователях бота"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)  # Telegram ID пользователя может быть больше int32
    username = Column(String, nullable=True)  # @username пользователя
    is_admin = Column(Boolean, default=False)  # Флаг администратора
    is_authorized = Column(Boolean, default=False)  # Флаг авторизации
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Время создания
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # Время последнего обновления

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"

class Channel(Base):
    """Модель для хранения информации о Telegram-каналах"""
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)  # ID канала может быть очень большим
    title = Column(String, nullable=False)  # Название канала
    username = Column(String, nullable=True)  # @username канала (если есть)
    is_active = Column(Boolean, default=True)  # Активен ли канал
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Время создания
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # Время последнего обновления

    def __repr__(self):
        return f"<Channel(telegram_id={self.telegram_id}, title={self.title})>"


class Schedule(Base):
    """Модель для хранения расписания рассылок"""
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('channels.id'), nullable=False)
    time_of_day = Column(Time, nullable=False)  # Время рассылки
    messages = Column(String, nullable=True)  # Список сообщений в формате JSON
    message_delay_seconds = Column(Integer, default=60)  # Задержка между сообщениями
    image_delay_seconds = Column(Integer, default=60)  # Задержка перед отправкой изображений
    images_count = Column(Integer, default=5)  # Количество изображений для отправки
    bet_amount = Column(Integer, default=0)  # Сумма ставки для генерации изображений
    enabled = Column(Boolean, default=True)  # Активно ли расписание
    welcome_to_first_signal_seconds = Column(Integer, default=60)  # Задержка между приветственным сообщением и 1 сигналом
    signal_to_win_seconds = Column(Integer, default=45)  # Задержка между сигналом и выигрышем
    between_signals_seconds = Column(Integer, default=25)  # Задержка между сигналами
    last_signal_to_summary_seconds = Column(Integer, default=40)  # Задержка между последним сигналом и итогами
    template = Column(String, default="lkr")  # Шаблон страны для генерации изображений
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    channel = relationship('Channel', backref='schedules')

    def __repr__(self):
        return f"<Schedule(channel_id={self.channel_id}, time={self.time_of_day}, messages={self.messages})>"
