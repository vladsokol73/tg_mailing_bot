from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from loguru import logger
from image_bot.database.base import Session
from image_bot.database.models import User
from image_bot.keyboards.keyboards import get_base_keyboard, get_admin_keyboard, get_authorized_keyboard
from image_bot.image_generation.generator import ImageGenerator
from sqlalchemy import select


async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды генерации изображения"""
    if update.callback_query:
        message = update.callback_query.message
        await update.callback_query.answer()
    else:
        message = update.message

    # Проверяем права пользователя
    async with Session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == update.effective_user.id)
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_authorized:
            await message.reply_text("У вас нет прав на генерацию изображений. Обратитесь к администратору.")
            return
        
    if 'state' in context.user_data:
        await message.reply_text(
            "Сначала завершите текущее действие."
        )
        return
    
    try:
        # Создаем генератор изображений
        generator = ImageGenerator()
        
        # Генерируем изображение
        image_path = generator.generate_image()
        
        # Отправляем изображение
        with open(image_path, 'rb') as photo:
            await message.reply_photo(
                photo=photo,
                caption="Сгенерированное изображение с числами"
            )
        
        # Возвращаем клавиатуру в зависимости от прав пользователя
        keyboard = get_admin_keyboard() if user.is_admin else get_authorized_keyboard()
        await message.reply_text("Выберите действие:", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        await message.reply_text("Произошла ошибка при генерации изображения. Попробуйте позже.")
        # Возвращаем клавиатуру
        keyboard = get_admin_keyboard() if user.is_admin else get_authorized_keyboard()
        await message.reply_text("Выберите действие:", reply_markup=keyboard)


async def handle_image_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текста для генерации изображения"""
    # В данный момент не используется, так как генерация происходит сразу
    await update.message.reply_text("Используйте кнопку 'Сгенерировать изображение' для создания нового изображения.")
    
    # Возвращаем основную клавиатуру
    async with Session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == update.effective_user.id)
        )
        user = result.scalar_one_or_none()
        keyboard = get_admin_keyboard() if user and user.is_admin else get_authorized_keyboard()
        await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
    
    if 'state' in context.user_data:
        del context.user_data['state']


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены действия"""
    if 'state' in context.user_data:
        del context.user_data['state']
        
        # Возвращаем соответствующую клавиатуру
        async with Session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            user = result.scalar_one_or_none()
            keyboard = get_admin_keyboard() if user and user.is_admin else get_authorized_keyboard()
            
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=keyboard
        )
