# Python 3.12 slim base — küçük ve hızlı
FROM python:3.12-slim

# Chrome ve ChromeDriver kurulumu (Selenium için zorunlu)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    ca-certificates \
    --no-install-recommends

# Google Chrome'u resmi kanaldan kur
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
    http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Chrome sürümüne uyumlu ChromeDriver'ı kur
RUN CHROME_VER=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) && \
    LATEST=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VER}") && \
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/${LATEST}/linux64/chromedriver-linux64.zip" \
    -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /tmp && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    rm -rf /tmp/chromedriver*

# Çalışma dizini oluştur
WORKDIR /app

# Önce bağımlılıkları kopyala (Docker cache optimizasyonu)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY main.py .

# ChromeDriver yolunu ortam değişkeni olarak ayarla
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Container başlatıldığında botu çalıştır
CMD ["python", "main.py"]