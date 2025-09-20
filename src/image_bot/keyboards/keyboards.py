from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Tuple
from image_bot.database.models import Schedule, Channel


def get_base_keyboard():
    """Базовая клавиатура для неавторизованных пользователей"""
    keyboard = [
        [KeyboardButton("📺 Управление каналами")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_authorized_keyboard():
    """Клавиатура для авторизованных пользователей"""
    keyboard = [
        [KeyboardButton("📺 Управление каналами")],
        [KeyboardButton("📅 Управление расписанием")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_keyboard():
    """Клавиатура для администраторов"""
    keyboard = [
        [KeyboardButton("📺 Управление каналами")],
        [KeyboardButton("📅 Управление расписанием"), KeyboardButton("👥 Управление пользователями")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_channel_management_keyboard(has_channels=False):
    """Клавиатура для управления каналами"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
    ]
    if has_channels:
        keyboard.append([InlineKeyboardButton("❌ Удалить канал", callback_data="remove_channel")])

    return InlineKeyboardMarkup(keyboard)


def get_schedule_management_keyboard(has_schedules=False):
    """Клавиатура для управления расписаниями"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить расписание", callback_data="add_schedule")],
    ]
    if has_schedules:
        keyboard.append([InlineKeyboardButton("❌ Удалить расписание", callback_data="delete_schedule")])

    return InlineKeyboardMarkup(keyboard)


def create_channel_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Подтвердить", callback_data=f"channel_confirm_{channel_id}")],
        [InlineKeyboardButton("Отклонить", callback_data=f"channel_reject_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_schedule_keyboard(has_schedules: bool) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления расписаниями"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить расписание", callback_data="add_schedule")],
    ]
    
    if has_schedules:
        keyboard.append([InlineKeyboardButton("🗑 Удалить расписание", callback_data="delete_schedule")])
    
    keyboard.append([InlineKeyboardButton("📋 Список расписаний", callback_data="list_schedules")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)


def get_channels_list_keyboard(channels):
    """Клавиатура со списком каналов для удаления"""
    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(
            f"{channel.title} (@{channel.username if channel.username else 'no username'})",
            callback_data=f"delete_channel_{channel.telegram_id}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_channels")])

    return InlineKeyboardMarkup(keyboard)


def get_schedule_channel_select_keyboard(channels):
    """Клавиатура для выбора канала при создании расписания"""
    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(
            f"{channel.title} (@{channel.username if channel.username else 'no username'})",
            callback_data=f"select_channel_{channel.telegram_id}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_schedules")])
    return InlineKeyboardMarkup(keyboard)


def get_schedule_time_keyboard():
    """Клавиатура для выбора времени расписания"""
    times = [
        ("09:00", "09:00"), ("12:00", "12:00"), ("15:00", "15:00"), 
        ("18:00", "18:00"), ("21:00", "21:00")
    ]
    keyboard = []
    # Создаем ряды по 3 кнопки
    for i in range(0, len(times), 3):
        row = []
        for time_display, time_value in times[i:i+3]:
            row.append(InlineKeyboardButton(
                time_display,
                callback_data=f"select_time_{time_value}"
            ))
        keyboard.append(row)
    
    # Добавляем кнопку для ввода произвольного времени
    keyboard.append([InlineKeyboardButton(
        "🕒 Другое время",
        callback_data="custom_time"
    )])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_channel_select")])
    return InlineKeyboardMarkup(keyboard)
