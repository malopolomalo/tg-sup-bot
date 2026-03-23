FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiogram==2.25.1 flask==2.3.3

COPY bot.py .

CMD ["python", "bot.py"]
