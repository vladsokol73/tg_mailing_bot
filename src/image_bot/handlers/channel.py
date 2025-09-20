from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger
from sqlalchemy import select
from image_bot.database.base import Session
from image_bot.database.models import User, Channel
from image_bot.keyboards.keyboards import get_channel_management_keyboard, get_channels_list_keyboard


async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция управления каналами"""
    async with Session() as session:
        try:
            # Проверяем права пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_authorized:
                error_text = "У вас нет прав для управления каналами."
                if update.callback_query:
                    await update.callback_query.message.reply_text(error_text)
                else:
                    await update.message.reply_text(error_text)
                return

            # Получаем список каналов
            result = await session.execute(select(Channel))
            channels = result.scalars().all()

            channels_text = "📺 Список подключенных каналов:\n\n"
            if channels:
                for channel in channels:
                    channels_text += f"ID: {channel.telegram_id}\n"
                    channels_text += f"Название: {channel.title}\n"
                    if channel.username:
                        channels_text += f"Username: @{channel.username}\n"
                    channels_text += "\n"
            else:
                channels_text += "Нет подключенных каналов\n\n"

            # Добавляем кнопки для управления
            reply_markup = get_channel_management_keyboard(bool(channels))
            channels_text += "Выберите действие:"

            if update.callback_query:
                await update.callback_query.message.edit_text(channels_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(channels_text, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error in channel management: {e}")
            error_text = "Произошла ошибка при получении списка каналов."
            if update.callback_query:
                await update.callback_query.message.edit_text(error_text)
            else:
                await update.message.reply_text(error_text)


async def handle_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пересланных сообщений из каналов"""
    logger.info("Received forwarded message")

    if 'waiting_for' not in context.user_data or context.user_data['waiting_for'] != 'channel_message':
        logger.info("Not waiting for channel message")
        return

    if not update.message or not update.message.forward_origin:
        logger.warning("Message is not forwarded")
        await update.message.reply_text("Пожалуйста, перешлите сообщение из канала.")
        return

    logger.info(f"Forward origin type: {type(update.message.forward_origin)}")
    logger.info(f"Forward origin: {update.message.forward_origin}")

    # Получаем информацию о канале
    try:
        # Проверяем, что сообщение переслано из канала
        if not hasattr(update.message.forward_origin, 'chat'):
            logger.warning("Message is not forwarded from a channel")
            await update.message.reply_text("Пожалуйста, перешлите сообщение из канала.")
            return

        chat = update.message.forward_origin.chat
        if chat.type != 'channel':
            logger.warning("Forwarded message is not from a channel")
            await update.message.reply_text("Пожалуйста, перешлите сообщение именно из канала.")
            return

        logger.info(f"Processing channel: {chat.title} (ID: {chat.id})")

        # Проверяем права бота в канале
        try:
            # Получаем информацию о боте в канале
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)

            # Проверяем, является ли бот администратором
            if not bot_member.status in ['administrator', 'creator']:
                logger.warning(f"Bot is not admin in channel {chat.title}")
                await update.message.reply_text(
                    "Бот должен быть администратором канала!\n\n"
                    "1. Добавьте бота в администраторы канала\n"
                    "2. Предоставьте права на публикацию сообщений\n"
                    "3. Попробуйте добавить канал снова"
                )
                return

            # Проверяем необходимые права
            if not bot_member.can_post_messages:
                logger.warning(f"Bot doesn't have posting rights in channel {chat.title}")
                await update.message.reply_text(
                    "У бота недостаточно прав в канале!\n\n"
                    "Необходимо предоставить право на публикацию сообщений."
                )
                return

            logger.info(f"Bot has required permissions in channel {chat.title}")

        except Exception as e:
            logger.error(f"Error checking bot permissions: {e}")
            await update.message.reply_text(
                "Не удалось проверить права бота в канале.\n"
                "Убедитесь, что бот добавлен в канал как администратор."
            )
            return

        async with Session() as session:
            try:
                # Проверяем, есть ли уже такой канал
                result = await session.execute(
                    select(Channel).where(Channel.telegram_id == chat.id)
                )
                existing_channel = result.scalar_one_or_none()
                
                if existing_channel:
                    logger.info(f"Channel {chat.title} already exists")
                    await update.message.reply_text(f"Канал {chat.title} уже добавлен.")
                    return

                # Создаем новый канал
                new_channel = Channel(
                    telegram_id=chat.id,
                    title=chat.title,
                    username=chat.username if hasattr(chat, 'username') else None
                )
                session.add(new_channel)
                await session.commit()
                logger.info(f"Successfully added channel {chat.title}")

                await update.message.reply_text(
                    f"✅ Канал {chat.title} успешно добавлен!\n\n"
                    "Теперь бот сможет публиковать сообщения в этом канале."
                )

            except Exception as e:
                logger.error(f"Error adding channel: {e}")
                await update.message.reply_text("Произошла ошибка при добавлении канала.")
            finally:
                context.user_data.pop('waiting_for', None)

    except Exception as e:
        logger.error(f"Error processing channel: {e}")
        await update.message.reply_text(
            "Не удалось получить информацию о канале.\n"
            "Убедитесь, что бот добавлен в канал как администратор."
        )


async def handle_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов для управления каналами"""
    query = update.callback_query
    await query.answer()

    if query.data == "add_channel":
        # Запрашиваем добавление бота в канал
        await query.message.reply_text(
            "Для добавления канала:\n\n"
            "1. Добавьте бота в канал как администратора\n"
            "2. Перешлите любое сообщение из канала в этот чат"
        )
        # Сохраняем состояние ожидания пересланного сообщения
        context.user_data['waiting_for'] = 'channel_message'

    elif query.data == "remove_channel":
        async with Session() as session:
            try:
                # Получаем список каналов для удаления
                result = await session.execute(select(Channel))
                channels = result.scalars().all()
                reply_markup = get_channels_list_keyboard(channels)

                await query.message.edit_text(
                    "Выберите канал для удаления:",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Error in remove_channel callback: {e}")
                await query.message.reply_text("Произошла ошибка при получении списка каналов.")

    elif query.data.startswith("delete_channel_"):
        channel_id = int(query.data.split('_')[2])
        async with Session() as session:
            try:
                # Находим канал
                result = await session.execute(
                    select(Channel).where(Channel.telegram_id == channel_id)
                )
                channel = result.scalar_one_or_none()
                
                if channel:
                    # Сначала удаляем все расписания для этого канала
                    from image_bot.database.models import Schedule
                    from sqlalchemy import delete
                    
                    # Удаляем все расписания канала
                    await session.execute(
                        delete(Schedule).where(Schedule.channel_id == channel.id)
                    )
                    
                    # Теперь удаляем сам канал
                    await session.delete(channel)
                    await session.commit()
                    await query.message.edit_text(f"Канал {channel.title} и все его расписания успешно удалены.")
                else:
                    await query.message.edit_text("Канал не найден.")
            except Exception as e:
                logger.error(f"Error in delete_channel callback: {e}")
                await query.message.edit_text("Произошла ошибка при удалении канала.")

    elif query.data == "back_to_channels":
        # Возвращаемся к списку каналов
        await manage_channels(update, context)
