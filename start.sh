#!/bin/bash

# Создаем volume, если он еще не существует
docker volume create whisper_models > /dev/null 2>&1

# Запускаем контейнер для загрузки моделей
echo "Загружаем модели Whisper..."
docker run --rm -v whisper_models:/root/.cache/whisper kinzul/audio-messages-bot:latest \
    sh -c "pip install openai-whisper && \
           python -c 'import whisper; whisper.load_model(\"base\")' && \
           python -c 'import whisper; whisper.load_model(\"large\")'"

# Запускаем основное приложение
echo "Запускаем бота..."
docker-compose up -d 