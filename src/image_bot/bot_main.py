import asyncio
from loguru import logger
from image_bot.database.base import Base, engine, Session
from image_bot.bot.bot import bot
from image_bot.services.scheduler_service import SchedulerService
from image_bot.config import Config
from image_bot.utils.cleanup import schedule_cleanup

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def main():
    try:
        # Create tables
        await init_db()
        logger.info("Database tables created successfully")

        # Start the bot
        await bot.initialize()
        await bot.start()
        logger.info("Bot started successfully")
        
        # Initialize scheduler (передаём фабрику сессий)
        config = Config()
        scheduler = SchedulerService(bot, Session, config)
        
        # Start scheduler in background
        scheduler_task = asyncio.create_task(scheduler.run())
        logger.info("Scheduler started successfully")
        
        # Start cleanup scheduler in background (очистка в 00:00)
        cleanup_task = asyncio.create_task(schedule_cleanup(hour=0, minute=0))
        logger.info("Cleanup scheduler started successfully")
        
        # Run the bot
        logger.info("Bot is running...")
        await bot.updater.start_polling()

        # Wait for termination
        stop_signal = asyncio.Event()
        await stop_signal.wait()
        
        # Cancel scheduler task
        scheduler_task.cancel()
        cleanup_task.cancel()
        try:
            await scheduler_task
            await cleanup_task
        except asyncio.CancelledError:
            pass

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        # Properly shutdown the bot
        logger.info("Shutting down...")
        if bot.updater.running:
            await bot.updater.stop()
        if bot.running:
            await bot.stop()
        logger.info("Bot stopped successfully")

def run():
    """Run the bot."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

if __name__ == "__main__":
    run()
