import asyncio
from telegram.ext import ApplicationBuilder
from image_bot.config import Config
from image_bot.handlers import setup_handlers
from image_bot.services.scheduler_service import SchedulerService
from image_bot.database.base import Session

config = Config()
bot_token = config.config_data['telegram']['token']

# Создаем приложение
bot = ApplicationBuilder().token(bot_token).build()

# Настраиваем обработчики
setup_handlers(bot)

# Создаем планировщик
async def start_scheduler():
    # Передаем фабрику сессий, чтобы планировщик открывал и закрывал сессии сам
    scheduler = SchedulerService(bot.bot, Session, config)
    await scheduler.run()

async def run():
    """Run both the bot and the scheduler"""
    # Запускаем планировщик в фоновом режиме
    scheduler_task = asyncio.create_task(start_scheduler())
    
    try:
        # Запускаем бота
        await bot.start()
        await bot.updater.start_polling()
        
        # Ждем завершения бота
        await bot.updater.stop()
        await bot.stop()
    finally:
        # Останавливаем планировщик
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
