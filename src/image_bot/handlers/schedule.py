from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from image_bot.handlers.schedule_create import (
    add_schedule_command,
    CHANNEL_SELECT, TIME_SELECT, IMAGES_COUNT, WELCOME_TO_FIRST_SIGNAL, SIGNAL_TO_WIN, 
    BETWEEN_SIGNALS, LAST_SIGNAL_TO_SUMMARY, TEMPLATE_SELECT, BET_AMOUNT, MESSAGES
)
from image_bot.handlers.schedule_list import list_schedules_command
from image_bot.handlers.schedule_delete import delete_schedule_command
from image_bot.handlers.schedule_messages import add_schedule_messages_command


def register_schedule_handlers(application):
    """Регистрация обработчиков команд для работы с расписанием"""
    
    # Обработчик создания расписания
    add_schedule_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add_schedule", add_schedule_command),
            CallbackQueryHandler(add_schedule_command, pattern="^add_schedule$")
        ],
        states={
            CHANNEL_SELECT: [
                CallbackQueryHandler(add_schedule_command, pattern="^select_channel_|back_to_main")
            ],
            TIME_SELECT: [
                CallbackQueryHandler(add_schedule_command, pattern="^time_|back_to_main"),
                # Обработчик для любого текстового сообщения в состоянии TIME_SELECT
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_schedule_command)
            ],
            IMAGES_COUNT: [
                CallbackQueryHandler(add_schedule_command, pattern="^count_|back_to_main")
            ],
            WELCOME_TO_FIRST_SIGNAL: [
                CallbackQueryHandler(add_schedule_command, pattern="^welcome_delay_|back_to_main")
            ],
            SIGNAL_TO_WIN: [
                CallbackQueryHandler(add_schedule_command, pattern="^signal_win_delay_|back_to_main")
            ],
            BETWEEN_SIGNALS: [
                CallbackQueryHandler(add_schedule_command, pattern="^between_signals_delay_|back_to_main")
            ],
            LAST_SIGNAL_TO_SUMMARY: [
                CallbackQueryHandler(add_schedule_command, pattern="^last_signal_delay_|back_to_main")
            ],
            TEMPLATE_SELECT: [
                CallbackQueryHandler(add_schedule_command, pattern="^template_|back_to_main")
            ],
            BET_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_schedule_command)
            ],
            MESSAGES: [
                CommandHandler("add_schedule_messages", add_schedule_messages_command)
            ]
        },
        fallbacks=[CommandHandler("cancel", add_schedule_command)],
        name="schedule_conversation",
        persistent=False,
        allow_reentry=True
    )

    # Регистрируем обработчики
    application.add_handler(add_schedule_conv_handler, group=1)  # Приоритетная группа
    
    # Обработчики для списка расписаний
    application.add_handler(CommandHandler("list_schedules", list_schedules_command), group=2)
    application.add_handler(CallbackQueryHandler(list_schedules_command, pattern="^delete_schedule$|^confirm_delete_schedule_|^back_to_schedules$"), group=2)
    
    # Остальные обработчики
    application.add_handler(CommandHandler("delete_schedule", delete_schedule_command), group=2)
    application.add_handler(CommandHandler("add_schedule_messages", add_schedule_messages_command), group=2)
