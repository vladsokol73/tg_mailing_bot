from loguru import logger

# Настройка логгера
logger.add(
    "logs/image_bot.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
