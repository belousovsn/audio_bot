# syntax=docker/dockerfile:1

# Этап сборки
FROM python:3.11-slim AS builder

# Установка рабочей директории
WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install -r requirements.txt

# Загрузка модели
RUN python -c "import whisper; whisper.load_model('large')"

# Финальный этап
FROM python:3.11-slim
WORKDIR /app

# Установка ffmpeg в финальном образе
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей и модели из этапа сборки
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /root/.cache/whisper /root/.cache/whisper

# Копирование кода приложения
COPY . .

# Проверка наличия ffmpeg (опционально)
RUN ffmpeg -version

# Запуск приложения
CMD ["python", "bot.py"]