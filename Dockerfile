# Используем Python 3.12
FROM python:3.12-slim

# Установка системных зависимостей и tzdata для работы с временными зонами
RUN apt-get update && apt-get install -y \
    gcc \
    fonts-liberation \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем временную зону
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Создание и переход в рабочую директорию
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создаем директорию для output если её нет
RUN mkdir -p output && chmod 777 output

# Установка переменных окружения
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Создание пользователя без прав root и настройка прав
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app
USER appuser

EXPOSE 8080

# Запуск миграций и бота
CMD echo "Server time: $(date)" && alembic upgrade head && python -m src.image_bot.bot_main