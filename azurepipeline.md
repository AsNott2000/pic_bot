# Azure Pipelines'e Geçiş Rehberi

Bu belge, mevcut GitHub Actions tabanlı deploy pipeline'ını Azure DevOps üzerinden çalışan Azure Pipelines'e taşımak için adım adım rehber sunar. Örnek proje bu repo için hazırlanmıştır; uygulama Azure Container Apps üzerinde çalışmaktadır.

---

## 1. Ne değişecek?

Şu anki yapı:
- GitHub Actions: GitHub üzerinde çalışan CI/CD pipeline
- Azure tarafı: Container Registry + Container Apps + Azure kaynakları

Azure Pipelines'e geçtiğinde temel akış şu olur:

1. Kod GitHub'a push edilir
2. Azure DevOps Pipeline tetiklenir
3. Docker image oluşturulur
4. Azure Container Registry'e push edilir
5. Azure Container Apps güncellenir

---

## 2. Ön Hazırlık

Aşağıdaki şeyler hazır olmalı:

- Azure DevOps hesabı
- Azure aboneliği
- Azure Container Registry (ACR)
- Azure Container Apps
- GitHub reposu
- Uygulama için gerekli ortam değişkenleri

Örnek olarak bu projede kullanılacak değerler:
- ACR login server: `yourregistry.azurecr.io`
- Container App adı: `pic-bot`
- Resource Group: `pic-bot-rg`

---

## 3. Azure DevOps Projesi Oluşturma

1. Azure DevOps'a git: https://dev.azure.com
2. Yeni bir organization oluştur veya mevcut kullan
3. Yeni bir project oluştur
4. Project içinde "Pipelines" bölümüne gir

---

## 4. Azure ile Bağlantı Kurma (Service Connection)

Azure Pipelines'in Azure kaynaklarına erişebilmesi için bir service connection oluşturman gerekir.

### Adımlar

1. Azure DevOps project içinden "Project Settings"
2. "Service connections" bölümüne gir
3. "New service connection" → "Azure Resource Manager"
4. "Service principal (automatic)" seç
5. Abonelik ve resource group seç
6. Bağlantıya bir isim ver, örneğin: `azure-service-connection`

Bu bağlantı daha sonra pipeline içinde kullanılacaktır.

---

## 5. Gizli Değerleri Azure DevOps'ta Tanımlama

GitHub Secrets yerine Azure DevOps'ta "Library" veya "Variable Group" kullanılır.

### Variable Group Oluşturma

1. Azure DevOps → Pipelines → Library
2. "Variable group" oluştur
3. Aşağıdaki değişkenleri ekle:

- `AZURE_SERVICE_CONNECTION` → `azure-service-connection`
- `ACR_LOGIN_SERVER` → `yourregistry.azurecr.io`
- `ACR_USERNAME` → ACR kullanıcı adı
- `ACR_PASSWORD` → ACR şifresi
- `AZURE_CONTAINERAPP_NAME` → `pic-bot`
- `AZURE_RESOURCE_GROUP` → `pic-bot-rg`
- `DISCORD_TOKEN` → Discord bot token
- `KANAL_ID` → Discord kanal ID
- `KICK_KULLANICI_ADI` → Kick kullanıcı adı
- `YOUTUBE_KANAL_ID` → varsa
- `YOUTUBE_DUYURU_KANAL_ID` → varsa

> Önemli: Hassas bilgiler için `secret` işaretini aç.

---

## 6. Azure Pipelines YAML Dosyası Oluşturma

Proje kök dizinine bir dosya ekle: `azure-pipelines.yml`

Örnek içerik:

