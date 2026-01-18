# ZAI Shell "Kıyamet" Stres Test Protokolü
### *Otonom AI Agentlar için Otomatik Güvenilirlik ve Kendi Kendini Onarma Benchmark'ı*

> **"Bir AI'nın kod yazması yeterli değildir. Kendi ortamının sonuçlarından sağ çıkabilmelidir."**

## 1. Proje Genel Bakış

**ZAI Shell Stres Testi** (veya "Kıyamet Protokolü"), otonom AI agentların dayanıklılığını, kendi kendini onarma yeteneklerini ve güvenlik farkındalığını değerlendirmek için tasarlanmış gelişmiş, yıkıcı bir test çerçevesidir.

Bu **standart** bir birim testi değildir. Bu bir **düşman ortam simülatörüdür**.
Çerçeve, işletim sistemini aktif olarak sabote eder — derleyicileri siler, bölümleri değiştirir, zombi süreçleri oluşturur ve izinleri gizler. AI Agent, **sıfır ipucu**, **yığın izi yok** ve **yardım yok** ile bu bozuk ortama bırakılır. Temel nedeni çıkarmak ve bir düzeltme mühendislik etmek için tamamen **OODA Döngüsüne** (Gözlem, Yönelim, Karar, Eylem) güvenmek zorundadır.

---

## 2. "Kıyamet" Metodolojisi: Sıfır İpucu Protokolü

Bu testin temel felsefesi **Bilişsel Stres**'tir. Agent, sistemin *nasıl* bozulduğu hakkında tam olarak bilgilendirilmez, yalnızca belirli bir alanın (örneğin, "Ağ") başarısız olduğu bildirilir.

1.  **Kör Yürütme**: Agent genellikle `ls`, `sudo` veya `pip`'in basitçe mevcut olmadığı bir shell'de uyanır. Bir komut çalıştırmayı deneyip başarısız olana kadar hata günlükleri almaz.
2.  **Mantık Boşluğu**: **OODA Mantık** senaryolarında hata bir çökme değil, ince bir yanlış yapılandırmadır (örneğin, "Disk neden dolu?" → Agent, iç içe dizin ağacında gizli 10GB sparse dosyayı bulmalıdır).
3.  **Düşman Koşulları**: "Bozucu" script, kullanıcıyla aktif olarak savaşır (örneğin, script yürütmesini engellemek için `/tmp`'yi `noexec` olarak bağlamak veya `rm`'nin başarısız olması için dosyaları değişmez yapmak).

### Boz-Onar-Doğrula Döngüsü
*   **Bozucu**: Ayrıcalıklı, yıkıcı değişiklikler yürütür.
*   **Onarıcı (AI)**: Otonom olarak keşfetmeli, teşhis etmeli ve onarmalıdır.
*   **Doğrulayıcı**: Sistem restorasyonunu matematiksel olarak kanıtlar.

---

## 3. Gauntlet: Aşırı Zorluk Kategorileri

Paket, AI'yı **6 kaos kategorisine** maruz bırakır, her biri Agent'ın belirli bir "bilişsel kasını" test etmek için tasarlanmıştır:

### 1. Bağımlılık Cehennemi
*   **Zorluk**: ⭐⭐⭐⭐
*   **Zorluk**: Kritik sistem ikili dosyaları (`pip`, `npm`, `gcc`, `make`, `git`) zorla kaldırılır veya `/bin/false`'a işaret eden bozuk sembolik bağlarla değiştirilir.
*   **Gerekli Mantık**: Agent sadece "yeniden yükleyemez" — genellikle yeniden yüklemek *için* araçlardan yoksundur (örneğin, `apt` önbelleği bozuk). Manuel ikili yeniden yapılandırma gerçekleştirmeli veya alternatif kurulum yolları bulmalıdır (örneğin, derleyici olmadan kaynaktan derleme).

### 2. Kernel ve Servis Cerrahisi
*   **Zorluk**: ⭐⭐⭐⭐⭐
*   **Zorluk**: İşletim sistemini çalışırken bozmak. Temel kernel modüllerini kaldırma, önyükleme hatalarına neden olmak için `fstab`'ı değiştirme, sistem günlüklerini durdurma ve zaman senkronizasyonunu bozma (`chrony`/`systemd-timesyncd`).
*   **Gerekli Mantık**: Yüksek riskli işlemler. AI, oturumu çökertmeden kernel modüllerini yeniden yüklemek veya dosya sistemi tablolarını düzenlemek için Linux iç yapısını anlamalıdır.

