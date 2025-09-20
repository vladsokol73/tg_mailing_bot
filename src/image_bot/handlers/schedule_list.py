import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select, delete
from loguru import logger

from image_bot.database.base import Session
from image_bot.database.models import Schedule, Channel
from image_bot.utils.decorators import admin_required
from image_bot.keyboards.keyboards import get_schedule_management_keyboard


@admin_required
async def list_schedules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра всех расписаний"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        if query.data == "delete_schedule":
            # Получаем список расписаний для удаления
            async with Session() as session:
                result = await session.execute(
                    select(Schedule, Channel).join(Channel, Schedule.channel_id == Channel.id)
                )
                schedules = result.all()

                if not schedules:
                    await query.message.edit_text(
                        "Нет активных расписаний для удаления.",
                        reply_markup=get_schedule_management_keyboard(False)
                    )
                    return

                # Создаем клавиатуру с кнопками для каждого расписания
                keyboard = []
                for schedule, channel in schedules:
                    channel_text = f"{channel.title}"
                    if channel.username:
                        channel_text += f" (@{channel.username})"
                    button_text = f"{schedule.time_of_day.strftime('%H:%M')} - {channel_text}"
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"confirm_delete_schedule_{schedule.id}"
                    )])
                keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_schedules")])

                await query.message.edit_text(
                    "Выберите расписание для удаления:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

        elif query.data.startswith("confirm_delete_schedule_"):
            schedule_id = int(query.data.replace("confirm_delete_schedule_", ""))
            async with Session() as session:
                try:
                    # Находим расписание
                    result = await session.execute(
                        select(Schedule).where(Schedule.id == schedule_id)
                    )
                    schedule = result.scalar_one_or_none()

                    if schedule:
                        # Удаляем расписание
                        await session.delete(schedule)
                        await session.commit()
                        await query.message.edit_text(
                            f"✅ Расписание успешно удалено!",
                            reply_markup=get_schedule_management_keyboard(True)
                        )
                    else:
                        await query.message.edit_text(
                            "❌ Расписание не найдено.",
                            reply_markup=get_schedule_management_keyboard(True)
                        )
                except Exception as e:
                    logger.error(f"Error deleting schedule: {e}")
                    await query.message.edit_text(
                        "❌ Произошла ошибка при удалении расписания.",
                        reply_markup=get_schedule_management_keyboard(True)
                    )
                return

        elif query.data == "back_to_schedules":
            # Возвращаемся к списку расписаний
            await list_schedules_command(update, context)
            return
    try:
        async with Session() as session:
            # Получаем все расписания с информацией о каналах
            result = await session.execute(
                select(Schedule, Channel).join(Channel, Schedule.channel_id == Channel.id)
            )
            schedules = result.all()

            # Подготавливаем клавиатуру
            keyboard = get_schedule_management_keyboard(bool(schedules))

            if not schedules:
                await update.message.reply_text(
                    "Нет активных расписаний.",
                    reply_markup=keyboard
                )
                return

            message = "📋 Список активных расписаний:\n\n"
            for schedule, channel in schedules:
                channel_text = f"{channel.title}"
                if channel.username:
                    channel_text += f" (@{channel.username})"
                
                messages = json.loads(schedule.messages) if schedule.messages else []
                message += (
                    f"ID: {schedule.id}\n"
                    f"Канал: {channel_text}\n"
                    f"Время: {schedule.time_of_day.strftime('%H:%M')}\n"
                    f"⌛️ Задержка между сообщениями: {schedule.message_delay_seconds} сек\n"
                    f"⏱ Задержка перед изображениями: {schedule.image_delay_seconds} сек\n"
                    f"Количество изображений: {schedule.images_count}\n"
                )
                if messages:
                    message += "Сообщения:\n"
                    message += f"1. Приветствие: {messages[0]}\n"
                    message += f"2. Перед картинкой: {messages[1]}\n"
                    message += f"3. Итог: {messages[2]}\n"
                message += "\n"

            # Разбиваем сообщение на части, если оно слишком длинное
            max_length = 4096
            messages = []
            while len(message) > 0:
                if len(message) <= max_length:
                    messages.append(message)
                    break
                split_index = message[:max_length].rfind('\n\n')
                if split_index == -1:
                    split_index = max_length
                messages.append(message[:split_index])
                message = message[split_index:].lstrip()

            # Отправляем каждую часть сообщения
            for i, msg in enumerate(messages):
                # Добавляем клавиатуру только к последнему сообщению
                if i == len(messages) - 1:
                    await update.message.reply_text(msg, reply_markup=keyboard)
                else:
                    await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"Error in list_schedules: {e}")
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")
