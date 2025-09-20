import asyncio
from datetime import datetime
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from image_bot.config import Config
from image_bot.database.base import init_db, get_session
from image_bot.services.mailing_service import MailingService
from image_bot.services.scheduler_service import SchedulerService
from image_bot.utils.logger import logger


class Bot:
    def __init__(self, config: Config):
        self.config = config
        self.application = None
        self.scheduler_service = None
        self.mailing_service = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        keyboard = [
            [InlineKeyboardButton("📢 Управление каналами", callback_data="show_channels")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👋 Привет! Я бот для рассылки изображений по расписанию.\n\n"
            "Чтобы начать работу:\n"
            "1. Добавьте меня в канал\n"
            "2. Сделайте меня администратором\n"
            "3. Включите право на публикацию сообщений\n"
            "4. Добавьте канал в список рассылки\n"
            "5. Настройте расписание рассылки\n\n"
            "Используйте кнопки ниже для управления:",
            reply_markup=reply_markup
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "ℹ️ Справка по использованию бота\n\n"
            "Основные команды:\n"
            "/start - Запустить бота\n"
            "/help - Показать эту справку\n\n"
            "Управление каналами:\n"
            "1. Добавьте бота в канал\n"
            "2. Сделайте бота администратором\n"
            "3. Включите право на публикацию сообщений\n"
            "4. Добавьте канал через меню «Управление каналами»\n"
            "5. Настройте расписание рассылки\n\n"
            "Расписание:\n"
            "- Вы можете добавить несколько рассылок для каждого канала\n"
            "- Каждая рассылка может быть включена или выключена\n"
            "- Время рассылки указывается в формате ЧЧ:ММ",
            reply_markup=reply_markup
        )

    async def handle_channel_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода ID канала"""
        if 'waiting_for' not in context.user_data or context.user_data['waiting_for'] != 'channel_id':
            return

        try:
            channel_id = int(update.message.text)
            success, message = await self.mailing_service.check_channel_permissions(channel_id)
            
            if success:
                try:
                    chat = await context.bot.get_chat(channel_id)
                    await self.mailing_service.add_channel(channel_id, chat.title)
                    await update.message.reply_text(
                        f"✅ Канал успешно добавлен!\n{message}\n\n"
                        "Теперь вы можете настроить расписание рассылки для этого канала."
                    )
                except Exception as e:
                    logger.error(f"Error adding channel: {e}")
                    await update.message.reply_text("❌ Произошла ошибка при добавлении канала.")
            else:
                await update.message.reply_text(
                    f"❌ Не удалось добавить канал.\n{message}\n\n"
                    "📋 Необходимо:\n"
                    "1. Добавить бота в канал\n"
                    "2. Сделать бота администратором\n"
                    "3. Включить право на публикацию сообщений"
                )
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID канала. Попробуйте еще раз.")
        except Exception as e:
            logger.error(f"Error handling channel ID: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке ID канала.")
        finally:
            context.user_data.pop('waiting_for', None)

    async def handle_schedule_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода времени рассылки"""
        if 'editing_schedule' not in context.user_data:
            return

        try:
            time_str = update.message.text
            # Проверяем формат времени
            time = datetime.strptime(time_str, "%H:%M").time()
            
            channel_id = context.user_data['editing_schedule']['channel_id']
            schedule_id = context.user_data['editing_schedule'].get('id')
            
            if schedule_id:
                # Обновляем существующее расписание
                await self.mailing_service.update_schedule(schedule_id, new_time=time)
            else:
                # Создаем новое расписание
                await self.mailing_service.create_schedule(int(channel_id), time)
            
            await update.message.reply_text("✅ Время рассылки обновлено!")
            await self.mailing_service.show_schedule_menu(update, context, int(channel_id))
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат времени. Используйте формат ЧЧ:ММ, например: 15:30"
            )
        except Exception as e:
            logger.error(f"Error handling schedule time: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обновлении времени рассылки.")
        finally:
            context.user_data.pop('editing_schedule', None)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback-запросов"""
        query = update.callback_query
        data = query.data
        
        try:
            if data == "start":
                await self.start(update, context)
            elif data == "help":
                await self.help(update, context)
            elif data == "show_channels":
                await self.mailing_service.show_channels_menu(update, context)
            elif data == "add_channel":
                context.user_data['waiting_for'] = 'channel_id'
                keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data="show_channels")]]
                await query.edit_message_text(
                    text="📝 Отправьте ID канала:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            elif data.startswith("show_channel:"):
                channel_id = int(data.split(":")[1])
                await self.mailing_service.show_channel_menu(update, context, channel_id)
            elif data.startswith("check_permissions:"):
                channel_id = int(data.split(":")[1])
                success, message = await self.mailing_service.check_channel_permissions(channel_id)
                await query.answer(message)
            elif data.startswith("manage_schedules:"):
                channel_id = int(data.split(":")[1])
                await self.mailing_service.show_schedule_menu(update, context, channel_id)
            elif data.startswith("add_schedule:"):
                channel_id = data.split(":")[1]
                context.user_data['editing_schedule'] = {
                    'channel_id': channel_id,
                    'id': None
                }
                keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data=f"manage_schedules:{channel_id}")]]
                await query.edit_message_text(
                    text="🕒 Введите время для новой рассылки в формате ЧЧ:ММ (например, 15:30):",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            elif data.startswith("edit_schedule:"):
                _, channel_id, schedule_id = data.split(":")
                await self.mailing_service.show_edit_schedule_menu(update, context, int(channel_id), int(schedule_id))
            elif data.startswith("change_time:"):
                _, channel_id, schedule_id = data.split(":")
                context.user_data['editing_schedule'] = {
                    'channel_id': channel_id,
                    'id': int(schedule_id)
                }
                keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data=f"manage_schedules:{channel_id}")]]
                await query.edit_message_text(
                    text="🕒 Введите новое время для рассылки в формате ЧЧ:ММ (например, 15:30):",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            elif data.startswith("toggle_schedule:"):
                _, channel_id, schedule_id = data.split(":")
                schedule = await self.mailing_service.update_schedule(int(schedule_id), enabled=None)  # None для инвертирования
                await self.mailing_service.show_edit_schedule_menu(update, context, int(channel_id), int(schedule_id))
            elif data.startswith("delete_schedule:"):
                _, channel_id, schedule_id = data.split(":")
                await self.mailing_service.delete_schedule(int(schedule_id))
                await self.mailing_service.show_schedule_menu(update, context, int(channel_id))
            elif data.startswith("remove_channel:"):
                channel_id = int(data.split(":")[1])
                await self.mailing_service.delete_channel(channel_id)
                await self.mailing_service.show_channels_menu(update, context)
            else:
                await query.answer("❌ Неизвестная команда")
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await query.answer("❌ Произошла ошибка")

    async def run(self):
        """Запускает бота"""
        try:
            # Инициализируем базу данных
            await init_db()

            # Создаем приложение
            self.application = Application.builder().token(self.config.bot.token).build()

            # Инициализируем сервисы
            # Передаем фабрику сессий (Session), чтобы сервисы создавали короткоживущие сессии сами
            from image_bot.database.base import Session as SessionFactory
            self.mailing_service = MailingService(self.application.bot, SessionFactory)
            self.scheduler_service = SchedulerService(self.application.bot, SessionFactory, self.config)

            # Добавляем обработчики команд
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CallbackQueryHandler(self.handle_callback))
            self.application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_channel_id
            ))
            self.application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_schedule_time
            ))

            # Запускаем планировщик в отдельной задаче
            asyncio.create_task(self.scheduler_service.run())

            # Запускаем бота
            await self.application.run_polling()
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
