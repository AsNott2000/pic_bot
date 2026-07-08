import sys
import io
import os
from dotenv import load_dotenv

load_dotenv()  # .env dosyasını yükle

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import discord
from discord.ext import tasks, commands
import asyncio
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

# Azure Container Apps'te Dockerfile ile kurulan sabit ChromeDriver kullanılır.
# Local geliştirme için CHROMEDRIVER_PATH env değişkeni tanımlanabilir.
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")


# Discord Botunun Ayarları
INTENTS = discord.Intents.default()
INTENTS.message_content = True
bot = commands.Bot(command_prefix="!", intents=INTENTS)


# --- .env dosyasından okunur ---
TOKEN = os.getenv("DISCORD_TOKEN")
KANAL_ID = int(os.getenv("KANAL_ID"))
KICK_KULLANICI_ADI = os.getenv("KICK_KULLANICI_ADI")
# --------------------------------

# XPath: Offline iken gozuken h2 elementi
# Yayindayken bu element sayfada OLMAZ → element yokluğu = yayinda demek
STATUS_XPATH = "/html/body/div[2]/div[2]/div[4]/main/div[1]/div[4]/h2"

# Yayın durumunu hafızada tutan değişken
yayin_durumu = "offline"


# --- SELENIUM İLE KICK DURUM KONTROL FONKSİYONU ---
def kick_durumunu_al(kullanici_adi: str) -> str:
    """
    Kick sayfasını Selenium ile açar.
    
    - Offline iken: h2 elementi bulunur, "cevrim disi" içerir → "OFFLINE" döner
    - Yayında iken: h2 elementi YOKTUR (sayfa tamamen değişir) → "CANLI" döner
    - Hata durumunda: boş string döner
    """
    url = f"https://kick.com/{kullanici_adi}"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = None
    try:
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(20)
        driver.get(url)

        # JS render için bekle
        time.sleep(5)

        try:
            # Offline elementi bulmaya çalış
            element = driver.find_element(By.XPATH, STATUS_XPATH)
            metin = element.text.strip()
            print(f"[Kick] Offline mesaji bulundu: '{metin}'")
            driver.quit()
            return "OFFLINE"

        except NoSuchElementException:
            # Element yok = sayfa canli yayin layoutuna gecti = YAYINDA!
            print("[Kick] Offline mesaji yok → Yayinda!")
            driver.quit()
            return "CANLI"

    except Exception as e:
        print(f"[Selenium Hata] {e}")
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return ""


# --- BOT HAZIR OLDUĞUNDA ---
@bot.event
async def on_ready():
    print(f"[BOT] {bot.user.name} basariyla aktif oldu!")
    kick_kontrol_dongusu.start()


# --- 5 DAKİKADA BİR ÇALIŞAN DÖNGÜ ---
@tasks.loop(minutes=5)
async def kick_kontrol_dongusu():
    global yayin_durumu

    print(f"[Kontrol] Su anki durum: {yayin_durumu}")

    kanal = bot.get_channel(KANAL_ID)
    if not kanal:
        print("Hata: Kanal bulunamadi!")
        return

    # Selenium blokluyor, executor ile async yapıyoruz
    loop = asyncio.get_event_loop()
    durum_metni = await loop.run_in_executor(None, kick_durumunu_al, KICK_KULLANICI_ADI)

    if not durum_metni:
        print("[Kontrol] Durum alinamadi, atlanıyor.")
        return

    # kick_durumunu_al "CANLI" veya "OFFLINE" doner
    su_an_canli = (durum_metni == "CANLI")
    print(f"[Kontrol] Sonuc: {'YAYINDA' if su_an_canli else 'OFFLINE'} | Onceki: {yayin_durumu}")

    if su_an_canli and yayin_durumu == "offline":
        yayin_durumu = "live"
        await kanal.send(
            f"@everyone\n"
            f"**{KICK_KULLANICI_ADI}** su anda Kick'te **CANLI YAYINDA**!\n"
            f"https://kick.com/{KICK_KULLANICI_ADI}"
        )
        print(f"[{KICK_KULLANICI_ADI}] Yayina girdi! Discord bildirimi gonderildi.")

    elif not su_an_canli and yayin_durumu == "live":
        yayin_durumu = "offline"
        print(f"[{KICK_KULLANICI_ADI}] Yayin kapandi.")

    else:
        print(f"[{KICK_KULLANICI_ADI}] Durum degismedi: {yayin_durumu}")


# Botu başlat
bot.run(TOKEN)