### 3. Dosya Sistemi Yıkımı
*   **Zorluk**: ⭐⭐⭐⭐
*   **Zorluk**: Inode tükenmesi (100.000 küçük dosya oluşturma), döngüsel sembolik bağ tuzakları, değişmez dosya nitelikleri (`chattr +i`) ve "Rus Bebeği" dizin iç içe geçirmesi.
*   **Gerekli Mantık**: Agent, `df -h` alan olduğunu gösterirken "Disk Dolu" hatalarının neden oluştuğunu (inode'lar) veya root'a ait bir dosyada `rm`'nin neden başarısız olduğunu (değişmez bit) teşhis etmelidir.

### 4. OODA Döngü Mantığı
*   **Zorluk**: ⭐⭐⭐⭐⭐
*   **Zorluk**: Saf mantık bulmacaları.
    *   *Örnek*: "Sunucu yavaş." (Neden: Meşru olanların arasında gizlenmiş sahte arka plan süreci).
    *   *Örnek*: "Günlükler dönmüyor." (Neden: İnce bir yapılandırma sözdizimi hatası).
*   **Gerekli Mantık**: Hata mesajı yok. Agent sistem durumunu **Gözlemlemeli**, süreç ağacı içinde kendini **Yönlendirmeli**, bir hipotez üzerine **Karar Vermeli** ve doğrulamak için **Eylem** yapmalıdır.

### 5. Kırmızı Takım / Güvenlik
*   **Zorluk**: ⭐⭐⭐⭐⭐
*   **Zorluk**: Sistem savunmasız hale getirilir. Dünya tarafından yazılabilir shadow dosyaları, `/tmp`'de SUID bash ikili dosyaları ve payload indiren kötü amaçlı cron işleri.
*   **Gerekli Mantık**: Agent bir Güvenlik Mühendisi olarak hareket etmeli, ayrıcalık yükseltme vektörlerini tespit etmeli ve bunları hemen yamalamaldır.

### 6. Kaos Mühendisliği
*   **Zorluk**: ⭐⭐⭐⭐⭐
*   **Zorluk**: Yukarıdakilerin öngörülemeyen kombinasyonları.
*   **Gerekli Mantık**: Dayanıklılık ve adaptasyon.

---

## 4. Performans Raporu
**Oturum ID:** `20260117_091537`
**Süre:** 2 Saat 33 Dakika

AI Agent, sınırlarına kadar zorlandı, **165 geçerli kendi kendini onarma döngüsü** gerçekleştirdi — yani insan müdahalesi olmadan 165 kez başarısız oldu, kendi başarısızlığını analiz etti ve stratejisini düzeltti.

### Başarı Metrikleri

| Kategori | Başarı Oranı | Analiz |
| :--- | :--- | :--- |
| **Bağımlılık Cehennemi** | **%85.7** | Baskın performans. Agent, ikili altyapıyı geri yüklemede üstün. |
| **Kaos Mühendisliği** | **%82.3** | Karmaşık, karışık ortamlarda şaşırtıcı derecede yüksek dayanıklılık. |
| **Kernel Cerrahisi** | **%61.1** | Orta düzey başarı. `sudo`'nun kendisi kütüphane silmeleriyle tehlikeye girdiğinde zorlandı. |
| **Dosya Sistemi Yıkımı** | **%58.3** | İzinlerde iyi, ancak derin özyineleme ve inode tükenmesi teşhislerinde zorlandı. |
| **OODA Döngü Mantığı** | **%50.0** | **En Zor Kategori.** Açık hata mesajlarının olmaması Agent'ı "düşünmeye" zorladı, bu da daha düşük geçiş oranına yol açtı ancak gerçek akıl yürütme girişimlerini gösterdi. |
| **Kırmızı Takım** | **%50.0** | Açık güvenlik açıklarını (777 izinleri) başarıyla tespit etti ancak ince cron backdoor desenlerini kaçırdı. |

**Genel Başarı: %65.52** (87 Senaryodan 57'si Geçti)

---

## 5. Dikkat Çekici Savaş Senaryoları

### "Sudo-Yok" Paradoksu (Senaryo 4)
*   **Koşul**: `libssl.so.3` silindi. `sudo` anında bozuldu.
*   **Agent'ın Hamlesi**: `sudo`'nun öldüğünü fark etti. `pkexec`'e yöneldi. Bu da başarısız olunca, `.deb` paketini manuel olarak indirdi, `ar` kullanarak arşivi çıkardı ve paylaşılan kütüphaneyi `/lib/x86_64-linux-gnu/`'a manuel olarak enjekte etti. **Parlak yanal düşünme.**

### Mantık Tuzağı (Senaryo 7)
*   **Koşul**: Bir Python Virtualenv bozulmuştu (eksik aktivasyon scriptleri).
*   **Agent'ın Hamlesi**: Eksik dosyaları körlemesine yamalamaya çalışmak yerine, ortamın "dışarıdan yönetilen" olduğunu fark etti. `requirements.txt`'i yedekledi, tüm dizini yok etti ve ortamı sıfırdan yeniden oluşturdu, yakılmış toprak politikasıyla bağımlılık cehennemini çözdü.

---

## 6. Nasıl Çalıştırılır
(⚠️ **TEHLİKE: Bu script işletim sistemine zarar verir**)

```bash
sudo python3 zai_stress_test.py
```
*Not: Scriptte geçerli Gemini API anahtarlarının yapılandırıldığından emin olun.*
