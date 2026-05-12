# ZAI Shell
### Otonom P2P Sistem Yönetimi

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-AGPL%20v3.0-green?style=for-the-badge)
![Sentinel](https://img.shields.io/badge/Sentinel-ACTIVE-red?style=for-the-badge)

[![🇺🇸 English](https://img.shields.io/badge/🇺🇸_ENGLISH_DOCUMENTATION-0056D2?style=for-the-badge&logoColor=white)](README.md)

**Manuel sistem yönetimi öldü.**

ZAI Shell sadece başka bir CLI arayüzü değildir. Karmaşık ortamlarda gezinmek, onarmak ve güvenliği sağlamak için tasarlanmış **otonom bir SysOps ajanıdır**. Doğal dil niyetini doğrulanmış sistem eylemlerine dönüştürür, **Sentinel** ile sizi felaketlerden korur ve **P2P Şifreli Ağ** aracılığıyla güvenli iş birliğini sağlar.

---

## ⚡ Hızlı Kurulum (2 Dakika)
```bash
# 1. Bağımlılıkları Yükle
pip install google-generativeai colorama psutil posthog pyautogui keyboard

# 2. Ücretsiz Gemini API Anahtarını Ayarla
# Windows (PowerShell) için:
$env:GEMINI_API_KEY="anahtariniz_buraya"
# Linux/macOS (Bash) için:
export GEMINI_API_KEY="anahtariniz_buraya"

# 3. Çalıştır
git clone https://github.com/TaklaXBR/zai-shell.git
cd zai-shell
python zaishell.py
```
*İsteğe bağlı: `pip install cryptography` (P2P Şifreleme), `chromadb` (Uzun Süreli Bellek)*

---

## ✨ v9.1.0'da Neler Yeni?
- ⏱️ **Watch Sistemi (`--watch`)**: Arka planda kalıcı sistem izleyicileri oluşturun (örn: `--watch ram yüzde 80'i geçerse`). ZAI hafif betikler çalıştırır ve koşul sağlandığında sizi uyarır.
- 🛠️ **Fixer Modu**: Sadece sistem onarımı ve sorun gidermeye odaklanan yepyeni bir mod. Günlük sohbetleri görmezden gelir ve saf bir sistem doktoru gibi davranır.
- 👁️ **Görsel Bağlam (Ctrl+Shift+Z)**: Tek tuşla ekranınızın anlık görüntüsünü alın ve sorunun bağlamını anlaması için doğrudan ZAI'nin görüntü modeline gönderin.
- 🛡️ **Gelişmiş `--show` Modu**: ZAI artık bir komutu çalıştırmadan önce komutun sistemde tam olarak ne yapacağını detaylıca açıklıyor.

---

## Temel Sütunlar

### 🧠 Hibrit Zeka
- **Çok Modlu (Multi-Modal)**: Hata teşhisi için ekran içeriğini (GUI) ve görüntüleri analiz eder.
- **Kendi Kendini Onarma**: Bir komut başarısız olursa, ZAI görev tamamlanana kadar stratejiyi otomatik olarak değiştirir.
- **P2P Ağı**: Uçtan uca şifreleme ile dünya çapında terminaller üzerinde iş birliği yapın.

### 🛡️ Sentinel 1.5: Davranışsal Risk Zekası
Sentinel bağlamı anlayan ve hatalardan ders çıkaran bir kendini koruma sistemidir.
- Eylemleri Yapısal, Davranışsal, Bağlamsal ve Niyet risklerine ayırır.
- Gerçek hasara neden olan geçmiş başarısızlıkların hafif bir belleğini tutar.
- Engelleyici değildir: Uyarır ve açıklar, ancak son karar her zaman sizindir.

### 🔥 Savaşta Test Edildi: "Kıyamet" (Doomsday) Protokolü
> **"Bir yapay zekanın kod yazması yetmez. Sonuçlarına karşı hayatta kalabilmelidir."**

ZAI'yi düşman bir simülatöre (KERNEL_PANIC, SİLİNMİŞ_DOSYALAR, İZİN_KAOSU) maruz bıraktık.
- **Sonuç**: **%65.5 Hayatta Kalma Oranı** (87 senaryodan 57'si otonom olarak çözüldü).
- **Ana Zafer**: Eksik bir `libssl.so.3` kütüphanesini `sudo` olmadan bir `.deb` paketini manuel olarak çıkartarak geri yükledi.
- **[📄 Tam Stres Testi Sonuçlarını Oku](BENCHMARK/ZAI_DOOMSDAY_PROTOCOL_TR.md)**

---

## Komut Referansı

| Kategori | Komut | Açıklama |
| :--- | :--- | :--- |
| **Sentinel** | `sentinel status` / `on/off` | Risk metriklerini ve sağlık puanını görüntüle. |
| **P2P Paylaşım** | `share start` / `connect <IP>` | Güvenli terminal oturumu başlat veya katıl. |
| **Watch (YENİ)**| `--watch <koşul>` | Arka planda sistem izleyici oluştur. |
| | `watch list` / `stop <ID>` | Aktif izleyicileri gör veya durdur. |
| | `fix watch` | Tetiklenen uyarıyı otomatik onarım için Fixer moduna yolla. |
| **Çekirdek** | `switch <mod>` | `online` (Gemini API) veya `offline` (Phi-2 Yerel). |
| | `gui on/off` | Masaüstü otomasyon araçlarını etkinleştir. |
| | `research on/off` | Canlı web arama yeteneğini etkinleştir. |
| **Modlar** | `normal` / `eco` / `lightning` | Dengeli / Token verimli / Maksimum hız. |
| | `fixer` **(YENİ)** | Sadece sistem onarımı ve sorun giderme odaklı mod. |

---

## 🔐 Gizlilik & Telemetri
ZAI Shell, sistemi geliştirmek için **anonim** kullanım verilerini (başarı oranları, hata sayıları) toplar. **Kodunuzu, dosya içeriklerinizi, komut metinlerinizi veya kişisel verilerinizi ASLA toplamayız.**
Devre dışı bırakmak için: `telemetry off`

**❤️ ile yapıldı @TaklaXBR | Türkiye 🇹🇷**
