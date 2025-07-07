# Dockerfile
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости, чтобы кешировать этот слой
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY . .

# Команда для запуска (будет переопределена в docker-compose, но полезна для standalone запуска)
CMD ["python", "__main__.py"]
