from datetime import datetime
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from telegram import Bot

from image_bot.database.base import Session
from image_bot.database.models import Schedule, Channel
from image_bot.utils.logger import logger
from image_bot.config import Config
from image_bot.services.mailing_service import MailingService


class SchedulerService:
    def __init__(self, application: Bot, session_factory, config: Config):
        """Инициализация сервиса планировщика"""
        self.bot = application.bot if hasattr(application, 'bot') else application
        self.session_factory = session_factory
        self.config = config
        self.last_executed = {}  # Хранит время последнего выполнения для каждого канала и времени
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.mailing_service = MailingService(application, session_factory)
        self.active_tasks = {}  # Хранит активные задачи рассылки
        
    def _should_execute(self, channel_id: str, schedule_time: str, current_time: datetime) -> bool:
        """Проверяет, нужно ли выполнять рассылку"""
        try:
            # Преобразуем время из формата HH:MM:SS в HH:MM
            if len(schedule_time.split(':')) > 2:
                schedule_time = ':'.join(schedule_time.split(':')[:2])
            
            # Получаем время рассылки
            schedule_hour, schedule_minute = map(int, schedule_time.split(':'))
            schedule_dt = current_time.replace(hour=schedule_hour, minute=schedule_minute)
            
            # Ключ для отслеживания выполнения
            execution_key = f"{channel_id}_{schedule_time}"
            
            # Если рассылка уже была выполнена в эту минуту, пропускаем
            if execution_key in self.last_executed:
                last_exec = self.last_executed[execution_key]
                if (current_time - last_exec).total_seconds() < 60:
                    return False
            
            # Проверяем, что текущее время находится в пределах минуты от запланированного
            time_diff = abs((current_time - schedule_dt).total_seconds())
            should_execute = time_diff <= 30  # 30 секунд до или после запланированного времени
            
            if should_execute:
                self.last_executed[execution_key] = current_time
                
            return should_execute
        except Exception as e:
            logger.error(f"Error in _should_execute for channel {channel_id}, time {schedule_time}: {e}")
            return False

    async def send_to_channel(self, channel_id: int, schedule: dict):
        """Отправляет сообщения в канал"""
        task_key = f"{channel_id}_{schedule['time']}"
        
        try:
            # Получаем telegram_id канала
            async with self.session_factory() as session:
                result = await session.execute(
                    select(Channel).where(Channel.id == channel_id)
                )
                channel = result.scalar_one_or_none()

                if not channel:
                    logger.error(f"[SCHEDULER] Channel {channel_id} not found")
                    return

                # Отправляем сообщение через mailing_service
                await self.mailing_service.send_message_with_image(
                    channel_id=channel.telegram_id,
                    messages=schedule['messages'],
                    message_delay_seconds=schedule['message_delay_seconds'],
                    image_delay_seconds=schedule['image_delay_seconds'],
                    images_count=schedule['images_count'],
                    bet_amount=schedule['bet_amount'],
                    welcome_to_first_signal_seconds=schedule.get('welcome_to_first_signal_seconds', 60),
                    signal_to_win_seconds=schedule.get('signal_to_win_seconds', 45),
                    between_signals_seconds=schedule.get('between_signals_seconds', 25),
                    last_signal_to_summary_seconds=schedule.get('last_signal_to_summary_seconds', 40),
                    template=schedule.get('template', 'lkr')
                )
                logger.info(f"[SCHEDULER] Successfully sent message to channel {channel_id}")
            
        except Exception as e:
            logger.error(f"[SCHEDULER] Error sending message to channel {channel_id}: {e}")
        finally:
            # Удаляем задачу из активных после завершения
            if task_key in self.active_tasks:
                del self.active_tasks[task_key]

    async def check_and_execute_schedules(self):
        """Проверяет и выполняет запланированные рассылки"""
        try:
            current_time = datetime.now()
            logger.info(f"[SCHEDULER] Checking schedules at {current_time.strftime('%H:%M:%S')}")
            
            # Получаем все активные расписания
            schedules = await self.mailing_service.get_active_schedules()
            logger.info(f"[SCHEDULER] Found {len(schedules)} active schedules")
            
            # Группируем расписания по каналам
            channel_schedules = {}
            for schedule in schedules:
                if schedule.channel_id not in channel_schedules:
                    channel_schedules[schedule.channel_id] = []
                channel_schedules[schedule.channel_id].append({
                    'time': schedule.time_of_day.strftime('%H:%M'),
                    'enabled': schedule.enabled,
                    'messages': schedule.messages,
                    'message_delay_seconds': schedule.message_delay_seconds,
                    'image_delay_seconds': schedule.image_delay_seconds,
                    'images_count': schedule.images_count,
                    'bet_amount': schedule.bet_amount,
                    'welcome_to_first_signal_seconds': schedule.welcome_to_first_signal_seconds,
                    'signal_to_win_seconds': schedule.signal_to_win_seconds,
                    'between_signals_seconds': schedule.between_signals_seconds,
                    'last_signal_to_summary_seconds': schedule.last_signal_to_summary_seconds,
                    'template': schedule.template
                })
            
            tasks = []
            for channel_id, schedules in channel_schedules.items():
                logger.info(f"[SCHEDULER] Checking channel {channel_id}")
                
                for schedule in schedules:
                    schedule_time = schedule['time']
                    enabled = schedule['enabled']
                    task_key = f"{channel_id}_{schedule_time}"
                    
                    logger.info(f"[SCHEDULER] Schedule item - time: {schedule_time}, enabled: {enabled}")
                    
                    if not schedule_time or not enabled:
                        logger.info(f"[SCHEDULER] Skipping disabled or invalid schedule: {schedule}")
                        continue
                    
                    # Проверяем, не выполняется ли уже эта рассылка
                    if task_key in self.active_tasks:
                        if not self.active_tasks[task_key].done():
                            logger.info(f"[SCHEDULER] Task {task_key} is still running")
                            continue
                        else:
                            del self.active_tasks[task_key]
                    
                    if self._should_execute(str(channel_id), schedule_time, current_time):
                        logger.info(f"[SCHEDULER] Creating task for channel {channel_id} at {current_time.strftime('%H:%M:%S')}")
                        # Создаем новую задачу
                        task = asyncio.create_task(self.send_to_channel(channel_id, schedule))
                        self.active_tasks[task_key] = task
                        tasks.append(task)
                    else:
                        logger.info(f"[SCHEDULER] Schedule time {schedule_time} doesn't match current time {current_time.strftime('%H:%M:%S')}")
            
            # Ждем завершения всех новых задач
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                        
        except Exception as e:
            logger.error(f"Error checking schedules: {e}")
            
    async def run(self):
        """Запускает планировщик"""
        while True:
            await self.check_and_execute_schedules()
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд
