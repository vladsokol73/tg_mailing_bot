import asyncio
import logging
from pathlib import Path

from image_bot.config import Config
from image_bot.bot import Bot
from image_bot.utils.logger import logger


async def main():
    try:
        # Создаем необходимые директории
        base_dir = Path(__file__).parent.parent.parent
        output_dir = base_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Настраиваем логирование
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )

        # Запускаем бота
        from image_bot.bot.bot import run
        await run()

    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
