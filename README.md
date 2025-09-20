# Image Bot

Telegram бот для автоматической рассылки изображений по расписанию.

## Функциональность

- Управление каналами
- Создание расписаний рассылки
- Автоматическая генерация и отправка изображений
- Настраиваемые задержки между сообщениями и изображениями

## Развертывание на Digital Ocean

1. Создайте новый Droplet на Digital Ocean с Docker
2. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/image_bot.git
   cd image_bot
   ```

3. Создайте файл .env из примера:
   ```bash
   cp .env.example .env
   ```

4. Отредактируйте .env и укажите:
   - BOT_TOKEN - токен вашего Telegram бота
   - DB_PASSWORD - надежный пароль для базы данных
   - Другие необходимые настройки

5. Запустите приложение:
   ```bash
   docker-compose up -d
   ```

6. Проверьте логи:
   ```bash
   docker-compose logs -f
   ```

## Обновление бота

1. Остановите текущую версию:
   ```bash
   docker-compose down
   ```

2. Получите последние изменения:
   ```bash
   git pull
   ```

3. Пересоберите и запустите:
   ```bash
   docker-compose up -d --build
   ```

## Резервное копирование

База данных автоматически сохраняется в Docker volume. Для создания резервной копии:

```bash
docker-compose exec db pg_dump -U postgres image_bot > backup.sql
```

## Мониторинг

Логи бота доступны через:
```bash
docker-compose logs -f bot
```
