# 🚀 Discord Bot — Docker + AWS EC2 + CI/CD Deployment Rehberi

> Bu rehber, `pic_bot` Discord botunu Docker ile paketleyip GitHub Actions üzerinden otomatik olarak AWS EC2'ya deploy etmeyi adım adım anlatır.

---

## 📋 İçindekiler

1. [Gereksinimler](#1-gereksinimler)
2. [Proje Dosya Yapısı](#2-proje-dosya-yapısı)
3. [Dockerfile Oluşturma](#3-dockerfile-oluşturma)
4. [Docker Compose Oluşturma](#4-docker-compose-oluşturma)
5. [AWS EC2 Kurulumu](#5-aws-ec2-kurulumu)
6. [EC2'ya Docker Kurma](#6-ec2ya-docker-kurma)
7. [GitHub Secrets Ayarlama](#7-github-secrets-ayarlama)
8. [CI/CD Pipeline — GitHub Actions](#8-cicd-pipeline--github-actions)
9. [İlk Deploy](#9-ilk-deploy)
10. [Güncelleme & Sonraki Pushlar](#10-guncelleme--sonraki-pushlar)
11. [Logları İzleme](#11-loglari-izleme)
12. [Sık Karşılaşılan Sorunlar](#12-sik-karsilasilan-sorunlar)

---

## 1. Gereksinimler

| Araç | Sürüm | Amaç |
|------|-------|-------|
| Docker | 24+ | Bot'u container içinde çalıştırmak |
| Docker Hub hesabı | — | Image'ları depolamak |
| AWS hesabı | — | EC2 sunucusu |
| GitHub hesabı | — | Kod deposu + CI/CD |
| EC2 instance | t2.micro (ücretsiz katman) | Sunucu |

---

## 2. Proje Dosya Yapısı

Tüm işlemler tamamlandığında proje dizinin şöyle görünmesi gerekir:

```
pic_bot/
├── .github/
│   └── workflows/
│       └── deploy.yml       <- CI/CD pipeline tanımı
├── main.py                  <- Bot kodu
├── Dockerfile               <- Docker image tarifi
├── docker-compose.yml       <- Container yönetimi
├── requirements.txt         <- Python bağımlılıkları
├── .env                     <- Gizli bilgiler (GIT'e EKLENMEDİ!)
├── .gitignore
├── README.md
└── DEPLOYMENT.md            <- Bu dosya
```

---

## 3. Dockerfile Oluşturma

Proje kök dizininde `Dockerfile` adlı dosya oluştur:

```dockerfile
# Python 3.12 + Selenium için Chrome destekli base image
FROM python:3.12-slim

# Chrome ve gerekli sistem araçlarını kur
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    --no-install-recommends && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Bağımlılıkları önce kopyala (cache optimizasyonu)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY main.py .

# Bot'u başlat
CMD ["python", "main.py"]
```

---

## 4. Docker Compose Oluşturma

`docker-compose.yml` dosyası oluştur:

```yaml
version: "3.9"

services:
  pic_bot:
    image: ${DOCKER_USERNAME}/pic_bot:latest
    container_name: pic_bot
    restart: unless-stopped          # Crash olursa otomatik yeniden başlar
    env_file:
      - .env                         # Gizli değişkenleri .env'den okur
    environment:
      - PYTHONUNBUFFERED=1           # Logları anlık görmek için
    shm_size: '256mb'               # Selenium/Chrome için paylaşımlı bellek
```

`requirements.txt` dosyası oluştur:

```
discord.py
selenium
webdriver-manager
python-dotenv
```

---

## 5. AWS EC2 Kurulumu

### 5.1 EC2 Instance Oluşturma

1. AWS Console → **EC2** → **Launch Instance**
2. Ayarlar:
   - **Name**: `pic-bot-server`
   - **AMI**: `Ubuntu Server 22.04 LTS` *(ücretsiz katman uyumlu)*
   - **Instance type**: `t2.micro` *(ücretsiz katman)*
   - **Key pair**: Yeni oluştur → `.pem` dosyasını indir ve güvenli yerde sakla!
3. **Security Group** ayarları (Inbound Rules):

   | Type | Port | Source |
   |------|------|--------|
   | SSH  | 22   | My IP  |

4. **Launch Instance** butonuna bas.

### 5.2 Elastic IP Atama (Sabit IP için)

1. EC2 → **Elastic IPs** → **Allocate Elastic IP**
2. Oluşturulan IP'yi instance'a **Associate** et
3. Bu IP artık sunucunun kalıcı adresi olacak

---

## 6. EC2'ya Docker Kurma

SSH ile sunucuya bağlan:

```bash
# Windows'ta PowerShell veya WSL ile:
ssh -i "anahtar-dosyan.pem" ubuntu@<EC2_PUBLIC_IP>
```

Bağlandıktan sonra Docker'ı kur:

```bash
# Sistem güncellemesi
sudo apt update && sudo apt upgrade -y

# Docker kurulumu
curl -fsSL https://get.docker.com | sudo sh

# Kullanıcıyı docker grubuna ekle (sudo gerektirmemek için)
sudo usermod -aG docker ubuntu

# Oturumu yenile
newgrp docker

# Doğrula
docker --version
```

Docker Compose kurulumu:

```bash
sudo apt install -y docker-compose-plugin
docker compose version
```

---

## 7. GitHub Secrets Ayarlama

GitHub Actions'ın EC2'ya bağlanabilmesi ve Docker Hub'a push yapabilmesi için secrets eklemen gerekir.

**GitHub Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret Adı | Değer | Açıklama |
|------------|-------|----------|
| `DOCKER_USERNAME` | Docker Hub kullanıcı adın | Image push için |
| `DOCKER_PASSWORD` | Docker Hub şifren veya Access Token | Image push için |
| `EC2_HOST` | EC2 Public IP adresi | SSH bağlantısı için |
| `EC2_USER` | `ubuntu` | SSH kullanıcısı |
| `EC2_SSH_KEY` | `.pem` dosyasının **tüm içeriği** | SSH kimlik doğrulama |
| `DISCORD_TOKEN` | Bot token'ın | Bot için |
| `KANAL_ID` | Discord kanal ID'si | Bot için |
| `KICK_KULLANICI_ADI` | Kick kullanıcı adı | Bot için |

> **EC2_SSH_KEY** için: `.pem` dosyasını not defterinde aç,
> `-----BEGIN RSA PRIVATE KEY-----` ile başlayan tüm içeriği kopyala ve secret olarak yapıştır.

---

## 8. CI/CD Pipeline — GitHub Actions

`.github/workflows/deploy.yml` dosyasını oluştur:

```yaml
name: Deploy Discord Bot to EC2

on:
  push:
    branches:
      - main        # main branch'e push yapılınca tetiklenir

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      # 1. Kodu çek
      - name: Kodu checkout et
        uses: actions/checkout@v4

      # 2. Docker Hub'a giriş yap
      - name: Docker Hub'a giriş
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      # 3. Docker image oluştur ve push et
      - name: Image oluştur ve push et
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ secrets.DOCKER_USERNAME }}/pic_bot:latest

      # 4. EC2'ya SSH ile bağlan ve deploy et
      - name: EC2'ya deploy et
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            mkdir -p /home/ubuntu/pic_bot
            cd /home/ubuntu/pic_bot

            # .env dosyasını EC2'da oluştur
            cat > .env << EOF
            DISCORD_TOKEN=${{ secrets.DISCORD_TOKEN }}
            KANAL_ID=${{ secrets.KANAL_ID }}
            KICK_KULLANICI_ADI=${{ secrets.KICK_KULLANICI_ADI }}
            EOF

            # docker-compose.yml dosyasını güncelle
            cat > docker-compose.yml << EOF
            version: "3.9"
            services:
              pic_bot:
                image: ${{ secrets.DOCKER_USERNAME }}/pic_bot:latest
                container_name: pic_bot
                restart: unless-stopped
                env_file:
                  - .env
                environment:
                  - PYTHONUNBUFFERED=1
                shm_size: '256mb'
            EOF

            # En son image'ı çek
            docker pull ${{ secrets.DOCKER_USERNAME }}/pic_bot:latest

            # Eski container'ı durdur ve yeni başlat
            docker compose down || true
            docker compose up -d

            # Eski image'ları temizle (disk tasarrufu)
            docker image prune -f

            echo "Deploy tamamlandi!"
```

---

## 9. İlk Deploy

### 9.1 EC2'da Dizin Oluştur

Sunucuya SSH ile bağlan ve çalışma dizini oluştur:

```bash
ssh -i "anahtar-dosyan.pem" ubuntu@<EC2_PUBLIC_IP>
mkdir -p /home/ubuntu/pic_bot
```

### 9.2 Yeni Dosyaları GitHub'a Push Et

Tüm dosyaları commit'leyip push et:

```bash
git add Dockerfile docker-compose.yml requirements.txt .github/
git commit -m "feat: docker + ci/cd pipeline eklendi"
git push origin main
```

Push yapılınca GitHub Actions otomatik olarak:
1. Image'ı build eder
2. Docker Hub'a push eder
3. EC2'ya SSH bağlanır
4. `.env` dosyasını oluşturur
5. Container'ı başlatır

**GitHub → Actions** sekmesinden pipeline'ın durumunu gerçek zamanlı izleyebilirsin.

---

## 10. Güncelleme & Sonraki Pushlar

Botun kodunu güncellediğinde tek yapman gereken:

```bash
git add .
git commit -m "güncelleme açıklaması"
git push origin main
```

Pipeline otomatik devreye girer, EC2'daki bot birkaç dakika içinde yeni sürümle çalışır. Sıfır elle müdahale!

---

## 11. Logları İzleme

EC2'ya SSH ile bağlanıp logları izle:

```bash
# Canlı log akışı (Ctrl+C ile çık)
docker logs -f pic_bot

# Son 50 satır log
docker logs --tail 50 pic_bot

# Tüm çalışan container'ları listele
docker ps

# Container'ı manuel yeniden başlat
docker restart pic_bot

# Container'ı durdur
docker compose -f /home/ubuntu/pic_bot/docker-compose.yml down

# Container'ı tekrar başlat
docker compose -f /home/ubuntu/pic_bot/docker-compose.yml up -d
```

---

## 12. Sık Karşılaşılan Sorunlar

### Chrome bulunamıyor hatası
```
selenium.common.exceptions.WebDriverException: Chrome not found
```
**Çözüm:** Dockerfile'daki Chrome kurulum adımlarını kontrol et.
`--no-sandbox` ve `--disable-dev-shm-usage` argümanlarının `main.py`'de mevcut olduğundan emin ol.

---

### Bot başlamıyor, token None geliyor
```
TypeError: expected token to be str, not NoneType
```
**Çözüm:** GitHub Secrets'a doğru değerlerin girildiğini kontrol et.
Actions logunda `.env` oluşturma adımının başarılı olup olmadığını doğrula.

---

### SSH bağlanamıyor
```
Permission denied (publickey)
```
**Çözüm:** `EC2_SSH_KEY` secret'ını kontrol et.
`.pem` dosyasının `-----BEGIN ... KEY-----` satırları dahil **tüm içeriği** secret olarak girilmeli.

---

### Container sürekli yeniden başlıyor
**Çözüm:** Logları incele:
```bash
docker logs pic_bot --tail 100
```
Büyük ihtimalle token hatalı veya Chrome başlatılamıyor.

---

### Pipeline başlamıyor
**Çözüm:** `.github/workflows/deploy.yml` dosyasının tam olarak bu dizin yapısında olduğunu doğrula.
GitHub → Actions sekmesinde workflow görünmüyorsa dosya yolu hatalıdır.

---

## Güvenlik Hatırlatmaları

- `.env` dosyasını **asla** Git'e ekleme (`.gitignore`'da zaten var)
- AWS EC2 Security Group'ta **yalnızca SSH (22) portunu** açık bırak, kaynak olarak kendi IP'ni seç
- Docker Hub'da şifre yerine **Access Token** kullan: Docker Hub → Account Settings → Security → New Access Token
- `.pem` dosyasını kimseyle paylaşma, güvenli bir yerde sakla

---

*Son güncelleme: Temmuz 2026*
