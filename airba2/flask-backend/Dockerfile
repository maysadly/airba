FROM python:3.10-slim

# Установка рабочей директории
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_DEBUG=0

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Открываем порт
EXPOSE 5050

# Команда для запуска приложения
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "run:app"]