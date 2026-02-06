FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget curl unzip ca-certificates
RUN apt-get install -y fonts-liberation libnss3 libatk-bridge2.0-0 libgtk-3-0 libx11-xcb1
RUN apt-get install -y libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2
RUN apt-get install -y libdrm2 libxshmfence1 libxfixes3 libxkbcommon0
RUN apt-get install -y xvfb xauth
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chrome

COPY ./main.py .

ENV DISPLAY=:99
EXPOSE 9001

CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 & exec uvicorn main:app --host 0.0.0.0 --port 9001"]