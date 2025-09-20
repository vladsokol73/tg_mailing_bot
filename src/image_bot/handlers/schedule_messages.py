import json
from datetime import datetime, time
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from loguru import logger

from image_bot.database.base import Session
from image_bot.database.models import Channel, Schedule
from image_bot.utils.decorators import admin_required


@admin_required
async def add_schedule_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления сообщений к расписанию"""
    try:
        # Проверяем, что расписание не было только что создано
        if context.user_data.get('schedule_created'):
            context.user_data.pop('schedule_created', None)
            return

        if not context.args:
            await update.message.reply_text(
                "Используйте команду в формате:\n"
                "/add_schedule_messages Приветственное сообщение | "
                "Сообщение перед картинкой | "
                "Итоговое сообщение\n\n"
                "Например:\n"
                "/add_schedule_messages Начинаем! | Коэффициент: {average} | Итого: {total}\n\n"
                "Доступные переменные:\n"
                "• В сообщении перед картинкой: {average} - среднее значение\n"
                "• В итоговом сообщении: {total} - общая сумма коэффициентов"
            )
            return

        # Проверяем, что у пользователя есть незавершенное создание расписания
        required_keys = ["selected_channel", "schedule_time", "images_count", "bet_amount"]
        # Проверяем наличие хотя бы одного из новых ключей для интервалов
        interval_keys = ["welcome_to_first_signal_seconds", "signal_to_win_seconds", "between_signals_seconds", "last_signal_to_summary_seconds"]
        
        if not all(key in context.user_data for key in required_keys) or not any(key in context.user_data for key in interval_keys):
            logger.error(f"Missing required keys in user_data: {context.user_data}")
            await update.message.reply_text(
                "Сначала начните создание расписания с помощью команды /add_schedule"
            )
            return

        # Получаем сообщения из аргументов команды, сохраняя переносы строк
        raw_text = update.message.text.split(' ', 1)[1] if len(update.message.text.split(' ', 1)) > 1 else ''
        messages = [msg.strip() for msg in raw_text.split('|') if msg.strip()]

        # Проверяем, что есть ровно 3 сообщения
        if len(messages) != 3:
            await update.message.reply_text(
                "Необходимо указать ровно три сообщения:\n"
                "1. Приветственное сообщение\n"
                "2. Сообщение перед каждой картинкой\n"
                "3. Итоговое сообщение"
            )
            return

        # Создаем расписание
        channel_id = context.user_data["selected_channel"]  # Теперь это id из базы
        time_str = context.user_data["schedule_time"]
        count = context.user_data["images_count"]
        
        # Используем значения по умолчанию для старых параметров
        message_delay = 60  # Значение по умолчанию
        image_delay = 60  # Значение по умолчанию

        # Получаем значения интервалов
        welcome_to_first_signal = context.user_data.get("welcome_to_first_signal_seconds", 60)
        signal_to_win = context.user_data.get("signal_to_win_seconds", 45)
        between_signals = context.user_data.get("between_signals_seconds", 25)
        last_signal_to_summary = context.user_data.get("last_signal_to_summary_seconds", 40)
        
        # Получаем выбранный шаблон страны
        template = context.user_data.get("template", "lkr")

        logger.info(f"Creating schedule for channel {channel_id} with intervals: welcome={welcome_to_first_signal}, signal_win={signal_to_win}, between={between_signals}, last={last_signal_to_summary}, template={template}")

        # Парсим время
        hour, minute = map(int, time_str.split(":"))
        schedule_time = time(hour, minute)

        # Создаем расписание
        async with Session() as session:
            # Получаем канал по id
            result = await session.execute(
                select(Channel).where(Channel.id == channel_id)
            )
            channel = result.scalar_one_or_none()

            if not channel:
                await update.message.reply_text("Ошибка: канал не найден.")
                return

            logger.info(f"Found channel: {channel.id=}, {channel.telegram_id=}, {channel.title=}")

            # Получаем сумму ставки
            bet_amount = int(context.user_data.get("bet_amount", 0))
            
            # Создаем новое расписание
            new_schedule = Schedule(
                channel_id=channel.id,
                time_of_day=schedule_time,
                messages=json.dumps(messages),
                message_delay_seconds=message_delay,
                image_delay_seconds=image_delay,
                images_count=count,
                bet_amount=bet_amount,
                welcome_to_first_signal_seconds=welcome_to_first_signal,
                signal_to_win_seconds=signal_to_win,
                between_signals_seconds=between_signals,
                last_signal_to_summary_seconds=last_signal_to_summary,
                template=template,
                enabled=True
            )

            session.add(new_schedule)
            await session.commit()

            logger.info(f"Schedule created successfully: {new_schedule.id=}, bet_amount={bet_amount}")

        # Отправляем подтверждение
        message = "✅ Расписание успешно создано:\n\n"
        message += f"Канал: {channel.title}\n"
        message += f"Время: {time_str}\n"
        message += f"Количество изображений: {count}\n"
        message += f"Сумма ставки: {bet_amount}\n"
        
        message += "\n⚙️ Интервалы:\n"
        message += f"• Между приветствием и 1 сигналом: {welcome_to_first_signal} сек\n"
        message += f"• Между сигналом и выигрышем: {signal_to_win} сек\n"
        message += f"• Между сигналами: {between_signals} сек\n"
        message += f"• Между последним сигналом и итогами: {last_signal_to_summary} сек\n"
        
        # Добавляем информацию о выбранном шаблоне
        template_names = {
            "lkr": "Ланкийская рупия (LKR)",
            "pkr": "Пакистанская рупия (PKR)",
            "uzs": "Узбекский сум (UZS)",
            "pen": "Перуанский соль (PEN)",
            "kgs": "Киргизский сом (KGS)"
        }
        template_name = template_names.get(template, template)
        message += f"\n⚡️ Шаблон страны: {template_name}\n"
        
        message += "\nСообщения:\n"
        message += f"1. Приветствие: {messages[0]}\n"
        message += f"2. Перед картинкой: {messages[1]}\n"
        message += f"3. Итог: {messages[2]}\n"

        await update.message.reply_text(message)

        # Очищаем данные о создании расписания
        context.user_data.clear()
        
        # Добавляем флаг, что расписание уже создано
        context.user_data['schedule_created'] = True

    except Exception as e:
        logger.error(f"Error in add_schedule_messages: {e}")
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")
