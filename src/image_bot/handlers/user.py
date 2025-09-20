from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from image_bot.models import Session
from image_bot.database.models import User
from image_bot.handlers.base import help_command
from image_bot.handlers.admin import manage_users
from image_bot.handlers.channel import manage_channels
from image_bot.handlers.image import generate_image, handle_image_prompt, cancel_action
from image_bot.handlers.schedule_list import list_schedules_command
from image_bot.services.mailing_service import MailingService


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        text = update.message.text
        if text == "📺 Управление каналами":
            await manage_channels(update, context)
        elif text == "📅 Управление расписанием":
            await list_schedules_command(update, context)
        elif text == "👥 Управление пользователями":
            await manage_users(update, context)
        elif text == "ℹ️ Помощь":
            await help_command(update, context)
        # Не делаем ничего для других текстовых сообщений, чтобы они могли быть обработаны другими обработчиками

    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")
