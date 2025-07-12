# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Обновляем pip
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache/pip

COPY . .

CMD ["python", "__main__.py"]
