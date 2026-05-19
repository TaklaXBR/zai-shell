# ZAI Shell v9.2.0
### Otonom P2P Sistem Yönetimi Ajanı

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-AGPL%20v3.0-green?style=for-the-badge)
![Sentinel](https://img.shields.io/badge/Sentinel-AKTİF-red?style=for-the-badge)

[![🇬🇧 English](https://img.shields.io/badge/🇬🇧_ENGLISH_DOCUMENTATION-blue?style=for-the-badge&logoColor=white)](README.md)

**Manuel sistem yönetimi devri kapandı.**

ZAI Shell, karmaşık ortamları yönlendirmek, onarmak ve güvence altına almak için tasarlanmış **otonom bir SysOps ajanıdır**. Doğal dildeki niyetinizi doğrulanmış sistem eylemlerine dönüştürür, sizi **Sentinel 1.5** ile korur ve **P2P Şifreli Ağ** üzerinden güvenli işbirliği sağlar.

---

## 🚀 Neden ZAI Shell? (Temel Özellikler)

### 🤖 1. `--auto` ile Tam Otonomi
ZAI'ye sadece bir komut değil, bir **görev** verin. Komutunuzun sonuna `--auto` eklediğinizde ZAI Shell tamamen otonom bir ajana dönüşür. Adımları uygular, terminal çıktılarını okur, neyin yanlış gittiğini fark eder, kendi hatalarını düzeltir ve görev **%100 tamamlanana kadar** döngüde kalır.

### ⏱️ 2. Uyarlanabilir Çalışma Modları
Görevleriniz farklı tempolar gerektirir. İşinize göre modunuzu anında değiştirin:
- 🛠️ **`fixer`**: Sistemdeki şeyleri silip yüklemekten yoruldunuz mu? Fixer modu sadece sistem onarımı ve sorun gidermeye odaklanır. Vakit kazanmanız için bir sistem doktoru gibi davranır.
- ⚡ **`lightning`**: Diğer ajanlardan daha hızlı işlem yapmak mı istiyorsunuz? Lightning modu, hızlıca komut yürütmek için düşünce sürecini optimize eder.
- 🍃 **`eco`**: Kotanızın hata vermesinden kurtulmak ve performansı koruyabilmek için Eco modunu kullanın. Temel işlevlerden ödün vermeden token limitlerinizi korur.
- ⚖️ **`normal`**: Mantık yürütme ve eylemin mükemmel dengesi.

### 🛡️ 3. Güvenli Yürütme: Undo & Sentinel 1.5
- ⏪ **Tek Tıkla Geri Alma (`undo`)**: Yapay zekaya dosyayı emanet ettiniz ama her şeyi bozdu mu? Hiç dert değil! ZAI, düzenlediği her dosyayı otomatik olarak yedekler. Sadece `undo` yazarak anında eski haline getirin.
- 🛑 **Sentinel Risk Zekası**: Arka planda sürekli çalışan koruyucu meleğiniz. Sistemi bozacak bir kod yazıldığında uyarır. Hatta okunan dosyalarda gizli **Prompt Injection** saldırıları varsa anında bloklar! `sentinel report` ile günün özetini alabilirsiniz.

### 👁️ 4. Çoklu Bağlam & Görme Yeteneği
- **Konuşma Zinciri Hafızası**: ZAI balık hafızalı değildir. Son 5 işlemin tam girdi/çıktılarını hatırlar. Saniyeler önce ne yaptığını bilerek mantıklı adımlar atar.
- **Ekranı Görebilen Ajan (Ctrl+Shift+Z)**: Bir hata mı aldınız? Kodu kopyalamanıza gerek yok! Tek tuşla ekranınızın fotoğrafını çekin, ZAI anında sorunun nerede olduğunu bulsun.

### 🕒 5. Uyumayan Gözlemci (`--watch` + `--force`)
Yapay zekaya bir nöbet görevi verin: `--watch CPU kullanımı %90'ın üzerindeyse`. ZAI arka planda bekler, durum gerçekleştiğinde uyarır.
🔥 **Daha da delisi:** Eğer bunu `--watch ... --force` şeklinde yazarsanız, ZAI sizi uyarmakla kalmaz, arka planda anında **Fixer moduna geçer ve sorunu kendi kendine çözer!** Siz kahvenizi içerken sistem kendini iyileştirir.

### 🌐 6. E2E Şifreli P2P Terminal Paylaşımı
Arkadaşınızın bilgisayarında bir sorun mu var? AnyDesk veya TeamViewer kurmanıza gerek yok!
ZAI'nin P2P ağı üzerinden `share start` deyin, arkadaşınız `share connect IP` yazsın. Tüm terminal bağlantısı **uçtan uca şifreli** şekilde birbirine bağlanır. Uzaktaki bilgisayarı kendi terminalinizden, yapay zeka destekli ajanınızla birlikte onarın!

### 🕵️‍♂️ 7. Tam Gizlilik İsteyenlere: Yerel Mod (Microsoft Phi-2)
Kodlarınızın, hata mesajlarınızın veya terminalinizin tek bir baytının bile buluta gitmesini istemiyor musunuz? Hiç sorun değil!
`switch offline` komutunu girin ve **Microsoft Phi-2** modelini tamamen bilgisayarınıza indirip **internetsiz, %100 gizlilikle** çalışın.
⚠️ **Ama dikkatli olun!** *"Küçük model, büyük sıkıntı"* getirebilir. Gemini kadar zeki değildir, sisteminize zarar vermemesi için gözünüzü üzerinden ayırmayın!

---

## ⚡ Hızlı Kurulum (2 Dakika)
```bash
# 1. Bağımlılıkları Yükleyin
pip install google-generativeai colorama psutil posthog pyautogui keyboard requests beautifulsoup4

# 2. Ücretsiz Gemini API Anahtarını Ayarlayın
# Windows için (PowerShell):
$env:GEMINI_API_KEY="anahtarınız_buraya"
# Linux/macOS için (Bash):
export GEMINI_API_KEY="anahtarınız_buraya"

# 3. Çalıştırın
git clone https://github.com/TaklaXBR/zai-shell.git
cd zai-shell
python zaishell.py
```
*Opsiyonel: `pip install cryptography` (P2P Şifreleme), `chromadb` (Uzun Vadeli Hafıza)*

---

## 🕹️ Komut Referansı

| Kategori | Komut | Açıklama |
| :--- | :--- | :--- |
| **Otonomi** | `[isteğiniz] --auto` | Görev tamamlanana kadar tam otonom döngü. |
| **Güvenlik** | `undo` | ZAI tarafından yapılan son dosya değişikliğini geri alır. |
| | `--safe` / `--show` | Her eylemden önce onay iste / Önizleme modu. |
| **Sentinel** | `sentinel status` / `on/off` | Risk metriklerini ve sağlık puanını görüntüleyin. |
| | `sentinel report` | Detaylı bir markdown güvenlik raporu oluşturun. |
| **Watch** | `--watch <koşul>` | Arka plan sistem monitörü oluşturun. |
| | `watch list` / `stop <ID>` | Aktif monitörleri görün veya durdurun. |
| **Modlar** | `normal` / `eco` / `lightning` / `fixer` | YZ davranışını dinamik olarak değiştirin. |
| **P2P Paylaşım** | `share start` / `connect <IP>` | Güvenli şifreli terminal oturumu kurun veya katılın. |

---

## 🔥 Savaş Testinden Geçti: "Kıyamet Günü" Protokolü
> **"Bir yapay zekanın kod yazması yeterli değildir. Sonuçlarından sağ çıkabilmelidir."**

ZAI'yi düşmanca bir simülatöre maruz bıraktık (ÇEKİRDEK_PANİĞİ, SİLİNEN_İKİLİLER, İZİN_KAOSU).
- **Sonuç**: **%65.5 Hayatta Kalma Oranı** (87 senaryodan 57'si otonom olarak çözüldü).
- **[📄 Tam Stres Testi Sonuçlarını Oku](BENCHMARK/ZAI_DOOMSDAY_PROTOCOL_TR.md)**

---

## 🐛 Hata Bildirimi ve Katkı
Projeyi denerken bir sorun mu yaşadınız veya harika bir fikriniz mi var? Lütfen GitHub üzerinden **Issue** (Hata/Talep) açmaktan çekinmeyin! Geri bildirimleriniz ZaiShell'i daha da akıllı yapmamız için çok değerli.

---

## 🔐 Gizlilik ve Telemetri
ZAI Shell sistemi geliştirmek için **anonim** kullanım verileri (başarı oranları, hata sayıları) toplar. **Kodlarınızı, dosya içeriklerinizi, komut metinlerinizi veya kişisel verilerinizi ASLA toplamıyoruz.**
Telemetriyi devre dışı bırakmak için: `telemetry off`

**@TaklaXBR tarafından ❤️ ile Türkiye'de yapıldı 🇹🇷**
