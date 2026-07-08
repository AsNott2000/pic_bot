# 🔵 Discord Bot — Azure Container Apps Deployment Rehberi

> **Bu rehber kimler için?**
> Azure'u hiç kullanmamış, ilk defa bulut platformuna uygulama deploy edecek kişiler için hazırlanmıştır.
> Her adım ekran görüntüsü seviyesinde detaylı anlatılmıştır. Hiçbir adımı atlama!

---

## 📋 İçindekiler

1. [Kavramsal Harita — Ne Yapacağız?](#1-kavramsal-harita--ne-yapacagiz)
2. [Gereksinimler](#2-gereksinimler)
3. [Azure Hesabı Oluşturma](#3-azure-hesabi-olusturma)
4. [Azure CLI Kurulumu](#4-azure-cli-kurulumu)
5. [Resource Group Oluşturma](#5-resource-group-olusturma)
6. [Azure Container Registry (ACR) Oluşturma](#6-azure-container-registry-acr-olusturma)
7. [Dockerfile Hazırlama](#7-dockerfile-hazirlama)
8. [Azure Container Apps Ortamı Oluşturma](#8-azure-container-apps-ortami-olusturma)
9. [İlk Manuel Deploy (Test Amaçlı)](#9-ilk-manuel-deploy-test-amacli)
10. [GitHub Secrets Ayarlama](#10-github-secrets-ayarlama)
11. [CI/CD Pipeline — GitHub Actions](#11-cicd-pipeline--github-actions)
12. [Ortam Değişkenlerini Azure'da Yönetme](#12-ortam-degiskenlerini-azureda-yonetme)
13. [Logları İzleme](#13-loglari-izleme)
14. [Maliyet Yönetimi ve Ücretsiz Katman](#14-maliyet-yonetimi-ve-ucretsiz-katman)
15. [Sık Karşılaşılan Sorunlar](#15-sik-karsilasilan-sorunlar)

---

## 1. Kavramsal Harita — Ne Yapacağız?

Adımlara geçmeden önce büyük resmi anlayalım. Kafanda şu akış şemasını canlandır:

```
Sen (kod yaz)
    │
    ▼
GitHub'a push yap (git push)
    │
    ▼ (otomatik tetiklenir)
GitHub Actions Pipeline
    ├── Docker image oluşturur
    ├── Azure Container Registry'e (ACR) push eder
    └── Azure Container Apps'e "yeni sürümü çek ve çalıştır" komutu verir
                │
                ▼
        Azure Container Apps
        (botun çalıştığı yer — 7/24 açık)
```

**Kullanacağımız Azure servisleri:**

| Servis | Ne İşe Yarar | Ücretsiz mi? |
|--------|-------------|--------------|
| **Azure Container Registry (ACR)** | Docker image'larını depolar (Docker Hub gibi ama Azure'un kendi versiyonu) | Ücretli (Basic: ~$5/ay) |
| **Azure Container Apps** | Docker container'ını çalıştırır | İlk 180.000 vCPU-saniye/ay ücretsiz |
| **Resource Group** | Tüm Azure kaynaklarını bir arada tutar (klasör gibi) | Ücretsiz |

> **💡 İpucu:** Aylık maliyet tahmini: ~$5-10 USD (ACR Basic + minimum Container Apps kullanımı).
> İlk ay için Azure $200 ücretsiz kredi veriyor, bu yüzden ilk aylarda sıfır maliyet!

---

## 2. Gereksinimler

Başlamadan önce şunlara ihtiyacın var:

| Araç/Hesap | Link | Not |
|-----------|------|-----|
| Azure hesabı | [portal.azure.com](https://portal.azure.com) | Kredi kartı gerekiyor ama ücret kesilmez (ilk $200 kredi) |
| Azure CLI | [aka.ms/installazurecli](https://aka.ms/installazurecli) | Komut satırından Azure yönetmek için |
| Docker Desktop | [docker.com](https://www.docker.com/products/docker-desktop) | Local image build için |
| Git + GitHub hesabı | Zaten var | Kod deposu |
| Discord Bot Token | Discord Developer Portal | Zaten var |

---

## 3. Azure Hesabı Oluşturma

> Zaten Azure hesabın varsa bu adımı atla.

1. [portal.azure.com](https://portal.azure.com) adresine git
2. **"Start free"** veya **"Free account"** butonuna tıkla
3. Microsoft hesabınla giriş yap (yoksa yeni oluştur)
4. Formu doldur:
   - Ad, soyad, ülke (Türkiye)
   - Telefon numarasını doğrula (SMS kodu gelecek)
   - Kredi kartı bilgilerini gir — **ücret kesilmez**, sadece kimlik doğrulama için
5. Hesap oluşturulunca **Azure Portal** açılır — bu senin kontrol panelindir

> **⚠️ Önemli:** Kredi kartı bilgisi girilmeden hesap açılamaz. Ancak Azure, ücretsiz katmanı aşmadıkça ücret kesmez. İlk 30 gün $200 krediyle başlarsın.

---

## 4. Azure CLI Kurulumu

Azure CLI, terminal üzerinden Azure'u yönetmeni sağlar. Portal üzerinden de yapılabilir ama CLI çok daha hızlı.

### Windows'ta Kurulum

**PowerShell'i Yönetici olarak aç** (Başlat → PowerShell → Sağ tık → "Yönetici olarak çalıştır") ve çalıştır:

```powershell
# Azure CLI kurulumu (Windows Installer)
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'
Remove-Item .\AzureCLI.msi
```

Kurulum bittikten sonra **terminali kapat ve yeniden aç**, ardından:

```powershell
# Kurulumu doğrula
az version
```

Şuna benzer bir çıktı görmelisin:
```json
{
  "azure-cli": "2.x.x",
  ...
}
```

### Azure CLI ile Giriş Yap

```powershell
az login
```

Bu komut tarayıcıyı açar, Azure hesabınla giriş yapman istenir. Giriş başarılı olunca terminalde hesap bilgilerin görünür:

```json
[
  {
    "name": "Azure subscription 1",
    "state": "Enabled",
    "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    ...
  }
]
```

> **💡 İpucu:** Birden fazla subscription (abonelik) görürsen, doğru olanı seç:
> ```powershell
> az account set --subscription "Subscription Adı veya ID"
> ```

---

## 5. Resource Group Oluşturma

**Resource Group** = Azure'daki tüm kaynaklarını bir arada tutan klasör. Projeyi silmek istediğinde sadece bu grubu silmek yeterli olur.

```powershell
# Resource Group oluştur
# "pic-bot-rg" adını ve "westeurope" bölgesini kullanacağız
# Avrupa sunucusu: Türkiye'ye yakın, hızlı

az group create `
  --name pic-bot-rg `
  --location westeurope
```

Başarı mesajı:
```json
{
  "id": "/subscriptions/.../resourceGroups/pic-bot-rg",
  "location": "westeurope",
  "name": "pic-bot-rg",
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

**"provisioningState": "Succeeded"** görüyorsan her şey yolunda! ✅

---

## 6. Azure Container Registry (ACR) Oluşturma

ACR, Docker image'larını Azure içinde depolar. Docker Hub'a alternatif ama Azure Container Apps ile çok daha iyi entegre çalışır.

```powershell
# ACR oluştur
# NOT: ACR adı DÜNYA GENELINDE benzersiz olmalı!
# "picbotregistry" yerine kendi adını yaz, örn: "mehmetpicbot"

az acr create `
  --resource-group pic-bot-rg `
  --name picbotregistry `
  --sku Basic `
  --admin-enabled true
```

**Parametreler:**
- `--name`: Registry adı (küçük harf, rakam, harf; özel karakter yok)
- `--sku Basic`: En ucuz katman (~$5/ay) — botumuz için fazlasıyla yeterli
- `--admin-enabled true`: Username/password ile erişim için (CI/CD'de lazım)

Çıktıdan `loginServer` değerini kopyala — ileride lazım olacak:
```json
{
  "loginServer": "picbotregistry.azurecr.io", picbotregistry.azurecr.io
  ...
}
```

### ACR Kimlik Bilgilerini Al

```powershell
# ACR'a giriş için kullanıcı adı ve şifreyi al
az acr credential show --name picbotregistry
```

Çıktı:
```json
{
  "passwords": [                 {                                                                                         "name": "password",                                                                               "value": "5MUQoQ9K5u371hvZUtkcScZGDa91kLLp0xSJxex9WbH9aYGWquKtJQQJ99CGACfhMk5Eqg7NAAACAZCRQBk6"    },                                                                                                                      {                                                                                         "name": "password2",                                                                              "value": "5D93JA1DjGrffRhHGAA0YgnkMEu3t8JBmSXFyz1AePuZsWnWLnN9JQQJ99CGACfhMk5Eqg7NAAACAZCRtizQ"    }],
  "username": "picbotregistry"
}
```

Bu bilgileri bir yere not et — GitHub Secrets'a ekleyeceğiz.

---

## 7. Dockerfile Hazırlama

Proje kök dizininde (`pic_bot/`) `Dockerfile` dosyasını oluştur:

```dockerfile
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
```

> **💡 Neden bu kadar uzun?** Azure Container Apps, Chrome/Selenium gibi browser tabanlı araçları çalıştırmak için gerekli sistem kütüphanelerini içermiyor. Bu Dockerfile her şeyi sıfırdan kuruyor — bu sayede her ortamda aynı şekilde çalışır.

---

## 8. Azure Container Apps Ortamı Oluşturma

Azure Container Apps çalıştırmadan önce bir **Environment** (ortam) oluşturman gerekiyor. Bu ortam, container'ların ağ ve altyapı ayarlarını barındırır.

### 8.1 Container Apps Extension Kur

```powershell
# Azure CLI'ya Container Apps desteği ekle
az extension add --name containerapp --upgrade
```

### 8.2 Provider'ı Kaydet

```powershell
# Azure'a Container Apps ve Log servisi kullanacağımızı bildir
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

> Bu komutlar birkaç dakika sürebilir. Tamamlanmasını bekle.

### 8.3 Container Apps Ortamı Oluştur

```powershell
az containerapp env create `
  --name pic-bot-env `
  --resource-group pic-bot-rg `
  --location westeurope
```

Tamamlanınca:
```json
{
  "name": "pic-bot-env",
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

---

## 9. İlk Manuel Deploy (Test Amaçlı)

CI/CD kurmadan önce her şeyin çalıştığını manuel olarak test edelim. Bu aşama öğrenme açısından çok önemli — ne yaptığını anlamadan otomasyona geçme!

### 9.1 ACR'a Giriş Yap

```powershell
# Docker'ı ACR'a bağla
az acr login --name picbotregistry
```

### 9.2 Docker Image Oluştur

```powershell
# Proje klasörünün içinde olduğundan emin ol
cd "C:\Users\nurul\OneDrive\Masaüstü\Main DEV\Discord Bot\pic_bot"

# Image oluştur ve ACR adresini tag olarak ekle
# Format: <registry-adı>.azurecr.io/<image-adı>:tag
docker build -t picbotregistry.azurecr.io/pic-bot:latest .
```

Build birkaç dakika sürer (Chrome kurulumu yüzünden). Sondaki satır şöyle görünmeli:
```
Successfully built abc123def456
Successfully tagged picbotregistry.azurecr.io/pic-bot:latest
```

### 9.3 Image'ı ACR'a Push Et

```powershell
docker push picbotregistry.azurecr.io/pic-bot:latest
```

### 9.4 Container App Oluştur ve Çalıştır

Şimdi Azure Container Apps'te botu çalıştır. **Token ve diğer gizli bilgileri buraya gir:**

```powershell
az containerapp create --name pic-bot --resource-group pic-bot-rg --environment pic-bot-env --image picbotregistry.azurecr.io/pic-bot:latest --registry-server picbotregistry.azurecr.io --registry-username picbotregistry --registry-password"5MUQoQ9K5u371hvZUtkcScZGDa91kLLp0xSJxex9WbH9aYGWquKtJQQJ99CGACfhMk5Eqg7NAAACAZCRQBk6" --cpu 0.5 --memory 1.0Gi --min-replicas 1 --max-replicas 1 --env-vars DISCORD_TOKEN="MTUxOTYyNTI3MDMzMDY1NDczMA.GO8SOZbzk9-gWsUn8OEyFIOX4Nkb-7KM4XljAaE3lFSg" KANAL_ID="1012713692510556210" KICK_KULLANICI_ADI="picubclear" CHROMEDRIVER_PATH="/usr/bin/chromedriver"

**Parametreler açıklaması:**

| Parametre | Açıklama |
|-----------|----------|
| `--cpu 0.5` | Yarım CPU core — bot için yeterli |
| `--memory 1.0Gi` | 1 GB RAM — Chrome için minimum |
| `--min-replicas 1` | En az 1 container sürekli çalışsın |
| `--max-replicas 1` | En fazla 1 container (maliyet kontrolü) |
| `--env-vars` | Ortam değişkenleri (.env dosyası yerine) |

### 9.5 Çalışıp Çalışmadığını Kontrol Et

```powershell
# Container'ın durumunu kontrol et
az containerapp show `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --query "properties.runningStatus"
```

`"Running"` görüyorsan bot çalışıyor! 🎉

```powershell
# Logları izle
az containerapp logs show `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --tail 50
```

`[BOT] ... basariyla aktif oldu!` mesajını görürsen her şey mükemmel!

---

## 10. GitHub Secrets Ayarlama

CI/CD pipeline'ın çalışması için GitHub'a gizli bilgileri kaydetmen gerekiyor. Bu bilgiler şifrelenmiş olarak saklanır — Actions loglarında **asla** görünmez.

**GitHub Repon → Settings → Secrets and variables → Actions → New repository secret**

Her biri için tek tek "New repository secret" tıklayıp ekle:

| Secret Adı | Değer | Nereden Alınır |
|------------|-------|----------------|
| `AZURE_CREDENTIALS` | Servis hesabı JSON'u | Aşağıdaki komutla oluşturulacak |
| `ACR_LOGIN_SERVER` | `picbotregistry.azurecr.io` | ACR oluştururken çıktıdan |
| `ACR_USERNAME` | `picbotregistry` | `az acr credential show` çıktısından |
| `ACR_PASSWORD` | ACR şifresi | `az acr credential show` çıktısından |
| `DISCORD_TOKEN` | Discord bot token'ın | Discord Developer Portal |
| `KANAL_ID` | Discord kanal ID'si | Discord'dan kopyalanacak |
| `KICK_KULLANICI_ADI` | Kick kullanıcı adı | Kick profil URL'inden |
| `AZURE_RESOURCE_GROUP` | `pic-bot-rg` | Az önce oluşturduğumuz grup adı |
| `AZURE_CONTAINERAPP_NAME` | `pic-bot` | Container app adı |

### AZURE_CREDENTIALS Oluşturma

Bu en kritik adım. GitHub Actions'ın Azure'a erişmesi için bir "servis hesabı" oluşturuyoruz:

```powershell
# Önce subscription ID'ni al
az account show --query id --output tsv
# Çıktı: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (bunu kopyala)
```

```powershell
# Servis principal oluştur
# SUBSCRIPTION_ID_BURAYA kısmını bir önceki çıktıyla değiştir
az ad sp create-for-rbac `
  --name "pic-bot-github-actions" `
  --role contributor `
  --scopes /subscriptions/SUBSCRIPTION_ID_BURAYA/resourceGroups/pic-bot-rg `
  --sdk-auth
```

Çıktı şöyle görünecek — **tamamını kopyala** (süslü parantezler dahil):
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

Bu tüm JSON'u `AZURE_CREDENTIALS` secret olarak kaydet.

---

## 11. CI/CD Pipeline — GitHub Actions

Proje kök dizininde şu klasör yapısını oluştur:

```
pic_bot/
└── .github/
    └── workflows/
        └── deploy-azure.yml
```

### Windows'ta Klasör Oluşturma

```powershell
# Proje dizininde olduğundan emin ol
cd "C:\Users\nurul\OneDrive\Masaüstü\Main DEV\Discord Bot\pic_bot"

# Klasörü oluştur
mkdir .github\workflows
```

Şimdi `.github/workflows/deploy-azure.yml` dosyasını oluştur ve aşağıdaki içeriği yapıştır:

```yaml
name: 🔵 Deploy to Azure Container Apps

# main branch'e push yapılınca otomatik tetiklenir
on:
  push:
    branches:
      - main

jobs:
  build-and-deploy:
    name: Build & Deploy
    runs-on: ubuntu-latest

    steps:
      # ─────────────────────────────────────────────
      # ADIM 1: Kodu çek
      # ─────────────────────────────────────────────
      - name: 📥 Kodu checkout et
        uses: actions/checkout@v4

      # ─────────────────────────────────────────────
      # ADIM 2: Azure'a giriş yap
      # ─────────────────────────────────────────────
      - name: 🔑 Azure'a giriş yap
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      # ─────────────────────────────────────────────
      # ADIM 3: Azure Container Registry'ye giriş yap
      # ─────────────────────────────────────────────
      - name: 🐳 ACR'ye giriş yap
        uses: azure/docker-login@v1
        with:
          login-server: ${{ secrets.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      # ─────────────────────────────────────────────
      # ADIM 4: Docker image oluştur ve ACR'ye push et
      # ─────────────────────────────────────────────
      - name: 🔨 Docker image oluştur ve push et
        run: |
          docker build -t ${{ secrets.ACR_LOGIN_SERVER }}/pic-bot:latest .
          docker push ${{ secrets.ACR_LOGIN_SERVER }}/pic-bot:latest

      # ─────────────────────────────────────────────
      # ADIM 5: Container Apps'i yeni image ile güncelle
      # ─────────────────────────────────────────────
      - name: 🚀 Azure Container Apps'e deploy et
        run: |
          az extension add --name containerapp --upgrade --yes

          az containerapp update \
            --name ${{ secrets.AZURE_CONTAINERAPP_NAME }} \
            --resource-group ${{ secrets.AZURE_RESOURCE_GROUP }} \
            --image ${{ secrets.ACR_LOGIN_SERVER }}/pic-bot:latest \
            --set-env-vars \
              DISCORD_TOKEN="${{ secrets.DISCORD_TOKEN }}" \
              KANAL_ID="${{ secrets.KANAL_ID }}" \
              KICK_KULLANICI_ADI="${{ secrets.KICK_KULLANICI_ADI }}" \
              CHROMEDRIVER_PATH="/usr/bin/chromedriver"

          echo "✅ Deploy başarıyla tamamlandı!"

      # ─────────────────────────────────────────────
      # ADIM 6: Sonucu kontrol et
      # ─────────────────────────────────────────────
      - name: ✅ Deploy durumunu kontrol et
        run: |
          STATUS=$(az containerapp show \
            --name ${{ secrets.AZURE_CONTAINERAPP_NAME }} \
            --resource-group ${{ secrets.AZURE_RESOURCE_GROUP }} \
            --query "properties.runningStatus" \
            --output tsv)
          echo "Container durumu: $STATUS"
```

### Pipeline'ı Aktive Et

```bash
git add .github/ Dockerfile
git commit -m "feat: azure ci/cd pipeline eklendi"
git push origin main
```

Push yapılınca GitHub → **Actions** sekmesine git. Pipeline'ın çalıştığını göreceksin. Her adımın yanında ✅ görürsen başarılı!

---

## 12. Ortam Değişkenlerini Azure'da Yönetme

`.env` dosyası Azure'da **kullanılmaz**. Bunun yerine Container Apps'in kendi env/secret sistemi var.

### Mevcut env değişkenlerini görüntüle

```powershell
az containerapp show `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --query "properties.template.containers[0].env"
```

### Tek bir değişkeni güncelle (örn: token değiştirdiysen)

```powershell
az containerapp update `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --set-env-vars DISCORD_TOKEN="YENI_TOKEN_BURAYA"
```

> Değişkeni güncelledikten sonra container otomatik yeniden başlar.

---

## 13. Logları İzleme

### Azure Portal Üzerinden (En Kolay Yol — Tavsiye Edilir)

1. [portal.azure.com](https://portal.azure.com) adresine git
2. Üst arama çubuğuna `pic-bot` yaz → Container Apps sonucuna tıkla
3. Sol menüde **"Log stream"** seçeneğine tıkla
4. Canlı logları tarayıcında izle — hiçbir komut gerekmez!

### Azure CLI ile Log İzleme

```powershell
# Son 100 satır log
az containerapp logs show `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --tail 100

# Canlı log akışı (Ctrl+C ile durdur)
az containerapp logs show `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --follow
```

### Container'ı Yeniden Başlatma

```powershell
# Mevcut revision adını al
$REVISION = az containerapp show `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --query "properties.latestRevisionName" `
  --output tsv

# O revision'ı yeniden başlat
az containerapp revision restart `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --revision $REVISION
```

---

## 14. Maliyet Yönetimi ve Ücretsiz Katman

### Aylık Maliyet Tahmini

| Servis | Katman | Tahmini Maliyet |
|--------|--------|----------------|
| Azure Container Registry | Basic | ~$5/ay |
| Azure Container Apps | Consumption | İlk 180.000 vCPU-saniye/ay **ücretsiz** |
| Log Analytics | İlk 5 GB/ay | **Ücretsiz** |
| **Toplam (7/24 çalışma)** | | **~$26-35/ay** |

> **💡 Maliyet Notu:** 7/24 çalışan bir bot için Container Apps pahalı olabilir.
> Daha ucuz alternatif: **Azure Container Instances (ACI)** — 0.5 vCPU + 1GB RAM ≈ ~$13/ay.
> Başlangıç için Container Apps kullanabilirsin, maliyet sorun olursa ACI'ye geçersin.

### Harcama Uyarısı Kurma (Sürpriz Fatura Önleme)

Azure Portal → arama çubuğuna "Cost Management" yaz → **Budgets** → **+ Add**

```
- Budget name: pic-bot-budget
- Amount: $20
- Time grain: Monthly
- Alert threshold: 80% ($16 geçince uyar)
- Email: kendi e-postanı gir
```

Kaydet. Artık $16'yı geçersen e-posta uyarısı alırsın.

---

## 15. Sık Karşılaşılan Sorunlar

### ❌ "az: command not found" veya az tanınmıyor

**Sebep:** Azure CLI kurulmadı veya terminal yenilenmedi.

**Çözüm:**
```powershell
# Terminali kapat, yeniden aç ve test et:
az version

# Hala hata veriyorsa bilgisayarı yeniden başlat.
# Yine hata veriyorsa tekrar kurulum yap:
winget install Microsoft.AzureCLI
```

---

### ❌ "The registry name 'picbotregistry' is already taken"

**Sebep:** ACR adları tüm dünyada benzersiz olmalı.

**Çözüm:** Farklı ve özgün bir ad dene:
```powershell
az acr create --resource-group pic-bot-rg --name SENIN_ADIN_picbot --sku Basic --admin-enabled true
# Ardından tüm komutlarda "picbotregistry" yerine yeni adını kullan
```

---

### ❌ "UNAUTHORIZED: authentication required"

**Sebep:** ACR'ye giriş yapılmamış.

**Çözüm:**
```powershell
az acr login --name picbotregistry
```

---

### ❌ Container başlıyor ama hemen duruyor (sürekli restart)

**Sebep:** Büyük ihtimalle çevre değişkeni eksik veya Chrome başlatılamıyor.

**Teşhis:**
```powershell
az containerapp logs show `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --tail 50
```

- `TypeError: expected token to be str, not NoneType` → `DISCORD_TOKEN` eksik
- `Chrome not found` → Dockerfile'da Chrome kurulumu başarısız

**Çözüm:**
```powershell
# Token güncelle
az containerapp update `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --set-env-vars DISCORD_TOKEN="DOGRU_TOKEN_BURAYA"
```

---

### ❌ "Insufficient privileges" — AZURE_CREDENTIALS hatası

**Sebep:** Servis principal yeterli izinlere sahip değil veya JSON yanlış kopyalandı.

**Çözüm:** Servis principal'ı sil ve yeniden oluştur:
```powershell
# Önce client ID'yi bul
az ad sp list --display-name "pic-bot-github-actions" --query "[].appId" --output tsv

# Sil
az ad sp delete --id "BURAYA_CLIENT_ID"

# Yenisini oluştur
az ad sp create-for-rbac `
  --name "pic-bot-github-actions" `
  --role contributor `
  --scopes /subscriptions/SUBSCRIPTION_ID/resourceGroups/pic-bot-rg `
  --sdk-auth
```

---

### ❌ GitHub Actions pipeline başlamıyor

**Sebep:** Workflow dosyasının yolu yanlış veya YAML sözdizimi hatalı.

**Kontrol:**
```powershell
# Dosyanın doğru yerde olduğunu doğrula
ls .github\workflows\
# "deploy-azure.yml" görünmeli
```

GitHub → Actions sekmesinde workflow görünmüyorsa dosyayı push etmeyi unutmuş olabilirsin.
YAML girintilerine dikkat et — TAB değil, boşluk kullan.

---

### ❌ Yüksek fatura uyarısı aldım

**Çözüm 1 — Container'ı devre dışı bırak:**
```powershell
az containerapp revision deactivate `
  --name pic-bot `
  --resource-group pic-bot-rg `
  --revision $(az containerapp show --name pic-bot --resource-group pic-bot-rg --query "properties.latestRevisionName" --output tsv)
```

**Çözüm 2 — Tüm kaynakları sil (kalıcı, geri alınamaz!):**
```powershell
# UYARI: Bu komut her şeyi siler!
az group delete --name pic-bot-rg --yes
```

---

## 🔒 Güvenlik Kontrol Listesi

Aşağıdaki her maddeyi tamamladığına emin ol:

- [ ] `.env` dosyası `.gitignore`'da ve GitHub'a push edilmedi
- [ ] `AZURE_CREDENTIALS` JSON'unu kimseyle paylaşmadın ve not defterine yapıştırmadın
- [ ] ACR şifresi GitHub Secrets'ta güvenli şekilde saklanıyor
- [ ] Bütçe uyarısı kuruldu (Azure Cost Management)
- [ ] Servis principal sadece `pic-bot-rg` Resource Group'una erişebiliyor (tüm subscription değil)
- [ ] Discord token'ın güvende ve değiştirilmesi gerekirse biliyorsun nasıl yapılacağını

---

## 🗑️ Her Şeyi Temizleme

Botu kapatıp tüm Azure kaynaklarını silmek istersen **tek komut** yeterli:

```powershell
az group delete --name pic-bot-rg --yes --no-wait
```

Bu komut; Container App, ACR, Container Apps Environment, Log Analytics — hepsini siler. Faturalama anında durur.

---

## 🆘 Yardım Al

Takıldığın yer olursa:

- **Azure Resmi Dokümantasyon:** [docs.microsoft.com/azure/container-apps](https://docs.microsoft.com/azure/container-apps)
- **Azure CLI Yardım:** `az containerapp --help` veya `az containerapp create --help`
- **GitHub Actions Logları:** Repo → Actions → İlgili workflow → Hatalı adıma tıkla
- **Azure Portal Log Stream:** portal.azure.com → Container Apps → pic-bot → Log stream

---

*Son güncelleme: Temmuz 2026*
*Bu rehber `pic_bot` projesi için özelleştirilmiştir.*
