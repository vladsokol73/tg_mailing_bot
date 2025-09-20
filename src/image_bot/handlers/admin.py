from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger
from sqlalchemy import select
from image_bot.database.base import Session
from image_bot.database.models import User
from image_bot.keyboards.keyboards import get_authorized_keyboard


async def authorize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /authorize"""
    async with Session() as session:
        try:
            # Проверяем, является ли отправитель админом
            result = await session.execute(
                select(User).where(
                    User.telegram_id == update.effective_user.id,
                    User.is_admin == True
                )
            )
            admin = result.scalar_one_or_none()

            if not admin:
                await update.message.reply_text("У вас нет прав для выполнения этой команды.")
                return

            # Проверяем, указан ли ID пользователя
            if not context.args:
                await update.message.reply_text("Укажите ID пользователя для авторизации.")
                return

            try:
                user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("Неверный формат ID пользователя.")
                return

            # Находим пользователя для авторизации
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Создаем нового пользователя без username (он заполнится при /start)
                user = User(
                    telegram_id=user_id,
                    username=None,
                    is_admin=False,
                    is_authorized=True  # Сразу авторизуем
                )
                session.add(user)
                await session.commit()
                logger.info(f"Created and authorized new user with ID {user_id}")
            else:
                # Авторизуем существующего пользователя
                user.is_authorized = True
                await session.commit()
                logger.info(f"Authorized existing user with ID {user_id}")

            # Отправляем сообщение админу
            await update.message.reply_text(f"Пользователь {user_id} успешно авторизован.")

            # Отправляем сообщение пользователю с новой клавиатурой
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Вы были авторизованы администратором! Теперь вы можете использовать бота. Пожалуйста, отправьте команду /start для настройки вашего профиля.",
                    reply_markup=get_authorized_keyboard()
                )
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {str(e)}")
                logger.exception(e)
                await update.message.reply_text(
                    f"Пользователь авторизован, но не удалось отправить ему уведомление. Ошибка: {str(e)}"
                )

        except Exception as e:
            logger.error(f"Error in authorize command: {str(e)}")
            logger.exception(e)
            await update.message.reply_text(f"Произошла ошибка при обработке команды: {str(e)}")


async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция управления пользователями"""
    async with Session() as session:
        try:
            # Проверяем права администратора
            result = await session.execute(
                select(User).where(
                    User.telegram_id == update.effective_user.id,
                    User.is_admin == True
                )
            )
            admin = result.scalar_one_or_none()

            if not admin:
                await update.message.reply_text("У вас нет прав для выполнения этой команды.")
                return

            # Получаем список пользователей
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            users_text = "Список пользователей:\n\n"
            for user in users:
                status = "✅" if user.is_authorized else "❌"
                admin_status = "👑" if user.is_admin else ""
                users_text += f"{status} {admin_status} ID: {user.telegram_id}"
                if user.username:
                    users_text += f" (@{user.username})"
                users_text += "\n"

            users_text += "\nИспользуйте /authorize <user_id> для авторизации пользователя"
            await update.message.reply_text(users_text)

        except Exception as e:
            logger.error(f"Error in user management: {e}")
            await update.message.reply_text("Произошла ошибка при получении списка пользователей.")
