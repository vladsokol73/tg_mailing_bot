from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
from image_bot.handlers.base import start_command, help_command, cancel_command
from image_bot.handlers.admin import authorize_command
from image_bot.handlers.user import handle_text
from image_bot.handlers.channel import handle_channel_message, handle_channel_callback
from image_bot.handlers.schedule import register_schedule_handlers
from image_bot.handlers.image import generate_image

def setup_handlers(application):
    """Настройка обработчиков команд"""
    # Базовые команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("authorize", authorize_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Команды для управления расписаниями
    register_schedule_handlers(application)
    
    # Обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(generate_image, pattern='^generate_image$'))
    application.add_handler(CallbackQueryHandler(handle_channel_callback))
    
    # Обработчик пересланных сообщений
    application.add_handler(MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, handle_channel_message))
    
    # Обработчик текстовых команд меню (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$"), handle_text))
