FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Playwright deps already in base image, just ensure
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -r requirements.txt

COPY bot.py bale_messenger.py message.txt contacts_sample.csv entrypoint.sh ./
COPY .env.example .env.example

RUN chmod +x entrypoint.sh bot.py bale_messenger.py

# دیتای بله (پروفایل کروم) روی volume می‌مونه تا لاگین حفظ بشه
VOLUME ["/data"]

ENV BALE_CDP=http://127.0.0.1:9222
ENV BALE_DATA_DIR=/data/.bale-chrome
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]
