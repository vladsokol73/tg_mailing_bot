import asyncio
from datetime import datetime, time
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from telegram import Bot, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
import json

from image_bot.database.models import Schedule, Channel
from image_bot.utils.logger import logger


class MailingService:
    def __init__(self, application: Bot, session_factory):
        self.bot = application.bot if hasattr(application, 'bot') else application
        self.session_factory = session_factory
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.image_generator = None

    # Методы для управления каналами
    async def add_channel(self, channel_id: int, title: str = None) -> Channel:
        """Добавляет новый канал"""
        # Если название не указано, пробуем получить его из Telegram
        if not title:
            chat = await self.bot.get_chat(channel_id)
            title = chat.title

        async with self.session_factory() as session:
            try:
                channel = Channel(telegram_id=channel_id, title=title)
                session.add(channel)
                await session.commit()
                return channel
            except Exception as e:
                logger.error(f"Error adding channel: {e}")
                await session.rollback()
                raise

    async def delete_channel(self, channel_id: int):
        """Удаляет канал"""
        async with self.session_factory() as session:
            try:
                query = select(Channel).where(Channel.telegram_id == channel_id)
                result = await session.execute(query)
                channel = result.scalar_one_or_none()
                
                if channel:
                    await session.delete(channel)
                    await session.commit()
                    return True
                return False
            except Exception as e:
                logger.error(f"Error deleting channel: {e}")
                await session.rollback()
                raise

    async def get_channels(self):
        """Получает список всех каналов"""
        async with self.session_factory() as session:
            query = select(Channel)
            result = await session.execute(query)
            return result.scalars().all()

    async def check_channel_permissions(self, channel_id: int) -> tuple[bool, str]:
        """Проверяет права бота в канале"""
        try:
            chat_member = await self.bot.get_chat_member(channel_id, self.bot.id)
            if chat_member.status in ['administrator', 'creator']:
                can_post = chat_member.can_post_messages
                if can_post:
                    return True, "✅ Бот имеет все необходимые права"
                else:
                    return False, "❌ У бота нет прав на публикацию сообщений"
            else:
                return False, "❌ Бот не является администратором канала"
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            return False, "❌ Ошибка при проверке прав"

    # Методы для управления расписаниями
    async def create_schedule(self, channel_id: int, schedule_time: time, messages: list[str] = None,
                         message_delay_seconds: int = 60, image_delay_seconds: int = 60, 
                         images_count: int = 5, welcome_to_first_signal_seconds: int = 60,
                         signal_to_win_seconds: int = 45, between_signals_seconds: int = 25,
                         last_signal_to_summary_seconds: int = 40) -> Schedule:
        """Создает новое расписание для канала"""
        async with self.session_factory() as session:
            try:
                # Проверяем существование канала
                query = select(Channel).where(Channel.telegram_id == channel_id)
                result = await session.execute(query)
                channel = result.scalar_one_or_none()
                
                if not channel:
                    raise ValueError(f"Channel {channel_id} not found")

                # Проверяем параметры
                if message_delay_seconds < 0 or image_delay_seconds < 0:
                    raise ValueError("Задержка не может быть отрицательной")
                if images_count < 1:
                    raise ValueError("Количество изображений должно быть больше 0")

                schedule = Schedule(
                    channel_id=channel.id,
                    time_of_day=schedule_time,
                    messages=json.dumps(messages) if messages else None,
                    message_delay_seconds=message_delay_seconds,
                    image_delay_seconds=image_delay_seconds,
                    images_count=images_count,
                    welcome_to_first_signal_seconds=welcome_to_first_signal_seconds,
                    signal_to_win_seconds=signal_to_win_seconds,
                    between_signals_seconds=between_signals_seconds,
                    last_signal_to_summary_seconds=last_signal_to_summary_seconds,
                    enabled=True
                )
                session.add(schedule)
                await session.commit()
                return schedule
            except Exception as e:
                logger.error(f"Error creating schedule: {e}")
                await session.rollback()
                raise

    async def delete_schedule(self, schedule_id: int):
        """Удаляет расписание"""
        async with self.session_factory() as session:
            try:
                schedule = await session.get(Schedule, schedule_id)
                if schedule:
                    await session.delete(schedule)
                    await session.commit()
                    return True
                return False
            except Exception as e:
                logger.error(f"Error deleting schedule: {e}")
                await session.rollback()
                raise

    async def update_schedule(self, schedule_id: int, enabled: bool = None, new_time: time = None) -> Schedule:
        """Обновляет расписание"""
        async with self.session_factory() as session:
            try:
                schedule = await session.get(Schedule, schedule_id)
                if schedule:
                    if enabled is not None:
                        schedule.enabled = enabled
                    if new_time is not None:
                        schedule.time_of_day = new_time
                    schedule.updated_at = datetime.now()
                    await session.commit()
                    return schedule
                return None
            except Exception as e:
                logger.error(f"Error updating schedule: {e}")
                await session.rollback()
                raise

    async def get_channel_schedules(self, channel_id: int):
        """Получает все расписания для канала"""
        async with self.session_factory() as session:
            query = select(Schedule).join(Channel).where(Channel.telegram_id == channel_id).order_by(Schedule.time_of_day)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_active_schedules(self):
        """Получает все активные расписания для всех каналов"""
        async with self.session_factory() as session:
            query = select(Schedule).where(Schedule.enabled == True)
            result = await session.execute(query)
            return result.scalars().all()

    async def generate_images(self, count=5, bet_amount=0, template="lkr"):
        """Генерирует набор изображений
        
        Args:
            count (int, optional): Количество изображений для генерации. По умолчанию 5.
            bet_amount (int, optional): Сумма ставки для генерации изображений. По умолчанию 0.
            template (str, optional): Шаблон страны для генерации изображений. По умолчанию "lkr".
                                     Доступные варианты: "lkr", "pkr", "uzs".
        """
        try:
            # Инициализируем генератор изображений при первом использовании
            if self.image_generator is None:
                from image_bot.image_generation.generator import ImageGenerator
                self.image_generator = ImageGenerator()
            
            # Генерируем набор изображений с использованием суммы ставки и выбранного шаблона
            logger.info(f"Using template: {template} for image generation")
            images, data_list = self.image_generator.generate_images(count, bet_amount, template)
            
            return images, data_list
        except Exception as e:
            logger.error(f"Error generating images: {e}")
            return None, None

    async def send_message_with_image(self, channel_id: int, messages: str,
                                    message_delay_seconds: int = 60,
                                    image_delay_seconds: int = 60,
                                    images_count: int = 5,
                                    bet_amount: int = 0,
                                    welcome_to_first_signal_seconds: int = 60,
                                    signal_to_win_seconds: int = 45,
                                    between_signals_seconds: int = 25,
                                    last_signal_to_summary_seconds: int = 40,
                                    template: str = "lkr"):
        """Отправляет сообщения и изображения в канал"""
        try:
            # Парсим сообщения из JSON с сохранением форматирования
            if isinstance(messages, str):
                try:
                    message_list = json.loads(messages)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing messages JSON: {e}")
                    # Если не удалось распарсить JSON, используем строку как есть
                    message_list = [messages, "", ""]
            else:
                message_list = messages
            
            if len(message_list) != 3:
                raise ValueError("Необходимо указать ровно три сообщения")

            # Отправляем первое сообщение с сохранением форматирования и повторными попытками
            logger.info("Sending welcome message")
            welcome_sent = False
            max_welcome_retries = 3
            welcome_retry_count = 0
            
            while welcome_retry_count < max_welcome_retries and not welcome_sent:
                try:
                    await asyncio.wait_for(
                        self.bot.send_message(
                            chat_id=channel_id,
                            text=message_list[0],
                            parse_mode='HTML'  # Используем HTML для сохранения форматирования
                        ),
                        timeout=15
                    )
                    welcome_sent = True
                    logger.info("Welcome message sent successfully")
                except asyncio.TimeoutError:
                    welcome_retry_count += 1
                    logger.warning(f"Timeout sending welcome message, retry {welcome_retry_count}/{max_welcome_retries}")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Error sending welcome message: {e}")
                    break
                    
            if not welcome_sent:
                logger.error(f"Failed to send welcome message after {max_welcome_retries} retries")
                # Продолжаем выполнение, даже если не удалось отправить приветственное сообщение
            
            # Используем задержку между приветственным сообщением и 1 сигналом
            logger.info(f"Waiting {welcome_to_first_signal_seconds} seconds before first signal")
            await asyncio.sleep(welcome_to_first_signal_seconds)
            logger.info("Wait completed, proceeding to signals")

            # Генерируем изображения с использованием суммы ставки и выбранного шаблона
            logger.info(f"Generating {images_count} images with bet_amount={bet_amount} and template={template}")
            generated_images, data_list = await self.generate_images(images_count, bet_amount, template)
            if not generated_images or not data_list:
                logger.error("Failed to generate images")
                return
            
            logger.info(f"Successfully generated {len(generated_images)} images")

            total_multiplied = 0
            success_count = 0
            results_list = []

            # Отправляем каждое изображение последовательно
            logger.info(f"Starting to send {len(generated_images)} images one by one")
            
            # Подготавливаем все сообщения и данные для отправки
            messages_to_send = []
            
            for i, (image_path, data) in enumerate(zip(generated_images, data_list)):
                try:
                    logger.info(f"Preparing data for image {i+1}/{len(generated_images)}")
                    
                    # Проверяем, является ли это fail-изображением
                    multiplied_str = data.get('multiplied_number', '0')
                    is_fail = multiplied_str == 'fail'

                    if not is_fail:
                        # Убираем 'x' с конца, удаляем запятые и преобразуем в float
                        number_str = data['multiplied_number'].rstrip('x')
                        # Удаляем запятые из строки перед преобразованием в float
                        number = float(number_str.replace(',', ''))
                        total_multiplied += number
                        success_count += 1

                        # Добавляем успешный результат в список
                        sub_num_str = data['subtracted_number'].rstrip('x')
                        results_list.append(f"✅ {sub_num_str}")

                        # Вычисляем среднее между main_number и subtracted_number
                        try:
                            main_num = float(data['main_number'].rstrip('x'))
                            sub_num = float(data['subtracted_number'].rstrip('x'))
                            avg_number = round((main_num + sub_num) / 2)
                            message_text = message_list[1].format(
                                average=f"{avg_number}x",
                                main_number=data['main_number'],
                                subtracted_number=data['subtracted_number'],
                                multiplied_number=data['multiplied_number']
                            )
                        except (ValueError, AttributeError):
                            message_text = message_list[1].format(
                                average="N/A",
                                main_number=data['main_number'],
                                subtracted_number=data['subtracted_number'],
                                multiplied_number=data['multiplied_number']
                            )

                    else:
                        # Для fail-изображений добавляем отрицательное значение к общей сумме
                        try:
                            if multiplied_str != 'fail':
                                number = float(multiplied_str.replace(',', ''))
                                total_multiplied += number
                        except (ValueError, AttributeError):
                            pass

                        # Добавляем неудачный результат в список
                        sub_num_str = data['subtracted_number'].rstrip('x')
                        results_list.append(f"❌ {sub_num_str}")

                        # Формируем сообщение для fail-изображения
                        try:
                            message_text = message_list[1].format(
                                average="FAIL",
                                main_number=data['main_number'],
                                subtracted_number=data['subtracted_number'],
                                multiplied_number="FAIL"
                            )
                        except (ValueError, AttributeError, KeyError):
                            message_text = f"❌ FAIL: {data['subtracted_number']}"
                    
                    # Добавляем данные для отправки
                    messages_to_send.append({
                        'message_text': message_text,
                        'image_path': image_path
                    })
                    
                except Exception as e:
                    logger.error(f"Error preparing data for image {i}: {e}")
                    continue
            
            # Последовательно отправляем все сообщения и изображения
            logger.info(f"Starting to send {len(messages_to_send)} signals one by one")
            
            for i, item in enumerate(messages_to_send):
                try:
                    # Отправляем сообщение перед картинкой с повторными попытками
                    logger.info(f"Sending message for signal {i+1}")
                    max_msg_retries = 3
                    msg_retry_count = 0
                    msg_success = False
                    msg = None
                    
                    while msg_retry_count < max_msg_retries and not msg_success:
                        try:
                            # Увеличиваем таймаут для отправки сообщения
                            msg = await asyncio.wait_for(
                                self.bot.send_message(
                                    chat_id=channel_id,
                                    text=item['message_text'],
                                    parse_mode='HTML'
                                ),
                                timeout=15  # Увеличиваем таймаут до 15 секунд
                            )
                            msg_success = True
                            logger.info(f"Message for signal {i+1} sent successfully")
                        except asyncio.TimeoutError:
                            msg_retry_count += 1
                            logger.warning(f"Timeout sending message {i+1}, retry {msg_retry_count}/{max_msg_retries}")
                            await asyncio.sleep(2)  # Небольшая пауза перед повторной попыткой
                        except Exception as e:
                            logger.error(f"Error sending message {i+1}: {e}")
                            break
                    
                    if not msg_success or not msg:
                        logger.error(f"Failed to send message {i+1} after {max_msg_retries} retries")
                        # Пропускаем этот сигнал и переходим к следующему
                        continue
                    
                    # Используем задержку между сигналом и выигрышем
                    logger.info(f"Waiting {signal_to_win_seconds} seconds before sending image {i+1}")
                    await asyncio.sleep(signal_to_win_seconds)  

                    # Отправляем изображение в ответ на сообщение с повторными попытками
                    logger.info(f"Sending image {i+1}")
                    max_retries = 3
                    retry_count = 0
                    success = False
                    
                    while retry_count < max_retries and not success:
                        try:
                            with open(item['image_path'], 'rb') as photo:
                                # Увеличиваем таймаут для отправки изображения
                                await asyncio.wait_for(
                                    self.bot.send_photo(
                                        chat_id=channel_id,
                                        photo=photo,
                                        reply_to_message_id=msg.message_id
                                    ),
                                    timeout=30  # Увеличиваем таймаут до 30 секунд
                                )
                            success = True
                            logger.info(f"Image {i+1} sent successfully")
                        except asyncio.TimeoutError:
                            retry_count += 1
                            logger.warning(f"Timeout sending image {i+1}, retry {retry_count}/{max_retries}")
                            await asyncio.sleep(2)  # Небольшая пауза перед повторной попыткой
                        except Exception as e:
                            logger.error(f"Error sending image {i+1}: {e}")
                            break
                    
                    if not success:
                        logger.error(f"Failed to send image {i+1} after {max_retries} retries")
                        # Продолжаем с следующим сигналом, даже если этот не удался

                    # Делаем паузу перед следующим сигналом
                    if i < len(messages_to_send) - 1:
                        # Используем задержку между сигналами
                        logger.info(f"Waiting {between_signals_seconds} seconds before next signal")
                        await asyncio.sleep(between_signals_seconds)
                        logger.info("Wait completed, proceeding to next signal")  
                except Exception as e:
                    logger.error(f"Error sending signal {i+1}: {e}")
                    continue

            # Делаем паузу перед отправкой итогового сообщения
            logger.info(f"Waiting {last_signal_to_summary_seconds} seconds before sending summary")
            await asyncio.sleep(last_signal_to_summary_seconds)
            logger.info("Wait completed, proceeding to summary")
            
            # Отправляем итоговое сообщение с форматированным числом
            try:
                logger.info("Preparing summary message")
                # Форматируем число с разделителями тысяч
                formatted_total = "{:,.2f}".format(total_multiplied)
                # Формируем строку с результатами
                results_summary = "\n".join(results_list)
                try:
                    # Пробуем отформатировать сообщение с доступными переменными
                    final_message = message_list[2].format(
                        total=formatted_total, 
                        results=results_summary
                    )
                except KeyError as e:
                    # Если какая-то переменная отсутствует, логируем ошибку и используем базовый формат
                    logger.warning(f"Missing variable in final message format: {e}")
                    final_message = f"Итого: {formatted_total}\n\n{results_summary}"
                
                logger.info("Sending summary message")
                summary_sent = False
                max_summary_retries = 3
                summary_retry_count = 0
                
                while summary_retry_count < max_summary_retries and not summary_sent:
                    try:
                        await asyncio.wait_for(
                            self.bot.send_message(
                                chat_id=channel_id,
                                text=final_message,
                                parse_mode='HTML'
                            ),
                            timeout=15
                        )
                        summary_sent = True
                        logger.info("Summary message sent successfully")
                    except asyncio.TimeoutError:
                        summary_retry_count += 1
                        logger.warning(f"Timeout sending summary message, retry {summary_retry_count}/{max_summary_retries}")
                        await asyncio.sleep(2)
                    except Exception as e:
                        logger.error(f"Error sending summary message: {e}")
                        break
                        
                if not summary_sent:
                    logger.error(f"Failed to send summary message after {max_summary_retries} retries")
            except Exception as e:
                logger.error(f"Error sending final message: {e}")

        except Exception as e:
            logger.error(f"Error in send_message_with_image: {e}")
            raise

    async def show_channels_menu(self, update, context):
        """Показывает меню управления каналами"""
        keyboard = []
        channels = await self.get_channels()
        
        for channel in channels:
            try:
                chat = await self.bot.get_chat(channel.telegram_id)
                title = chat.title
                if title != channel.title:
                    channel.title = title
                    async with self.session_factory() as session:
                        await session.merge(channel)
                        await session.commit()
            except:
                title = channel.title or f"Канал {channel.telegram_id}"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📢 {title}", 
                    callback_data=f"show_channel:{channel.telegram_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "📅 Выберите канал для настройки рассылки:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text=text, reply_markup=reply_markup)

    async def show_channel_menu(self, update, context, channel_id: int):
        """Показывает меню управления конкретным каналом"""
        keyboard = [
            [InlineKeyboardButton("🔄 Проверить права", callback_data=f"check_permissions:{channel_id}")],
            [InlineKeyboardButton("⏰ Управление расписанием", callback_data=f"manage_schedules:{channel_id}")],
            [InlineKeyboardButton("❌ Удалить канал", callback_data=f"remove_channel:{channel_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Получаем информацию о канале
        async with self.session_factory() as session:
            query = select(Channel).where(Channel.telegram_id == channel_id)
            result = await session.execute(query)
            channel = result.scalar_one_or_none()

        if not channel:
            await update.callback_query.answer("❌ Канал не найден")
            return

        try:
            chat_info = await self.bot.get_chat(channel_id)
            channel_name = chat_info.title
            if channel.title != channel_name:
                channel.title = channel_name
                async with self.session_factory() as session:
                    await session.merge(channel)
                    await session.commit()
        except:
            channel_name = channel.title or f"Канал {channel_id}"

        schedules = await self.get_channel_schedules(channel_id)
        schedule_text = "Нет активных рассылок"
        if schedules:
            active_schedules = [s.time_of_day.strftime("%H:%M") for s in schedules if s.enabled]
            if active_schedules:
                schedule_text = f"Активные рассылки: {', '.join(active_schedules)}"

        text = f"📢 Канал: {channel_name}\n" \
               f"🆔 ID: {channel_id}\n" \
               f"⏰ {schedule_text}"

        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)

    async def show_schedule_menu(self, update, context, channel_id: int):
        """Показывает меню управления расписанием"""
        keyboard = []
        schedules = await self.get_channel_schedules(channel_id)
        
        for schedule in schedules:
            status = "✅" if schedule.enabled else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {schedule.time_of_day.strftime('%H:%M')}",
                    callback_data=f"edit_schedule:{channel_id}:{schedule.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("➕ Добавить рассылку", callback_data=f"add_schedule:{channel_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"show_channel:{channel_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "⏰ Управление рассылками\n\n" \
               "Нажмите на рассылку для редактирования или удаления.\n" \
               "Используйте кнопку «Добавить рассылку» для создания новой."
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text=text, reply_markup=reply_markup)

    async def show_edit_schedule_menu(self, update, context, channel_id: int, schedule_id: int):
        """Показывает меню редактирования рассылки"""
        schedule = await self.session.get(Schedule, schedule_id)
        if not schedule or schedule.channel_id != channel_id:
            await update.callback_query.answer("❌ Расписание не найдено")
            await self.show_schedule_menu(update, context, channel_id)
            return
        
        keyboard = [
            [InlineKeyboardButton("🕒 Изменить время", callback_data=f"change_time:{channel_id}:{schedule_id}")],
            [InlineKeyboardButton(
                "🔄 Включить" if not schedule.enabled else "🔄 Выключить",
                callback_data=f"toggle_schedule:{channel_id}:{schedule_id}"
            )],
            [InlineKeyboardButton("❌ Удалить рассылку", callback_data=f"delete_schedule:{channel_id}:{schedule_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=f"manage_schedules:{channel_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"📅 Управление рассылкой\n\n" \
               f"Текущее время: {schedule.time_of_day.strftime('%H:%M')}\n" \
               f"Статус: {'Включена' if schedule.enabled else 'Выключена'}"
        
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
