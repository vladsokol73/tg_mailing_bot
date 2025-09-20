import logging
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from image_bot.database.base import Session
from image_bot.database.models import User
from image_bot.keyboards.keyboards import get_base_keyboard, get_admin_keyboard, get_authorized_keyboard
from image_bot.config import Config
from image_bot.utils.decorators import admin_required
from image_bot.handlers.schedule_list import list_schedules_command

# Загружаем конфигурацию
config = Config()

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    async with Session() as session:
        try:
            # Проверяем, существует ли пользователь
            result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            user = result.scalar_one_or_none()

            if not user:
                # Создаем нового пользователя
                is_admin = update.effective_user.id in config.bot.admin_ids
                user = User(
                    telegram_id=update.effective_user.id,
                    username=update.effective_user.username,
                    is_admin=is_admin,
                    is_authorized=is_admin  # Админы автоматически авторизованы
                )
                session.add(user)
                await session.commit()

                if is_admin:
                    message = "Добро пожаловать! Вы зарегистрированы как администратор бота."
                    keyboard = get_admin_keyboard()
                else:
                    message = (
                        "Добро пожаловать! Я бот для создания рассылок. "
                        "Вам нужно получить разрешение от администратора для использования."
                    )
                    keyboard = get_base_keyboard()
            else:
                # Обновляем username пользователя, если он изменился
                if user.username != update.effective_user.username:
                    user.username = update.effective_user.username
                    await session.commit()
                    logger.info(f"Updated username for user {user.telegram_id} to {user.username}")

                if user.is_admin:
                    message = "С возвращением, администратор! Вы можете использовать бота для создания рассылок."
                    keyboard = get_admin_keyboard()
                elif user.is_authorized:
                    message = "С возвращением! Вы можете использовать бота для создания рассылок."
                    keyboard = get_authorized_keyboard()
                else:
                    message = "Вы уже зарегистрированы, но еще не получили разрешение от администратора."
                    keyboard = get_base_keyboard()

            if update.callback_query:
                await update.callback_query.message.edit_text(message)
                # Отправляем клавиатуру отдельным сообщением для callback_query
                await update.callback_query.message.reply_text("Выберите действие:", reply_markup=keyboard)
            else:
                await update.message.reply_text(message, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            error_message = "Произошла ошибка при обработке команды."
            if update.callback_query:
                await update.callback_query.message.reply_text(error_message)
            else:
                await update.message.reply_text(error_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    async with Session() as session:
        try:
            # Проверяем, является ли пользователь администратором
            result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            user = result.scalar_one_or_none()

            base_help_text = """
    Доступные команды:

    Сгенерировать изображение - создать новое изображение
    Помощь - показать это сообщение"""

            authorized_help_text = """

    Для авторизованных пользователей:
    Управление каналами - добавление и управление каналами
    /add_schedule CHANNEL_ID HH:MM - добавить расписание для канала
    /list_schedules - показать список всех расписаний
    /delete_schedule SCHEDULE_ID - удалить расписание"""

            admin_help_text = """

    Для администраторов:
    Управление пользователями - управление правами пользователей
    /authorize <user_id> - авторизовать пользователя"""

            help_text = base_help_text
            if user:
                if user.is_authorized:
                    help_text += authorized_help_text
                if user.is_admin:
                    help_text += admin_help_text

            if update.callback_query:
                await update.callback_query.message.reply_text(help_text)
            else:
                await update.message.reply_text(help_text)
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            error_message = "Произошла ошибка при обработке команды."
            if update.callback_query:
                await update.callback_query.message.reply_text(error_message)
            else:
                await update.message.reply_text(error_message)


@admin_required
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    if 'waiting_for_time' in context.user_data:
        del context.user_data['waiting_for_time']
        if 'selected_channel_id' in context.user_data:
            del context.user_data['selected_channel_id']
        await list_schedules_command(update, context)
        return

    # Очищаем все состояния
    context.user_data.clear()
    await update.message.reply_text("Действие отменено")