```yaml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: ubuntu-latest

variables:
- group: pic-bot-vars

steps:
- checkout: self

- task: AzureCLI@2
  displayName: Azure'a giriş yap
  inputs:
    azureSubscription: $(AZURE_SERVICE_CONNECTION)
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      az account show

- task: Docker@2
  displayName: ACR'ye giriş yap
  inputs:
    command: login
    containerRegistry: $(ACR_LOGIN_SERVER)

- script: |
    docker build -t $(ACR_LOGIN_SERVER)/pic-bot:latest .
    docker push $(ACR_LOGIN_SERVER)/pic-bot:latest
  displayName: Docker image oluştur ve push et

- script: |
    az extension add --name containerapp --upgrade --yes

    az containerapp update \
      --name $(AZURE_CONTAINERAPP_NAME) \
      --resource-group $(AZURE_RESOURCE_GROUP) \
      --image $(ACR_LOGIN_SERVER)/pic-bot:latest \
      --set-env-vars \
        DISCORD_TOKEN="$(DISCORD_TOKEN)" \
        KANAL_ID="$(KANAL_ID)" \
        KICK_KULLANICI_ADI="$(KICK_KULLANICI_ADI)" \
        YOUTUBE_KANAL_ID="$(YOUTUBE_KANAL_ID)" \
        YOUTUBE_DUYURU_KANAL_ID="$(YOUTUBE_DUYURU_KANAL_ID)" \
        CHROMEDRIVER_PATH="/usr/bin/chromedriver"
  displayName: Azure Container Apps'e deploy et
```

---

## 7. Pipeline'ı Azure DevOps'a Bağlama

1. Azure DevOps → Pipelines → New pipeline
2. GitHub reposunu seç
3. Repo içindeki `azure-pipelines.yml` dosyasını seç
4. "Run" ile test et

Pipeline ilk çalıştırmada:
- repo okunur
- Azure login yapılır
- image build edilir
- ACR'e push edilir
- Container App güncellenir

---

## 8. GitHub Actions ile Azure Pipelines Arasındaki Fark

| Alan | GitHub Actions | Azure Pipelines |
|------|----------------|----------------|
| Platform | GitHub | Azure DevOps |
| Secret yönetimi | GitHub Secrets | Variable Group / Library |
| Azure auth | `azure/login` | Service Connection |
| YAML | `.github/workflows/*.yml` | `azure-pipelines.yml` |

---

## 9. Mevcut GitHub Actions Dosyasını Kaldırma

Eğer artık GitHub Actions yerine Azure Pipelines kullanacaksan:

- `.github/workflows/deploy-azure.yml` dosyasını koruyabilir ya da silebilirsin
- GitHub Actions'ta çalışan deploy'i kapatmak için workflow dosyasını kaldırman gerekir
- Azure DevOps'ta pipeline aktif olduğunda, GitHub tarafında ayrı bir workflow çalışmaz

---

## 10. Sık Karşılaşılan Sorunlar

### 1) Azure login hatası alıyorum

Bunun nedeni genellikle service connection hatasıdır.

Çözüm:
- Service connection'ın doğru abonelikte olduğunu kontrol et
- Pipeline içinde `azureSubscription` adını doğru yaz

### 2) ACR'ye push yapamıyorum

Çözüm:
- ACR kullanıcı adı ve şifresi doğru mu kontrol et
- ACR login server doğru mu yaz

### 3) Container App güncellenmiyor

Çözüm:
- `az extension add --name containerapp --upgrade --yes` adımının çalıştığını kontrol et
- Container App adının ve resource group adının doğru olduğunu doğrula

### 4) Ortam değişkenleri gelmiyor

Çözüm:
- Variable Group içindeki değerlerin `secret` olarak işaretlendiğinden emin ol
- `--set-env-vars` kısmında değişken adlarını kontrol et

---

## 11. En Kolay Geçiş Stratejisi

Eğer hızlı geçiş istiyorsan şu sırayı uygula:

1. Azure DevOps projesi oluştur
2. Azure service connection kur
3. Variable Group oluştur
4. `azure-pipelines.yml` ekle
5. Pipeline'ı çalıştır
6. Başarılı olursa GitHub Actions workflow dosyasını kaldır

---

## 12. Özet

Azure Pipelines'e geçmek için temel mantık şudur:

- GitHub Actions yerine Azure DevOps pipeline kullan
- Azure kimlik doğrulaması için service connection kur
- Gizli değerleri variable group ile yönet
- Docker build/push ve Container Apps güncelleme adımlarını YAML içinde tanımla

İstersen bir sonraki adımda bu repo için hazır bir tam `azure-pipelines.yml` dosyasını doğrudan projeye ekleyebilirim.
