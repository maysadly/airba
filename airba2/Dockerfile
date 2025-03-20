FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей для компиляции и системных библиотек
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Открываем порт
EXPOSE 5000

# Запускаем сервер
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
