from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from loguru import logger

from image_bot.database.base import Session
from image_bot.database.models import Schedule, Channel
from image_bot.utils.decorators import admin_required


@admin_required
async def delete_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для удаления расписания"""
    try:
        # Если команда вызвана без аргументов, показываем список расписаний
        if not context.args:
            async with Session() as session:
                # Получаем все расписания с информацией о каналах
                result = await session.execute(
                    select(Schedule, Channel)
                    .join(Channel, Schedule.channel_id == Channel.id)
                )
                schedules = result.all()

                if not schedules:
                    await update.message.reply_text(
                        "Нет активных расписаний."
                    )
                    return

                message = "Выберите расписание для удаления:\n\n"
                keyboard = []
                row = []

                for schedule, channel in schedules:
                    schedule_text = (
                        f"{channel.title} "
                        f"({schedule.time_of_day.strftime('%H:%M')})"
                    )
                    row.append(InlineKeyboardButton(
                        text=schedule_text,
                        callback_data=f"confirm_delete_{schedule.id}"
                    ))
                    
                    if len(row) == 2:  # По 2 кнопки в ряд
                        keyboard.append(row)
                        row = []
                
                if row:  # Добавляем оставшиеся кнопки
                    keyboard.append(row)

                # Добавляем кнопку возврата
                keyboard.append([InlineKeyboardButton(
                    text="« Назад",
                    callback_data="back_to_main"
                )])

                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

        # Если указан ID расписания, удаляем его
        try:
            schedule_id = int(context.args[0])
        except (ValueError, IndexError):
            await update.message.reply_text(
                "Неверный формат ID расписания. Используйте /delete_schedule ID"
            )
            return

        async with Session() as session:
            # Находим расписание
            result = await session.execute(
                select(Schedule, Channel)
                .join(Channel, Schedule.channel_id == Channel.id)
                .where(Schedule.id == schedule_id)
            )
            schedule_data = result.first()

            if not schedule_data:
                await update.message.reply_text(
                    "Расписание с указанным ID не найдено."
                )
                return

            schedule, channel = schedule_data

            # Удаляем расписание
            await session.delete(schedule)
            await session.commit()

            await update.message.reply_text(
                f"Расписание для канала {channel.title} "
                f"({schedule.time_of_day.strftime('%H:%M')}) успешно удалено."
            )

    except Exception as e:
        logger.error(f"Error in delete_schedule: {e}")
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")
        raise
