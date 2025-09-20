import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import logging
from loguru import logger

# Получаем путь к папке output
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"


async def cleanup_old_files(days=1):
    """
    Очищает файлы из папки output, которые были созданы более указанного количества дней назад.
    
    Args:
        days (int): Количество дней. Файлы старше этого значения будут удалены.
    """
    try:
        logger.info(f"Запуск очистки старых файлов из {OUTPUT_DIR}")
        
        # Проверяем существование директории
        if not OUTPUT_DIR.exists():
            logger.warning(f"Директория {OUTPUT_DIR} не существует")
            return
        
        # Текущее время
        current_time = time.time()
        # Время в секундах для сравнения (days дней назад)
        threshold_time = current_time - (days * 24 * 60 * 60)
        
        # Счетчики для логирования
        total_files = 0
        deleted_files = 0
        
        # Проходим по всем файлам в директории
        for file_path in OUTPUT_DIR.glob("*.*"):
            total_files += 1
            
            # Получаем время создания/модификации файла
            file_mod_time = os.path.getmtime(file_path)
            
            # Если файл старше указанного порога
            if file_mod_time < threshold_time:
                try:
                    # Удаляем файл
                    os.remove(file_path)
                    deleted_files += 1
                    logger.debug(f"Удален старый файл: {file_path.name}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла {file_path.name}: {e}")
        
        logger.info(f"Очистка завершена. Всего файлов: {total_files}, удалено: {deleted_files}")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке старых файлов: {e}")


async def schedule_cleanup(hour=0, minute=0):
    """
    Планирует ежедневную очистку старых файлов в указанное время.
    
    Args:
        hour (int): Час для запуска очистки (0-23)
        minute (int): Минута для запуска очистки (0-59)
    """
    while True:
        try:
            # Получаем текущее время
            now = datetime.now()
            
            # Вычисляем время следующего запуска
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Если текущее время уже после запланированного, добавляем день
            if now >= next_run:
                next_run = next_run + timedelta(days=1)
            
            # Вычисляем время до следующего запуска
            wait_seconds = (next_run - now).total_seconds()
            
            logger.info(f"Следующая очистка запланирована на {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
                       f"(через {wait_seconds:.0f} секунд)")
            
            # Ждем до следующего запуска
            await asyncio.sleep(wait_seconds)
            
            # Запускаем очистку
            await cleanup_old_files()
            
        except Exception as e:
            logger.error(f"Ошибка в планировщике очистки: {e}")
            # В случае ошибки ждем 1 час перед повторной попыткой
            await asyncio.sleep(3600)
