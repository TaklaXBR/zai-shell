# ZAI Shell v9.0
### Otonom P2P Sistem Yöneticisi

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-AGPL%20v3.0-green?style=for-the-badge)
![Sentinel](https://img.shields.io/badge/Sentinel-ACTIVE-red?style=for-the-badge)
[![Whitepaper](https://img.shields.io/badge/📄_WHITEPAPER-READ_IEEE_FORMAT-0056D2?style=for-the-badge&logoColor=white)](docs/whitepaper.pdf)

[![🇺🇸 English](https://img.shields.io/badge/🇺🇸_ENGLISH_DOCUMENTATION-0056D2?style=for-the-badge&logoColor=white)](README.md)

**Manuel sistem yönetimi öldü.**

ZAI Shell, sadece başka bir CLI arayüzü değildir. Karmaşık ortamlarda gezinmek, onarmak ve güvenliği sağlamak için tasarlanmış bir **otonom SysOps ajanıdır**. Doğal dil niyetlerini doğrulanmış sistem eylemlerine dönüştürür, **Sentinel** ile sizi felaketlerden korur ve **P2P Şifreli Ağ** aracılığıyla güvenli, küresel iş birliğini mümkün kılar.

> **"ZAI kontrol etmek için değil, hayatta kalmak için konuşur."** — Sentinel Felsefesi

---

## ⚡ Hızlı Kurulum (2 Dakika)
```bash
# 1. Bağımlılıkları Yükle
pip install google-generativeai colorama psutil posthog

# 2. Ücretsiz Gemini API Anahtarını Ayarla (PowerShell)
$env:GEMINI_API_KEY="anahtariniz_buraya"

# 3. Çalıştır
git clone https://github.com/TaklaXBR/zai-shell.git
cd zai-shell
python zaishell.py
```
*İsteğe bağlı: `pip install cryptography` (P2P Şifreleme), `chromadb` (Uzun Süreli Bellek)*

---

## 🎯 Neden ZAI Shell?

**Geleneksel Yapay Zeka:**
`Sen: "Dosya oluştur..."` → `AI: [Hata Verdi]` → `Sen: Manuel hata ayıklama 😤`

**ZAI Shell:**
`Sen: "Dosya oluştur..."` → `AI: [Hata Verdi]` → `🔧 Otomatik Onarım...` → `✅ Başarılı! (Sıfır manuel işlem)`

---

## Temel Sütunlar

### 🛡️ Sentinel: Güvenlik Katmanı
Güvenlik sonradan düşünülecek bir şey olamaz. v9.0'da, **Sentinel** bağımsız bir gözlemci olarak hareket eder—bir "Yargıç"tan ziyade bir "Tanık"tır.
- **Niyet Analizi**: Sentinel sadece *hangi* komutu çalıştırdığınızı değil, *neden* çalıştırdığınızı da anlar.
- **Risk Değerlendirmesi**: Her eylem, sistem etkisi, geri alınabilirlik ve bağlama göre puanlanır (0-100).
- **Engelleyici Olmayan Uyarılar**: Sentinel sizi tehlikelere karşı uyarır ancak insan otoritesine saygı duyar. **Sadece risk algılandığında açık onay gerektirir.**
- **Kendini Koruma**: Onarım döngülerini, yetki yükseltmelerini ve geri dönüşü olmayan sistem değişikliklerini otomatik olarak algılar ve uyarır.

### 🔒 P2P Ağı: Güvenli İş Birliği
Terminaller üzerinde bir Google Doc kadar kolay, ancak güvenli uçtan uca şifreleme ile iş birliği yapın.
- **Uçtan Uca Şifreleme**: PBKDF2HMAC'den türetilmiş Fernet simetrik şifreleme (AES-128).
- **Sıfır Güven (Zero-Trust)**: Ana sunucu anahtarlarınızı asla görmez; sırrı sadece siz ve eşiniz (peer) bilir.
- **Doğal Dil Köprüsü**: Bir Yardımcı "Disk alanını kontrol et" der ve Ana Bilgisayarın yapay zekası bunu çevirip `Get-PSDrive` komutunu çalıştırır.
- **Küresel Erişim**: Bulut bağımlılığı olmadan dünya çapında erişim için `ngrok` gibi tünellerle sorunsuz çalışacak şekilde tasarlanmıştır.

**Güvenli İş Birliği (Log):**
`Yardımcı: "zai disk alanını kontrol et"`
`Ana Bilgisayar: [Niyeti Onaylar]` → `Çalıştırılıyor: Get-PSDrive C`
`Yardımcı: "C sürücüsünde 245GB boş alan var"`

### 🧠 Hibrit Zeka
Terminal artık sadece metinden ibaret değil.
- **Çok Modlu (Multi-Modal)**: Hata teşhisi için ekran içeriğini (GUI) ve görüntüleri analiz eder.
- **Araştırma Yeteneği**: Dokümantasyon bulmak ve genel hataları düzeltmek için canlı web'de gezinebilir.
- **Kendi Kendini Onarma**: Bir komut başarısız olursa, ZAI görev tamamlanana kadar stratejiyi otomatik olarak değiştirir (örn. CMD'den PowerShell'e geçer).

![ZAI Shell Auto-Retry Demo](assets/autoretry.gif)

**Gerçek Log:**
`[1/5] [CMD] İşletim sistemi bilgisini al` → `❌ Hata`
`🔧 PowerShell'e geçiliyor...`
`[2/5] [PowerShell] İşletim sistemi bilgisini al` → `✅ Başarılı!`

---

## ⚡ Performans: ZAI vs. Dünya

| Özellik | ZAI Shell v9.0 | ShellGPT | Open Interpreter | GitHub Copilot CLI | AutoGPT |
|---------|----------------|----------|------------------|-------------------|---------|
| **Sentinel (Güvenlik)** | ✅ Niyet Tabanlı Risk Analizi | ❌ Yok | ⚠️ Basit Onay | ❌ Yok | ⚠️ Tehlikeli Döngüler |
| **Kendi Kendini Onarma** | ✅ 5-Stratejili | ❌ Manuel | ❌ Manuel | ❌ Manuel | ⚠️ Sonsuz Döngüler |
| **P2P Şifreleme** | ✅ Uçtan Uca Şifreli Ağ | ❌ Yok | ❌ Yok | ❌ Yok | ❌ Yok |
| **Çevrimdışı AI** | ✅ Dahili Yerel Model | ✅ Yerel Modeller | ✅ Yerel Modeller | ❌ Sadece Bulut | ❌ Sadece API |
| **Web Araştırma** | ✅ Canlı Sentez | ⚠️ Özel Fonk. | ✅ Tam Erişim | ❌ Yok | ✅ Dahili |
| **Kalıcı Bellek** | ✅ Vektör + JSON | ⚠️ Sadece Sohbet | ✅ Geçmiş | ⚠️ Sınırlı | ✅ Uzun Süreli |
| **Düşünme Modu** | ✅ Görünür Akıl Yürütme | ❌ Kara Kutu | ❌ Kara Kutu | ❌ Kara Kutu | ⚠️ Çok Sözlü |
| **Kabuk Esnekliği** | ✅ 13+ Kabuk Desteği | ✅ Çoklu Kabuk | ✅ Çoklu Kabuk | ⚠️ Sadece Belirli | ⚠️ Python Yerel |
| **Maliyet** | ✅ Ücretsiz Katman + Çevrimdışı | ✅ Ücretsiz (Yerel) | ✅ Ücretsiz (Yerel) | ❌ Ücretli Abonelik | ⚠️ Yüksek API Ücretleri |
| **GUI Otomasyonu** | ✅ Hibrit (Terminal + Vizyon) | ❌ Sadece Terminal | ✅ OS Modu | ❌ Sadece Terminal | ⚠️ Sadece Tarayıcı |

### Yıldırım Modu (Lightning Mode) İş Başında
*Görev: 'pdfs' klasörü oluştur ve 48 dosyayı taşı. Süre: 3.34sn*

![Lightning Mode Performance](assets/lightningtest.gif)

### 🔥 Savaşta Test Edildi: "Kıyamet" (Doomsday) Protokolü
> **"Bir yapay zekanın kod yazması yetmez. Sonuçlarına karşı hayatta kalabilmelidir."**

ZAI'yi düşman bir simülatöre (KERNEL_PANIC, SİLİNMİŞ_DOSYALAR, İZİN_KAOSU) maruz bıraktık.
- **Sonuç**: **%65.5 Hayatta Kalma Oranı** (87 senaryodan 57'si otonom olarak çözüldü).
- **Ana Zafer**: Eksik bir `libssl.so.3` kütüphanesini `sudo` olmadan bir `.deb` paketini manuel olarak çıkartarak geri yükledi.
- **[📄 Tam Stres Testi Sonuçlarını Oku](BENCHMARK/ZAI_DOOMSDAY_PROTOCOL_TR.md)**

---

## 💬 Topluluk

> "'Kendi kendini onarma' mantığını kullanmak... gerçekten zekice. Sadece bir hata yığını (stack trace) dökmekten çok daha akıllıca." — **Hacker News Kullanıcısı**

> "Dostum kendi kendini onarma tekrar deneme mantığı harika geliyor... Bunu 15 yaşında geliştirmiş olman, oldukça etkileyici." — **Reddit Kullanıcısı (r/LocalLLaMA)**

> "Çok fazla agentvari şey denedim... özellikle offline model kullanımına bayıldım. Başarılarının devamını görmek isteriz." — **Reddit Kullanıcısı (r/TurkDev)**

---

### 🖱️ GUI & Çapraz Kabuk (Cross-Shell) Yetenekleri

**Hibrit İş Akışı:** Terminal + GUI otomasyonu ile Opera GX kurulumu
![Opera GX Installation Demo](assets/guiuse.gif)

**Çapraz Kabuk Gücü:** Tek bir istekte WSL → CMD → PowerShell → WSL kullanımı
![Cross-Shell Demo](assets/crossshell.gif)

---

## Mimari: Niyet Döngüsü

ZAI v9.0, özerklik ve güvenlik için tasarlanmış, kesinlikle doğrulanmış bir yürütme döngüsü üzerinde çalışır:

1.  **Niyet**: Kullanıcı "Python kurulumunu onar" isteğinde bulunur.
2.  **Plan**: Yapay zeka, bir yürütme planı oluşturmak için belleğe ve araçlara danışır.
3.  **Sentinel Kontrolü**: Plan, siz görmeden önce risk açısından puanlanır.
    *   *Düşük Risk*: Sessizce devam et.
    *   *Yüksek Risk*: **DUR**. Risk faktörlerini göster. Açık onay iste.
4.  **Yürütme**: Doğrulanmış komutlar çalıştırılır.
5.  **Sonuç & Onarım**:
    *   *Başarı*: Sonuç döndürülür.
    *   *Başarısızlık*: Hata yapay zekaya geri bildirilir → Yeni Plan → sentinel tekrar kontrolü → Tekrar Dene.

---

## Komut Referansı

| Kategori | Komut | Açıklama |
| :--- | :--- | :--- |
| **Sentinel** | `sentinel status` | Risk metriklerini, son uyarıları ve sağlık puanını görüntüle. |
| | `sentinel on/off` | Güvenlik katmanını aç/kapa (Önerilmez). |
| | `sentinel reset` | Davranışsal risk geçmişini temizle. |
| **P2P Paylaşım** | `share start` | Oturum başlat (IP/Port otomatik üretilir). |
| | `share connect <IP>` | Yardımcı olarak bir oturuma katıl. |
| | `share encrypt <sifre>` | Şifre ile E2E (Uçtan Uca) şifrelemeyi etkinleştir. |
| | `share file <yol>` | Dosyaları eşlere (peers) güvenli bir şekilde aktar. |
| | `share approve/reject` | Gelen yardımcı komutları için ana bilgisayar kontrolü. |
| **Çekirdek** | `switch <mod>` | `online` (Gemini API) veya `offline` (Phi-2 Yerel). |
| | `memory <komut>` | `show`, `search`, veya `clear` ile vektör belleği yönet. |
| | `gui on/off` | Masaüstü otomasyon araçlarını etkinleştir. |
| | `research on/off` | Canlı web arama yeteneğini etkinleştir. |
| | `telemetry off` | Anonim kullanım istatistiklerini devre dışı bırak. |
| **Modlar** | `normal` | Dengeli performans (Varsayılan). |
| | `eco` | Token verimli mod. |
| | `lightning` | Maksimum hız, minimum çıktı. |

---

## Kurulum

### Gereksinimler
- Python 3.8+
- Gemini API Anahtarı (Ücretsiz)

### Hızlı Başlangıç
```bash
# 1. Bağımlılıkları Yükle
pip install google-generativeai colorama psutil posthog

# 2. API Anahtarını Ayarla (PowerShell)
$env:GEMINI_API_KEY="anahtariniz_buraya"

# 3. ZAI'yi Çalıştır
python zaishell.py
```

*İsteğe bağlı: P2P şifreleme için `pip install cryptography`, uzun süreli bellek için `pip install chromadb`.*

---

## 🔐 Gizlilik & Telemetri

ZAI Shell, kararlılığı, performansı ve özellik geliştirmeyi iyileştirmek için **anonim** kullanım verilerini (ör. başarı oranları, hata sayıları) toplar.
**Kodunuzu, dosya içeriklerinizi, komut metinlerinizi veya kişisel verilerinizi ASLA toplamayız.**

Telemetri varsayılan olarak **AÇIK**tır. Devre dışı bırakmak için:
```bash
telemetry off
```
> Detaylar için tam [Gizlilik Politikamızı](PRIVACY_TR.md) okuyun.

---

## Sorumluluk Reddi

ZAI Shell v9.0, sistem düzeyinde komutlar çalıştırabilen güçlü bir araçtır. **Sentinel** riski önemli ölçüde azaltsa da, onaylanan tüm eylemlerden kullanıcı sorumludur. **Yüksek Riskli uyarıları her zaman inceleyin.**

---

**❤️ ile yapıldı @TaklaXBR | Türkiye 🇹🇷**

