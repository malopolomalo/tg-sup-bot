FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir aiogram==2.25.1

COPY bot.py .

CMD ["python", "bot.py"]