# ZaiShell

**Otonom Sistem Yönetimi, DevOps ve Terminal Mühendislik Ajanı**

[![English Documentation](https://img.shields.io/badge/English_Documentation-README.md-blue?style=for-the-badge)](README.md)

ZaiShell; sistem yönetimi, yazılım geliştirme ve DevOps iş akışları için tasarlanmış, Google Gemini tabanlı otonom bir komut satırı ajanıdır. Çok adımlı terminal operasyonlarını yürütür, kalıcı kabuk oturumlarını yönetir, hassas dosya düzenlemeleri yapar ve arka plan servislerini denetler.

---

## Temel Özellikler

* **Kalıcı Kabuk Oturumları:** Sistemdeki bash, zsh, powershell, pwsh, cmd, wsl ve git-bash gibi kabukları otomatik tespit eder. Çalışma dizini değişikliklerini, ortam değişkenlerini ve aktif sanal ortamları adımlar arasında korur.
* **Gelişmiş Dosya Düzenleme:** Dosyaların karakter kodlamasını ve satır sonu yapısını otomatik algılayarak korur. Belirli satır aralıklarını okuma, satır ekleme, satır silme, satır değiştirme, Regex ile arama-değiştirme, boşluk farklarını tolere eden blok eşleştirme ve Base64 ikili dosya yazma işlemlerini destekler.
* **Sanal Çıktı Tamponu:** Uzun komut çıktılarını kesip kaybetmek yerine bellekte saklar. Ajan komutu tekrar çalıştırmaya gerek duymadan bu çıktılar içinde Regex araması yapabilir veya belirli satır aralıklarını okuyabilir.
* **Arka Plan Görev Yönetimi ve Otomatik Onarım:** Uzun süreli servisleri arka planda başlatır, logları gerçek zamanlı izler, çalışan görevlere girdi gönderir, belirlenen hata desenlerinde uyarı üretir ve beklenmedik şekilde çöken servisleri otomatik olarak onarır.
* **Etkileşimli Süreç Kontrolü:** Çalışma sırasında onay veya parola bekleyen komut satırı araçlarının ara çıktılarını kontrol eder ve çalışan sürece canlı girdi göndererek işlemi tamamlar.
* **İş Akışı Kontrolü ve Veri Aktarımı:** Bir adımın çıktısını diğer adıma doğrudan aktarma, önceki çıktılara göre koşullu çalıştırma, hata dallanması, yerel yedek komutlar, durum yoklama ile sıralı veya paralel çalıştırma özelliklerini destekler.
* **Dayanıklı İletişim ve Güvenlik:** Geçici ağ hatalarına karşı otomatik yeniden deneme, bozuk JSON çıktılarını otomatik onarma, zaman aşımında tüm alt süreç ağacını temizleme ve yıkıcı sistem komutlarını engelleyen güvenlik kuralları içerir.

---

## Proje Yapısı

* `zaishell.py` — Ana ajan döngüsü, iş akışı yönetimi, JSON onarım ayrıştırıcısı ve etkileşimli süreç kontrolcüsü.
* `terminal_discovery.py` — Dinamik kabuk tespiti ve kalıcı oturum havuzu.
* `background_manager.py` — Arka plan servis yöneticisi ve bellek içi sanal çıktı tamponu.
* `file_surgery.py` — Karakter kodlaması duyarlı dosya okuma, yazma ve satır düzeyinde düzenleme modülü.
* `security_rules.py` — Yıkıcı sistem komutlarını engelleyen güvenlik kuralları.
* `prompts.py` — Sistem yönergeleri ve JSON hata düzeltme şablonları.

---

## Kurulum ve Kullanım

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/TaklaXBR/zai-shell.git
cd zaishell
```

### 2. Gerekli Paketleri Yükleyin
```bash
pip install google-genai rich
```

### 3. API Anahtarını Tanımlayın

**Linux ve macOS:**
```bash
export GEMINI_API_KEY="api_anahtariniz"
```

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="api_anahtariniz"
```

**Windows CMD:**
```cmd
set GEMINI_API_KEY=api_anahtariniz
```

Varsayılan `gemini-3.5-flash-lite` dışında bir model kullanmak isterseniz `ZAISHELL_MODEL` ortam değişkenini tanımlayabilirsiniz:
```bash
export ZAISHELL_MODEL="gemini-3.8-flash"
```

### 4. Çalıştırın
```bash
python zaishell.py
```

---

## Onay Kontrolleri

ZaiShell, adımları çalıştırmadan önce kullanıcıdan onay ister:
* `y` — İşlemleri onayla ve çalıştır.
* `n` — Mevcut görevi iptal et.
* `skip` — Bu yöntemi atla ve ajandan alternatif bir çözüm üretmesini iste.
* `q` veya `quit` — Açık oturumları kapat ve programdan çık.