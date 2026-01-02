# ZAI Shell - Gizlilik & Telemetri Politikası

## Genel Bakış

ZAI Shell, uygulamanın nasıl kullanıldığını anlamak için **gizlilik öncelikli** PostHog analitiği kullanır. Bu, kullanıcı deneyimini geliştirmemize yardımcı olur.

## Topladığımız Veriler

### ✅ Topladığımız Veriler (Anonim Kullanım Analitiği)

PostHog aracılığıyla aşağıdaki anonim kullanım verileri toplanır:

1. **Sistem Bilgileri**
   - İşletim sistemi (Windows/Linux/macOS)
   - İşletim sistemi sürümü
   - Shell türü (cmd/powershell/bash/vb.)

2. **Özellik Kullanım İstatistikleri**
   - Hangi özelliklerin kullanıldığı (GUI otomasyonu, web araştırması, çevrimdışı mod vb.)
   - Mod tercihleri (normal/eco/lightning)
   - Komut çalıştırma başarı/başarısızlık oranları
   - Otomatik yeniden deneme girişimleri ve sonuçları
   - Düşünme modu kullanımı
   - Force komut kullanımı

3. **Oturum Analitiği**
   - Oturum süresi
   - Oturum başına istek sayısı
   - Oturum başlangıç/bitiş olayları

4. **Arayüz Tercihleri**
   - Terminal vs GUI otomasyon kullanımı
   - Özellik etkinleştirme/devre dışı bırakma kalıpları

5. **Hata Takibi**
   - Güvenli mod engellemeleri (güvenlik analizi için)
   - Görev başarısızlık oranları (iyileştirme için)

### ❌ Toplamadığımız Veriler

**ASLA** toplamayız:

- ❌ Gerçek komutlarınız veya dosya içerikleri
- ❌ Dosya yolları veya dizin yapıları
- ❌ Kişisel bilgiler veya kullanıcı adları
- ❌ IP adresleri veya konum verileri
- ❌ Herhangi bir hassas veya özel veri
- ❌ Ekran içeriği veya ekran görüntüleri
- ❌ Klavye girişi veya yazılan metin
- ❌ Ağ trafiği veya tarama geçmişi

## Kullanıcı Tanımlayıcısı

- İlk çalıştırmada **rastgele anonim UUID** oluşturulur ve `.zaishell_telemetry_id` dosyasında yerel olarak saklanır
- Bu UUID **yalnızca** aynı kullanıcıdan gelen analitik olaylarını gruplamak için kullanılır
- **Kişisel bilgi içermez** ve size geri izlenemez

## Telemetriyi Nasıl Kontrol Edersiniz

### Telemetri varsayılan olarak ETKİNDİR

ZAI Shell'i ilk başlattığınızda telemetri **varsayılan olarak etkindir**. Tam kontrole sahipsiniz:

### Telemetriyi Tamamen Devre Dışı Bırak

```bash
telemetry off
```

### Telemetriyi Tekrar Etkinleştir

```bash
telemetry on
```

### Mevcut Durumu Kontrol Et

```bash
telemetry
```

Tercihiniz kaydedilir ve oturumlar arasında kalıcıdır.

## Neden Bu Verileri Topluyoruz

### 1. Uygulama İyileştirmesi
- Hangi özelliklerin en çok/en az kullanıldığını anlamak
- Yaygın hata kalıplarını belirlemek
- Geliştirme çabalarını önceliklendirmek
- Gerçek kullanıma dayalı kullanıcı deneyimini iyileştirmek
- Gelecek özellik geliştirmesine rehberlik etmek

### 2. Araştırma & Eğitim
- AI destekli shell kullanım kalıplarını anlamak
- İnsan-AI etkileşimi üzerine akademik araştırma
- Geliştirme için eğitici içgörüler

### 3. Açık Kaynak Geliştirme
- Ölçülebilir etkiye sahip sürdürülebilir proje oluşturmak
- Özellik önceliklendirmesi için veri odaklı kararlar almak
- Küresel kullanım kalıplarını anlamak

## Veri Güvenliği & Gizlilik

- **Kişisel Veri Yok**: Kasıtlı olarak kişisel olarak tanımlanabilir herhangi bir bilgi toplamaktan kaçınıyoruz
- **Tasarımdan Anonim**: Tüm veriler baştan anonimleştirilir
- **Veri Satışı Yok**: Verilerinizi asla üçüncü taraflara satmayız veya paylaşmayız
- **PostHog Gizliliği**: PostHog, kullanıcı gizliliğine saygı duyan gizlilik odaklı bir analitik platformudur
- **Yerel Kontrol**: Basit bir komutla telemetriyi istediğiniz zaman devre dışı bırakabilirsiniz

## Veri Depolama & Saklama

- Veriler **PostHog'un ABD sunucularında** (`us.i.posthog.com`) saklanır
- Toplu istatistikler araştırma amaçlı saklanabilir
- Bireysel kullanıcı takibi veya profilleme yapılmaz

## Açık Kaynak Şeffaflığı

ZAI Shell **açık kaynaklıdır**. Şunları yapabilirsiniz:
- `zaishell.py` dosyasındaki telemetri kodunu inceleyin (TelemetryManager sınıfı)
- Tam olarak neyin gönderildiğini doğrulayın
- Yerel kurulumunuzda telemetriyi değiştirin veya kaldırın
- Daha da gizlilik odaklı hale getirmek için katkıda bulunun

## Bu Politikadaki Değişiklikler

Uygulamayı geliştirdikçe bu politikayı güncelleyebiliriz. Herhangi bir değişiklik, net commit mesajlarıyla GitHub deposunda yansıtılacaktır.

## İletişim & Sorular

Gizlilik veya telemetri hakkında sorularınız varsa:
- GitHub'da bir issue açın
- Kaynak kodunu kendiniz inceleyin
- Geliştirme ekibine ulaşın

---

**Son Güncelleme**: Ocak 2026  
**Sürüm**: v1.0
