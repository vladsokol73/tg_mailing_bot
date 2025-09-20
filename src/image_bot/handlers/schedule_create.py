import json
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from loguru import logger

from image_bot.database.base import Session
from image_bot.database.models import Channel, Schedule
from image_bot.utils.decorators import admin_required
from image_bot.services.mailing_service import MailingService
from image_bot.keyboards.keyboards import create_schedule_keyboard, get_admin_keyboard, get_authorized_keyboard

# Состояния диалога
CHANNEL_SELECT, TIME_SELECT, IMAGES_COUNT, WELCOME_TO_FIRST_SIGNAL, SIGNAL_TO_WIN, BETWEEN_SIGNALS, LAST_SIGNAL_TO_SUMMARY, TEMPLATE_SELECT, BET_AMOUNT, MESSAGES = range(10)


@admin_required
async def add_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления расписания для канала"""
    try:
        logger.info(f"Update type: {'callback_query' if update.callback_query else 'message'}")
        if update.message:
            logger.info(f"Message text: {update.message.text}")

        # Если это callback, обрабатываем его
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            
            if query.data == "add_schedule":
                async with Session() as session:
                    result = await session.execute(select(Channel))
                    channels = result.scalars().all()

                    if not channels:
                        await query.message.edit_text(
                            "Сначала добавьте хотя бы один канал через меню управления каналами."
                        )
                        return ConversationHandler.END

                    message = "Выберите канал для добавления расписания:\n\n"
                    keyboard = []
                    row = []
                    for channel in channels:
                        channel_text = f"{channel.title}"
                        if channel.username:
                            channel_text += f" (@{channel.username})"
                        row.append(InlineKeyboardButton(
                            text=channel_text,
                            callback_data=f"select_channel_{channel.id}"
                        ))
                        if len(row) == 2:
                            keyboard.append(row)
                            row = []
                    if row:
                        keyboard.append(row)
                    keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_main")])

                    await query.message.edit_text(
                        message,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return CHANNEL_SELECT

            if query.data == "back_to_main":
                keyboard = get_admin_keyboard() if context.user_data.get("is_admin") else get_authorized_keyboard()
                await query.message.edit_text(
                    "Выберите действие:",
                    reply_markup=keyboard
                )
                return ConversationHandler.END

            # Обработка выбора канала
            if query.data.startswith("select_channel_"):
                channel_id = int(query.data.replace("select_channel_", ""))
                context.user_data["selected_channel"] = channel_id

                keyboard = [
                    [
                        InlineKeyboardButton("09:00", callback_data="time_09:00"),
                        InlineKeyboardButton("12:00", callback_data="time_12:00"),
                        InlineKeyboardButton("15:00", callback_data="time_15:00")
                    ],
                    [
                        InlineKeyboardButton("18:00", callback_data="time_18:00"),
                        InlineKeyboardButton("21:00", callback_data="time_21:00")
                    ],
                    [InlineKeyboardButton("« Назад", callback_data="back_to_main")]
                ]

                async with Session() as session:
                    result = await session.execute(
                        select(Channel).where(Channel.id == channel_id)
                    )
                    channel = result.scalar_one_or_none()

                await query.message.edit_text(
                    f"Выберите время для расписания канала {channel.title} или введите своё в формате HH:MM (например, 09:00):",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Сохраняем текущее состояние в контексте
                context.user_data['state'] = TIME_SELECT
                return TIME_SELECT

            # Обработка выбора времени из кнопок
            if query.data.startswith("time_"):
                time_str = query.data.replace("time_", "")
                context.user_data["schedule_time"] = time_str
                
                # Показываем клавиатуру для выбора количества изображений
                keyboard = [
                    [
                        InlineKeyboardButton("2", callback_data="count_2"),
                        InlineKeyboardButton("3", callback_data="count_3"),
                        InlineKeyboardButton("4", callback_data="count_4")
                    ],
                    [
                        InlineKeyboardButton("5", callback_data="count_5"),
                        InlineKeyboardButton("6", callback_data="count_6"),
                        InlineKeyboardButton("7", callback_data="count_7")
                    ],
                    [InlineKeyboardButton("« Назад", callback_data=f"select_channel_{context.user_data.get('selected_channel')}")]
                ]

                await query.message.edit_text(
                    "Выберите количество изображений:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Сохраняем текущее состояние в контексте
                context.user_data['state'] = IMAGES_COUNT
                return IMAGES_COUNT

            # Обработка количества изображений
            if query.data.startswith("count_"):
                count = int(query.data.replace("count_", ""))
                context.user_data["images_count"] = count
                
                # Показываем клавиатуру для выбора задержки между приветственным сообщением и 1 сигналом
                keyboard = [
                    [
                        InlineKeyboardButton("15 сек", callback_data="welcome_delay_15"),
                        InlineKeyboardButton("20 сек", callback_data="welcome_delay_20"),
                        InlineKeyboardButton("25 сек", callback_data="welcome_delay_25")
                    ],
                    [
                        InlineKeyboardButton("30 сек", callback_data="welcome_delay_30"),
                        InlineKeyboardButton("35 сек", callback_data="welcome_delay_35"),
                        InlineKeyboardButton("40 сек", callback_data="welcome_delay_40")
                    ],
                    [
                        InlineKeyboardButton("45 сек", callback_data="welcome_delay_45"),
                        InlineKeyboardButton("50 сек", callback_data="welcome_delay_50"),
                        InlineKeyboardButton("55 сек", callback_data="welcome_delay_55")
                    ],
                    [
                        InlineKeyboardButton("60 сек", callback_data="welcome_delay_60"),
                        InlineKeyboardButton("90 сек", callback_data="welcome_delay_90"),
                        InlineKeyboardButton("120 сек", callback_data="welcome_delay_120")
                    ],
                    [InlineKeyboardButton("« Назад", callback_data=f"time_{context.user_data.get('schedule_time')}")]
                ]
                
                await query.message.edit_text(
                    "Выберите задержку между приветственным сообщением и 1 сигналом:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Сохраняем текущее состояние в контексте
                context.user_data['state'] = WELCOME_TO_FIRST_SIGNAL
                return WELCOME_TO_FIRST_SIGNAL
                
            # Обработка задержки между приветственным сообщением и 1 сигналом
            if query.data.startswith("welcome_delay_"):
                delay = int(query.data.replace("welcome_delay_", ""))
                context.user_data["welcome_to_first_signal_seconds"] = delay
                
                # Показываем клавиатуру для выбора задержки между сигналом и выигрышем
                keyboard = [
                    [
                        InlineKeyboardButton("5 сек", callback_data="signal_win_delay_5"),
                        InlineKeyboardButton("10 сек", callback_data="signal_win_delay_10"),
                        InlineKeyboardButton("15 сек", callback_data="signal_win_delay_15")
                    ],
                    [
                        InlineKeyboardButton("20 сек", callback_data="signal_win_delay_20"),
                        InlineKeyboardButton("25 сек", callback_data="signal_win_delay_25"),
                        InlineKeyboardButton("30 сек", callback_data="signal_win_delay_30")
                    ],
                    [
                        InlineKeyboardButton("35 сек", callback_data="signal_win_delay_35"),
                        InlineKeyboardButton("40 сек", callback_data="signal_win_delay_40"),
                        InlineKeyboardButton("45 сек", callback_data="signal_win_delay_45")
                    ],
                    [
                        InlineKeyboardButton("50 сек", callback_data="signal_win_delay_50"),
                        InlineKeyboardButton("55 сек", callback_data="signal_win_delay_55"),
                        InlineKeyboardButton("60 сек", callback_data="signal_win_delay_60")
                    ],
                    [InlineKeyboardButton("« Назад", callback_data=f"welcome_delay_{context.user_data.get('welcome_to_first_signal_seconds', 60)}")]
                ]
                
                await query.message.edit_text(
                    "Выберите задержку между сигналом и выигрышем:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Сохраняем текущее состояние в контексте
                context.user_data['state'] = SIGNAL_TO_WIN
                return SIGNAL_TO_WIN
                
            # Обработка задержки между сигналом и выигрышем
            if query.data.startswith("signal_win_delay_"):
                delay = int(query.data.replace("signal_win_delay_", ""))
                context.user_data["signal_to_win_seconds"] = delay
                
                # Показываем клавиатуру для выбора задержки между сигналами
                keyboard = [
                    [
                        InlineKeyboardButton("5 сек", callback_data="between_signals_delay_5"),
                        InlineKeyboardButton("10 сек", callback_data="between_signals_delay_10"),
                        InlineKeyboardButton("15 сек", callback_data="between_signals_delay_15")
                    ],
                    [
                        InlineKeyboardButton("20 сек", callback_data="between_signals_delay_20"),
                        InlineKeyboardButton("25 сек", callback_data="between_signals_delay_25"),
                        InlineKeyboardButton("30 сек", callback_data="between_signals_delay_30")
                    ],
                    [
                        InlineKeyboardButton("35 сек", callback_data="between_signals_delay_35"),
                        InlineKeyboardButton("40 сек", callback_data="between_signals_delay_40"),
                        InlineKeyboardButton("45 сек", callback_data="between_signals_delay_45")
                    ],
                    [
                        InlineKeyboardButton("50 сек", callback_data="between_signals_delay_50"),
                        InlineKeyboardButton("55 сек", callback_data="between_signals_delay_55"),
                        InlineKeyboardButton("60 сек", callback_data="between_signals_delay_60")
                    ],
                    [InlineKeyboardButton("« Назад", callback_data=f"signal_win_delay_{context.user_data.get('signal_to_win_seconds', 45)}")]
                ]
                
                await query.message.edit_text(
                    "Выберите задержку между сигналами в целом:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Сохраняем текущее состояние в контексте
                context.user_data['state'] = BETWEEN_SIGNALS
                return BETWEEN_SIGNALS
                
            # Обработка задержки между сигналами
            if query.data.startswith("between_signals_delay_"):
                delay = int(query.data.replace("between_signals_delay_", ""))
                context.user_data["between_signals_seconds"] = delay
                
                # Показываем клавиатуру для выбора задержки между последним сигналом и итогами
                keyboard = [
                    [
                        InlineKeyboardButton("10 сек", callback_data="last_signal_delay_10"),
                        InlineKeyboardButton("15 сек", callback_data="last_signal_delay_15"),
                        InlineKeyboardButton("20 сек", callback_data="last_signal_delay_20")
                    ],
                    [
                        InlineKeyboardButton("25 сек", callback_data="last_signal_delay_25"),
                        InlineKeyboardButton("30 сек", callback_data="last_signal_delay_30"),
                        InlineKeyboardButton("35 сек", callback_data="last_signal_delay_35")
                    ],
                    [
                        InlineKeyboardButton("40 сек", callback_data="last_signal_delay_40"),
                        InlineKeyboardButton("45 сек", callback_data="last_signal_delay_45"),
                        InlineKeyboardButton("50 сек", callback_data="last_signal_delay_50")
                    ],
                    [
                        InlineKeyboardButton("60 сек", callback_data="last_signal_delay_60"),
                        InlineKeyboardButton("90 сек", callback_data="last_signal_delay_90"),
                        InlineKeyboardButton("120 сек", callback_data="last_signal_delay_120")
                    ],
                    [InlineKeyboardButton("« Назад", callback_data=f"between_signals_delay_{context.user_data.get('between_signals_seconds', 25)}")]
                ]
                
                await query.message.edit_text(
                    "Выберите задержку между последним сигналом и итогами:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Сохраняем текущее состояние в контексте
                context.user_data['state'] = LAST_SIGNAL_TO_SUMMARY
                return LAST_SIGNAL_TO_SUMMARY
                
            # Обработка задержки между последним сигналом и итогами
            if query.data.startswith("last_signal_delay_"):
                delay = int(query.data.replace("last_signal_delay_", ""))
                context.user_data["last_signal_to_summary_seconds"] = delay
                
                # Показываем клавиатуру для выбора шаблона страны
                keyboard = [
                    [
                        InlineKeyboardButton("Шри Ланка (LKR)", callback_data="template_lkr")
                    ],
                    [
                        InlineKeyboardButton("Пакистан (PKR)", callback_data="template_pkr")
                    ],
                    [
                        InlineKeyboardButton("Узбекистан (UZS)", callback_data="template_uzs")
                    ],
                    [
                        InlineKeyboardButton("Перу (PEN)", callback_data="template_pen")
                    ],
                    [
                        InlineKeyboardButton("Киргизия (KGS)", callback_data="template_kgs")
                    ],
                    [InlineKeyboardButton("« Назад", callback_data=f"last_signal_delay_{context.user_data.get('last_signal_to_summary_seconds', 40)}")]
                ]
                
                await query.message.edit_text(
                    "Выберите шаблон страны для генерации изображений:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Сохраняем текущее состояние в контексте
                context.user_data['state'] = TEMPLATE_SELECT
                return TEMPLATE_SELECT
                
            # Обработка выбора шаблона страны
            if query.data.startswith("template_"):
                template = query.data.replace("template_", "")
                context.user_data["template"] = template
                
                # Переходим к вводу суммы ставки
                await query.message.edit_text(
                    "Введите сумму ставки (целое число):"
                )
                # Сохраняем текущее состояние в контексте
                context.user_data['state'] = BET_AMOUNT
                return BET_AMOUNT

        # Обработка текстовых сообщений
        elif update.message:
            # Получаем текущее состояние из контекста
            current_state = context.user_data.get('state', None)
            logger.info(f"Processing text message: {update.message.text} in state: {current_state}")
            logger.info(f"User data: {context.user_data}")
            
            # В состоянии BET_AMOUNT обрабатываем ввод суммы ставки
            if current_state == BET_AMOUNT or (context.user_data.get("template") and "bet_amount" not in context.user_data):
                bet_text = update.message.text.strip()
                try:
                    bet_amount = int(bet_text)
                    # Проверяем, что сумма ставки не превышает лимит (1 000 000)
                    if bet_amount <= 0:
                        await update.message.reply_text(
                            "❌ Сумма ставки должна быть положительным числом. Пожалуйста, введите корректную сумму:"
                        )
                        return BET_AMOUNT
                    
                    if bet_amount > 1000000:
                        await update.message.reply_text(
                            "❌ Сумма ставки не может превышать 1 000 000. Пожалуйста, введите меньшую сумму:"
                        )
                        return BET_AMOUNT
                    
                    context.user_data["bet_amount"] = bet_amount
                    context.user_data['state'] = MESSAGES
                    logger.info(f"Successfully saved bet_amount: {bet_amount} and set state to MESSAGES")
                    
                    await update.message.reply_text(
                        "Теперь используйте команду /add_schedule_messages для добавления текстовых сообщений.\n\n"
                        "Формат:\n"
                        "/add_schedule_messages Приветственное сообщение | "
                        "Сообщение перед картинкой | "
                        "Итоговое сообщение\n\n"
                        "Например:\n"
                        "/add_schedule_messages Начинаем! | Коэффициент: {multiplied_number} | Итого: {total}\n\n{results}\n\n"
                        "Доступные переменные:\n"
                        "• В сообщении перед картинкой:\n"
                        "  - {average} - средний кэф\n"
                        "  - {multiplied_number} - ставка с кэфом\n"
                        "  - {subtracted_number} - основной кэф\n"
                        "• В итоговом сообщении:\n"
                        "  - {total} - общая сумма заработка\n"
                        "  - {results} - список всех кэфов с отметками ✅/❌"
                    )
                    return MESSAGES
                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат суммы ставки! Пожалуйста, введите целое число:"
                    )
                    return BET_AMOUNT
            
            # Проверяем, находимся ли мы в состоянии TIME_SELECT
            elif current_state == TIME_SELECT or (context.user_data.get("selected_channel") and "schedule_time" not in context.user_data):
                # В состоянии TIME_SELECT обрабатываем ввод времени
                time_str = update.message.text.strip()
                try:
                    # Проверяем формат времени
                    hour, minute = map(int, time_str.split(':'))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError("Invalid time range")
                    
                    # Сохраняем время и текущее состояние
                    context.user_data["schedule_time"] = time_str
                    context.user_data['state'] = IMAGES_COUNT
                    logger.info(f"Successfully saved time: {time_str} and set state to IMAGES_COUNT")

                    # Показываем клавиатуру для выбора количества изображений
                    keyboard = [
                        [
                            InlineKeyboardButton("2", callback_data="count_2"),
                            InlineKeyboardButton("3", callback_data="count_3"),
                            InlineKeyboardButton("4", callback_data="count_4")
                        ],
                        [
                            InlineKeyboardButton("5", callback_data="count_5"),
                            InlineKeyboardButton("6", callback_data="count_6"),
                            InlineKeyboardButton("7", callback_data="count_7")
                        ],
                        [InlineKeyboardButton("« Назад", callback_data=f"select_channel_{context.user_data.get('selected_channel')}")]
                    ]
                    
                    # Создаем новое сообщение с клавиатурой
                    # Используем reply_to_message_id, чтобы показать связь с предыдущим сообщением
                    sent_message = await update.message.reply_text(
                        f"Выбрано время: {time_str}\n\nВыберите количество изображений:",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        reply_to_message_id=update.message.message_id
                    )
                    return IMAGES_COUNT
                
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing time: {str(e)}")
                    await update.message.reply_text(
                        "❌ Неверный формат времени!\n"
                        "Пожалуйста, используйте формат HH:MM (например, 09:30)"
                    )
                    return TIME_SELECT

        # Начальное состояние команды
        if not update.callback_query:
            async with Session() as session:
                result = await session.execute(select(Channel))
                channels = result.scalars().all()

                if not channels:
                    await update.message.reply_text(
                        "Сначала добавьте хотя бы один канал через меню управления каналами."
                    )
                    return ConversationHandler.END

                message = "Выберите канал для добавления расписания:\n\n"
                keyboard = []
                row = []
                for channel in channels:
                    channel_text = f"{channel.title}"
                    if channel.username:
                        channel_text += f" (@{channel.username})"
                    row.append(InlineKeyboardButton(
                        text=channel_text,
                        callback_data=f"select_channel_{channel.id}"
                    ))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_main")])

                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return CHANNEL_SELECT

    except Exception as e:
        logger.error(f"Error in add_schedule_command: {str(e)}")
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "❌ Произошла ошибка. Пожалуйста, попробуйте снова или обратитесь к администратору."
            )
        else:
            await update.message.reply_text(
                "❌ Произошла ошибка. Пожалуйста, попробуйте снова или обратитесь к администратору."
            )
        return ConversationHandler.END


@admin_required
async def add_schedule_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления сообщений к расписанию"""
    try:
        if not update.message or not update.message.text:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите сообщения после команды."
            )
            return ConversationHandler.END

        # Получаем текст после команды
        command_text = update.message.text.split(maxsplit=1)
        if len(command_text) < 2:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите сообщения после команды."
            )
            return ConversationHandler.END

        messages = command_text[1].split("|")
        if len(messages) != 3:
            await update.message.reply_text(
                "❌ Необходимо указать ровно 3 сообщения, разделенных символом |"
            )
            return ConversationHandler.END

        # Очищаем сообщения только по краям, сохраняя внутреннее форматирование
        messages = [msg.strip() for msg in messages]

        # Получаем сохраненные данные
        channel_id = context.user_data.get("selected_channel")
        schedule_time_str = context.user_data.get("schedule_time")
        images_count = context.user_data.get("images_count", 5)
        # Используем значения по умолчанию для задержек
        message_delay = 60
        image_delay = 60
        # Получаем значения интервалов
        welcome_to_first_signal = context.user_data.get("welcome_to_first_signal_seconds", 60)
        signal_to_win = context.user_data.get("signal_to_win_seconds", 45)
        between_signals = context.user_data.get("between_signals_seconds", 25)
        last_signal_to_summary = context.user_data.get("last_signal_to_summary_seconds", 40)

        if not all([channel_id, schedule_time_str]):
            await update.message.reply_text(
                "❌ Не все параметры расписания были указаны. Пожалуйста, начните сначала с /add_schedule"
            )
            return ConversationHandler.END

        # Парсим время
        hour, minute = map(int, schedule_time_str.split(':'))
        schedule_time = time(hour=hour, minute=minute)

        # Создаем новое расписание
        async with Session() as session:
            # Получаем сумму ставки и убеждаемся, что она целочисленная
            bet_amount = int(context.user_data.get("bet_amount", 0))
            logger.info(f"Saving schedule with bet_amount: {bet_amount} (type: {type(bet_amount).__name__})")
            # Получаем новые параметры интервалов
            welcome_to_first_signal = context.user_data.get("welcome_to_first_signal_seconds", 60)
            signal_to_win = context.user_data.get("signal_to_win_seconds", 45)
            between_signals = context.user_data.get("between_signals_seconds", 25)
            last_signal_to_summary = context.user_data.get("last_signal_to_summary_seconds", 40)
            
            # Создаем расписание через mailing_service (используем фабрику сессий)
            from image_bot.database.base import Session as SessionFactory
            mailing_service = MailingService(context.bot, SessionFactory)
            schedule = await mailing_service.create_schedule(
                channel_id=channel.telegram_id,
                schedule_time=schedule_time,
                messages=messages,
                message_delay_seconds=message_delay,
                image_delay_seconds=image_delay,
                images_count=images_count,
                welcome_to_first_signal_seconds=welcome_to_first_signal,
                signal_to_win_seconds=signal_to_win,
                between_signals_seconds=between_signals,
                last_signal_to_summary_seconds=last_signal_to_summary
            )

            # Получаем информацию о канале
            result = await session.execute(
                select(Channel).where(Channel.id == channel_id)
            )
            channel = result.scalar_one_or_none()

            await update.message.reply_text(
                f"✅ Расписание для канала {channel.title} успешно создано!\n\n"
                f"⏰ Время: {schedule_time_str}\n"
                f"⌛️ Задержка между сообщениями: {message_delay} сек\n"
                f"⏱ Задержка перед изображениями: {image_delay} сек\n"
                f"💼 Количество изображений: {images_count}\n"
                f"💰 Сумма ставки: {bet_amount}\n\n"
                f"⏱ Интервалы:\n"
                f"• Между приветствием и 1 сигналом: {welcome_to_first_signal} сек\n"
                f"• Между сигналом и выигрышем: {signal_to_win} сек\n"
                f"• Между сигналами: {between_signals} сек\n"
                f"• Между последним сигналом и итогами: {last_signal_to_summary} сек\n\n"
                f"📝 Сообщения:\n"
                f"1️⃣ {messages[0]}\n"
                f"2️⃣ {messages[1]}\n"
                f"3️⃣ {messages[2]}"
            )

            # Очищаем данные
            context.user_data.clear()
            
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in add_schedule_messages_command: {str(e)}")
        await update.message.reply_text(
            "❌ Произошла ошибка при создании расписания. Пожалуйста, попробуйте снова."
        )
        return ConversationHandler.END
