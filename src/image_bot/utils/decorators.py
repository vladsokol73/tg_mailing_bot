from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from image_bot.config import Config
from image_bot.database.base import Session
from image_bot.database.models import User

# Загружаем конфигурацию
config = Config()

def admin_required(func):
    """Декоратор для проверки, является ли пользователь администратором"""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_user:
            error_message = "Ошибка: не удалось определить пользователя."
            if update.callback_query:
                await update.callback_query.message.reply_text(error_message)
            elif update.message:
                await update.message.reply_text(error_message)
            return

        # Проверяем, является ли пользователь админом через список админов
        user_id = update.effective_user.id
        if user_id in config.bot.admin_ids:
            # Если пользователь в списке админов, проверяем/создаем запись в БД
            async with Session() as session:
                session: AsyncSession
                try:
                    # Получаем пользователя из базы данных
                    query = select(User).where(User.telegram_id == user_id)
                    result = await session.execute(query)
                    user = result.scalar_one_or_none()

                    if not user:
                        # Создаем пользователя с правами админа
                        user = User(
                            telegram_id=user_id,
                            username=update.effective_user.username,
                            is_admin=True,
                            is_authorized=True
                        )
                        session.add(user)
                        await session.commit()
                    elif not user.is_admin:
                        # Обновляем права пользователя
                        user.is_admin = True
                        user.is_authorized = True
                        await session.commit()

                    return await func(update, context, *args, **kwargs)
                except Exception as e:
                    error_message = f"Произошла ошибка: {str(e)}"
                    if update.callback_query:
                        await update.callback_query.message.reply_text(error_message)
                    elif update.message:
                        await update.message.reply_text(error_message)
                    raise

        # Если пользователь не в списке админов, проверяем БД
        async with Session() as session:
            session: AsyncSession
            try:
                # Получаем пользователя из базы данных
                query = select(User).where(User.telegram_id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                if not user or not user.is_admin:
                    error_message = (
                        "У вас нет прав для выполнения этой команды. "
                        "Обратитесь к администратору для получения доступа."
                    )
                    if update.callback_query:
                        await update.callback_query.message.reply_text(error_message)
                    elif update.message:
                        await update.message.reply_text(error_message)
                    return

                return await func(update, context, *args, **kwargs)
            except Exception as e:
                error_message = f"Произошла ошибка: {str(e)}"
                if update.callback_query:
                    await update.callback_query.message.reply_text(error_message)
                elif update.message:
                    await update.message.reply_text(error_message)
                raise

    return wrapped
