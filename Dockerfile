# syntax=docker/dockerfile:1

# Этап сборки
FROM python:3.11-slim AS builder

# Установка рабочей директории
WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install -r requirements.txt

# Финальный этап
FROM python:3.11-slim
WORKDIR /app

# Установка ffmpeg в финальном образе
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей из этапа сборки
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Копирование кода приложения
COPY . .

# Проверка наличия ffmpeg (опционально)
RUN ffmpeg -version

# Указываем volume для хранения моделей
VOLUME /root/.cache/whisper

# Запуск приложения
CMD ["python", "bot.py"]