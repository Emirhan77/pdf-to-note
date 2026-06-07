Tamam Emirhan Bey. Bu projeyi artık şu mantıkla planlayalım:

> **Hazır özetleme/soru üretme kütüphanesine körü körüne güvenmeyen, PDF metnini temizleyip analiz eden, cümlelere önem puanı veren, konu bazlı ders notu çıkaran ve cevaplanabilir sorular üreten bulut tabanlı sistem.**

Bu yaklaşım ödev için daha güçlü olur çünkü hoca sadece uygulama istemiyor; **problem tanımı, literatür, yöntem, mimari, deneysel sonuç, değerlendirme ve karşılaştırma** istiyor. PDF’te de proje konusunun teorik açıklanması, uygulamasının yapılması, yöntemin açıklanması, deneysel sonuçların değerlendirilmesi ve literatürle karşılaştırılması gerektiği belirtilmiş. 

---

# 1. Projenin Net Başlığı

Bence proje başlığını şu yapalım:

## **Bulut Tabanlı Skor Destekli Ders Notu Çıkarma ve Otomatik Soru Üretme Sistemi**

Alternatif daha akademik başlık:

## **Bulut Tabanlı Hibrit Metin İşleme Yaklaşımı ile Ders Notu Özetleme ve Soru Üretme Sistemi**

Benim favorim ikinci başlık. Çünkü “hibrit metin işleme” deyince proje sadece basit web uygulaması gibi değil, yöntem içeren akademik bir çalışma gibi duruyor.

---

# 2. Projenin Ana Problemi

Problem şu olacak:

> Üniversite öğrencileri uzun PDF ders notları, slaytlar ve dokümanlar içindeki önemli bilgileri kısa sürede ayıklamakta zorlanmaktadır. Mevcut otomatik özetleme araçları ise çoğu zaman PDF yapısındaki bozukluklar, başlık-karışıklıkları, kaynakça satırları, şekil açıklamaları ve bağlam eksikliği nedeniyle ders çalışmaya uygun olmayan yüzeysel özetler ve anlamsız sorular üretebilmektedir.

Bu yüzden bizim sistemin amacı:

> PDF’i doğrudan özetlemek yerine, önce metni temizleyen, bölümleyen, önemli cümleleri puanlayan, konu bazlı not çıkaran ve sadece cevaplanabilir sorular üreten kontrollü bir sistem geliştirmek.

---

# 3. Projenin Temel Fikri

Sistem şöyle çalışacak:

```text
Kullanıcı PDF yükler
        ↓
PDF bulut depolamaya kaydedilir
        ↓
PDF içerisindeki metin çıkarılır
        ↓
Metin temizlenir
        ↓
Başlıklar, paragraflar ve cümleler ayrılır
        ↓
Cümlelere önem puanı verilir
        ↓
Konu bazlı ders notu çıkarılır
        ↓
Anahtar kavramlar belirlenir
        ↓
Soru-cevap çiftleri üretilir
        ↓
Kalite kontrol filtresinden geçirilir
        ↓
Sonuç kullanıcıya gösterilir
```

Buradaki en önemli fark şu:

> Sistem “rastgele özet” üretmeyecek. Cümleleri analiz edip önem derecesine göre seçecek.

---

# 4. Kullanılacak Teknolojiler

Bu proje için en mantıklı teknoloji yapısı şöyle:

| Katman         | Teknoloji                           | Açıklama                              |
| -------------- | ----------------------------------- | ------------------------------------- |
| Arayüz         | HTML, CSS, JavaScript               | PDF yükleme ve sonuç gösterme ekranı  |
| Backend        | Python Flask                        | Basit ve akademik proje için yeterli  |
| PDF okuma      | PyMuPDF                             | PDF’ten metin çıkarma                 |
| Metin işleme   | Python kendi algoritmamız           | Cümle puanlama, temizlik, soru üretme |
| Veritabanı     | SQLite                              | PDF bilgisi, özetler ve sorular için  |
| Bulut depolama | AWS S3 veya Google Cloud Storage    | Yüklenen PDF’lerin bulutta saklanması |
| Yayınlama      | Render / Railway / Google Cloud Run | Uygulamanın bulutta çalışması         |
| Teslim         | Google Drive / OneDrive             | Kod, video, rapor paylaşımı           |

Başlangıçta **Flask + SQLite + lokal dosya kaydı** ile MVP yapılır. Sonra bulut depolama ve deploy eklenir.

---

# 5. Projenin Modülleri

## Modül 1: PDF Yükleme Modülü

Kullanıcı PDF yükleyecek.

Sistem şu kontrolleri yapacak:

```text
Dosya PDF mi?
Dosya boş mu?
Dosya boyutu kabul edilebilir mi?
Aynı isimli dosya daha önce yüklendi mi?
Metin çıkarılabilir mi?
```

Bu modülün çıktısı:

```text
uploaded_file.pdf
document_id
upload_time
file_path veya cloud_url
```

---

## Modül 2: PDF Metin Çıkarma Modülü

PDF sayfa sayfa okunacak.

Çıktı şu olacak:

```text
Sayfa 1 metni
Sayfa 2 metni
Sayfa 3 metni
...
Tüm metin
```

Ama burada doğrudan özetlemeye geçmeyeceğiz. Önce temizleyeceğiz.

---

## Modül 3: Metin Temizleme Modülü

Bu modül çok önemli. Çünkü saçma özet ve saçma soruların çoğu bozuk PDF metninden çıkar.

Temizlenecek şeyler:

```text
Fazla boşluklar
Tekrarlı satırlar
Sayfa numaraları
Kaynakça satırları
Şekil/tablo açıklamaları
Çok kısa anlamsız satırlar
URL ve gereksiz semboller
Bozuk karakterler
```

Örnek:

Kötü metin:

```text
Şekil 2.1'de gösterilmiştir.
3
www.example.com
Bulut
bilişim
internet üzerinden...
```

Temizlenmiş metin:

```text
Bulut bilişim, internet üzerinden bilgi işlem kaynaklarının hizmet olarak sunulmasını sağlar.
```

---

## Modül 4: Bölümleme Modülü

Metni tek parça olarak işlemeyeceğiz. Çünkü uzun PDF’lerde bağlam kaybolur.

Metni şu yapılara ayıracağız:

```text
Başlıklar
Alt başlıklar
Paragraflar
Cümleler
```

Örneğin:

```text
1. Bulut Bilişim Nedir?
2. Bulut Bilişim Hizmet Modelleri
3. Bulut Depolama
4. Güvenlik ve Erişim
```

Her bölüm kendi içinde analiz edilecek. Böylece not daha anlamlı olacak.

---

# 6. Asıl Yöntem: Cümle Skorlama Sistemi

Bu projenin bilimsel tarafı burada olacak.

Her cümleye önem puanı vereceğiz.

## Cümle puanlama kriterleri

| Kriter                                                                     | Puan |
| -------------------------------------------------------------------------- | ---: |
| Tanım cümlesi içeriyorsa                                                   |   +3 |
| Başlık kelimelerini içeriyorsa                                             |   +2 |
| Anahtar kavram içeriyorsa                                                  |   +2 |
| “amaç”, “avantaj”, “dezavantaj”, “önem”, “kullanılır” gibi kelimeler varsa |   +2 |
| Liste/sınıflandırma içeriyorsa                                             |   +2 |
| Çok kısa ise                                                               |   -2 |
| Çok uzun ve karmaşıksa                                                     |   -1 |
| Kaynakça, şekil, tablo, sayfa numarası içeriyorsa                          |   -3 |
| Aynı cümle daha önce seçildiyse                                            |   -4 |

Örnek:

```text
Bulut bilişim, internet üzerinden bilgi işlem kaynaklarının hizmet olarak sunulmasıdır.
```

Bu cümle yüksek puan alır çünkü tanım cümlesidir.

```text
Şekil 3'te bu yapı gösterilmiştir.
```

Bu cümle düşük puan alır çünkü tek başına ders notu değeri yoktur.

---

# 7. Not Çıkarma Mantığı

Sistem doğrudan paragraf özeti vermeyecek. Daha düzenli ders notu çıkaracak.

Çıktı formatı şöyle olacak:

```text
Konu Başlığı

Kısa Tanım:
...

Önemli Noktalar:
- ...
- ...
- ...

Anahtar Kavramlar:
...

Kısa Ders Notu:
...
```

Örnek çıktı:

```text
Konu: Bulut Bilişim

Kısa Tanım:
Bulut bilişim, bilgi işlem kaynaklarının internet üzerinden hizmet olarak sunulmasıdır.

Önemli Noktalar:
- Kullanıcılar fiziksel sunucu sahibi olmadan kaynak kullanabilir.
- Depolama, işlem gücü ve yazılım hizmetleri internet üzerinden sağlanabilir.
- Ölçeklenebilirlik ve maliyet avantajı sağlar.

Anahtar Kavramlar:
Bulut bilişim, sanallaştırma, IaaS, PaaS, SaaS, depolama.

Kısa Ders Notu:
Bulut bilişim, bilişim kaynaklarının internet üzerinden hizmet olarak sunulduğu bir modeldir. Bu yapı sayesinde kullanıcılar donanım yatırımı yapmadan ihtiyaç duydukları kaynaklara erişebilir.
```

Bu, klasik özetten daha faydalı olur.

---

# 8. Soru Üretme Mantığı

Soru üretimini de rastgele yapmayacağız.

Her soru, önemli cümlelerden üretilecek ve yanında cevabı da olacak.

## Soru tipleri

| Cümle Türü            | Soru Kalıbı                          |
| --------------------- | ------------------------------------ |
| Tanım cümlesi         | “... nedir?”                         |
| Amaç cümlesi          | “... amacı nedir?”                   |
| Avantaj cümlesi       | “... avantajları nelerdir?”          |
| Sınıflandırma cümlesi | “... türleri nelerdir?”              |
| Neden-sonuç cümlesi   | “... neden önemlidir?”               |
| Karşılaştırma cümlesi | “... ile ... arasındaki fark nedir?” |

Örnek:

Kaynak cümle:

```text
Bulut bilişim hizmet modelleri IaaS, PaaS ve SaaS olarak üçe ayrılır.
```

Üretilen soru:

```text
Bulut bilişim hizmet modelleri nelerdir?
```

Cevap:

```text
Bulut bilişim hizmet modelleri IaaS, PaaS ve SaaS olarak üçe ayrılır.
```

Bu çok önemli. Çünkü cevap varsa soru daha güvenilir olur.

---

# 9. Kalite Kontrol Modülü

Sistem kötü soruları otomatik eleyecek.

Elenecek soru tipleri:

```text
Bu nedir?
Şu neden önemlidir?
Şekil neyi göstermektedir?
Tablo neyi açıklar?
Kaynakça nedir?
Çok kısa veya anlamsız sorular
Cevabı olmayan sorular
Tekrarlı sorular
```

Kalite kontrol şartları:

```text
Soru en az 4 kelime olmalı.
Soru içinde konu/kavram adı geçmeli.
Her sorunun kaynak cümlesi olmalı.
Aynı kavramdan çok fazla tekrar soru üretilmemeli.
Belirsiz “bu, şu, o” ifadeleriyle başlamamalı.
```

Bu sayede proje “saçma soru üreten sistem” olmaktan çıkar.

---

# 10. Uygulama Ekranları

## 1. Ana Sayfa

İçerik:

```text
Proje adı
PDF yükleme alanı
Özet uzunluğu seçimi
Soru sayısı seçimi
Analiz Et butonu
```

## 2. Sonuç Sayfası

İçerik:

```text
Dosya adı
Sayfa sayısı
Çıkarılan metin uzunluğu
İşlem süresi
Ders notu
Anahtar kavramlar
Üretilen soru-cevaplar
PDF bulut bağlantısı
```

## 3. Geçmiş Analizler Sayfası

İçerik:

```text
Daha önce yüklenen dosyalar
Oluşturulan notlar
Üretilen soru sayısı
Analiz tarihi
```

Bu üçüncü ekran zorunlu değil ama projeyi daha dolu gösterir.

---

# 11. Veritabanı Planı

Basit bir SQLite veritabanı yeterli.

## `documents` tablosu

```text
id
file_name
file_path
cloud_url
page_count
upload_date
processing_status
```

## `analysis_results` tablosu

```text
id
document_id
clean_text
generated_notes
keywords
processing_time
created_at
```

## `questions` tablosu

```text
id
document_id
question_text
answer_text
source_sentence
question_type
quality_score
```

Bu yapı raporda ER diyagramı olarak gösterilebilir.

---

# 12. Sistem Mimarisi

Rapora koyacağımız mimari şöyle olacak:

```text
Kullanıcı
   |
   v
Web Arayüzü
HTML / CSS / JavaScript
   |
   v
Flask Backend API
   |
   |---- PDF Upload Service
   |---- PDF Text Extraction Service
   |---- Text Cleaning Service
   |---- Sentence Scoring Service
   |---- Note Generation Service
   |---- Question Generation Service
   |---- Quality Control Service
   |
   v
SQLite Database
   |
   v
Cloud Storage
AWS S3 / Google Cloud Storage
```

Bu mimari ödevde istenen “materyal, metot ve mimari” kısmını karşılar. PDF’te de kullanılan materyal, metot ve mimarinin açıklanması; ayrıca flow-chart, sözde kod, durum diyagramı ve varlık ilişki diyagramı kullanılması isteniyor. 

---

# 13. Akış Diyagramı Planı

Flow-chart şu adımlardan oluşacak:

```text
Başla
  ↓
PDF yükle
  ↓
Dosya kontrolü yap
  ↓
PDF geçerli mi?
  ↓
Hayır → Hata mesajı göster
  ↓
Evet
  ↓
PDF metnini çıkar
  ↓
Metin boş mu?
  ↓
Evet → OCR gerekli uyarısı göster
  ↓
Hayır
  ↓
Metni temizle
  ↓
Cümlelere ayır
  ↓
Cümleleri puanla
  ↓
En önemli cümleleri seç
  ↓
Ders notu oluştur
  ↓
Anahtar kavramları çıkar
  ↓
Soru-cevap üret
  ↓
Kalite filtresinden geçir
  ↓
Sonuçları veritabanına kaydet
  ↓
Kullanıcıya göster
  ↓
Bitir
```

---

# 14. Sözde Kod Planı

Rapora koyacağımız sözde kod şöyle olabilir:

```text
Algoritma: Skor Destekli Ders Notu ve Soru Üretme

Girdi: PDF dosyası
Çıktı: Ders notu, anahtar kavramlar, soru-cevap listesi

1. PDF dosyasını yükle
2. PDF dosyasından metni çıkar
3. Metni temizle
4. Metni başlık, paragraf ve cümlelere ayır
5. Her cümle için önem puanı hesapla:
      a. Tanım içeriyorsa puan artır
      b. Anahtar kavram içeriyorsa puan artır
      c. Başlık kelimeleriyle ilişkiliyse puan artır
      d. Gereksiz veya kısa cümle ise puan azalt
6. En yüksek puanlı cümleleri seç
7. Seçilen cümlelerden konu bazlı ders notu oluştur
8. Anahtar kavramları belirle
9. Her önemli cümle için uygun soru kalıbını seç
10. Soru ve cevap çifti oluştur
11. Kalite kontrol filtresi uygula
12. Sonuçları veritabanına kaydet
13. Sonuçları kullanıcıya göster
```

---

# 15. Deneysel Sonuç Planı

Hoca deneysel sonuç istediği için mutlaka test yapacağız.

En az 5 PDF ile test yapılmalı:

| Test   | PDF Türü            | Amaç                         |
| ------ | ------------------- | ---------------------------- |
| Test 1 | Kısa ders notu      | Temel başarı testi           |
| Test 2 | Uzun ders notu      | Uzun metin performansı       |
| Test 3 | Slayt PDF’i         | Parçalı metin testi          |
| Test 4 | Teknik konu PDF’i   | Anahtar kavram çıkarma testi |
| Test 5 | Taranmış/görsel PDF | Sistem sınırını gösterme     |

Ölçülecek değerler:

| Metrik                   | Açıklama                       |
| ------------------------ | ------------------------------ |
| PDF sayfa sayısı         | Dosya uzunluğu                 |
| Çıkarılan kelime sayısı  | PDF’den ne kadar metin geldiği |
| İşlem süresi             | Sistem performansı             |
| Üretilen not uzunluğu    | Notun hacmi                    |
| Üretilen soru sayısı     | Soru üretim kapasitesi         |
| Anlamlı soru oranı       | Elle değerlendirilecek kalite  |
| Boş/başarısız PDF durumu | Sistem sınırı                  |

Örnek deneysel sonuç tablosu:

| PDF   | Sayfa | Kelime | İşlem Süresi | Üretilen Soru | Anlamlı Soru | Başarı Oranı |
| ----- | ----: | -----: | -----------: | ------------: | -----------: | -----------: |
| PDF 1 |     5 |  1.800 |         3 sn |            10 |            9 |          %90 |
| PDF 2 |    12 |  5.600 |         7 sn |            15 |           13 |          %86 |
| PDF 3 |    24 | 11.200 |        15 sn |            20 |           16 |          %80 |
| PDF 4 |    38 | 18.500 |        24 sn |            25 |           19 |          %76 |
| PDF 5 |    10 |      0 |            - |             0 |            0 |  OCR gerekli |

Böylece deneysel sonuç kısmı boş kalmaz.

---

# 16. Literatürle Karşılaştırma Planı

Raporda şunu yapacağız:

```text
Mevcut otomatik özetleme sistemleri genellikle metni doğrudan işleyerek özet üretmektedir.
Bu çalışmada ise PDF metni önce temizlenmiş, cümleler önem puanına göre değerlendirilmiş ve soru üretimi sadece cevaplanabilir cümlelerden yapılmıştır.
```

Karşılaştırma tablosu:

| Özellik                   | Genel Özetleme Araçları | Bizim Sistem                |
| ------------------------- | ----------------------- | --------------------------- |
| PDF temizleme             | Sınırlı                 | Var                         |
| Cümle puanlama            | Genellikle kapalı yapı  | Açık ve açıklanabilir       |
| Ders notu formatı         | Genelde paragraf        | Başlık, tanım, madde yapısı |
| Soru-cevap üretimi        | Her zaman yok           | Var                         |
| Kalite filtresi           | Sınırlı                 | Var                         |
| Bulut depolama            | Değişken                | Var                         |
| Akademik açıklanabilirlik | Düşük/orta              | Yüksek                      |

Bu karşılaştırma ödevde istenen “literatürdeki benzer çalışmalar ile karşılaştırma” kısmına destek olur. 

---

# 17. Haftalık Çalışma Planı

Bugünün tarihi 30 Nisan 2026 olduğu için teslim tarihine göre planı sıkı tutmalıyız. PDF’te raporların **24 Mayıs 2026 Pazar 23:59’a kadar** yüklenmesi gerektiği yazıyor; sunum tarihleri de 25 Mayıs, 1 Haziran ve 8 Haziran 2026 olarak belirtilmiş. 

## 1. Aşama — 30 Nisan - 3 Mayıs

Amaç: Proje iskeletini kurmak.

Yapılacaklar:

```text
Proje klasörü oluşturulacak
Flask kurulacak
Ana sayfa hazırlanacak
PDF yükleme formu yapılacak
Basit upload işlemi çalıştırılacak
README dosyası başlatılacak
```

Çıktı:

```text
Çalışan basit web arayüzü
PDF yükleme ekranı
Proje klasör yapısı
```

---

## 2. Aşama — 4 Mayıs - 7 Mayıs

Amaç: PDF metin çıkarma ve temizleme.

Yapılacaklar:

```text
PyMuPDF ile PDF metni çıkarılacak
Sayfa sayısı alınacak
Metin temizleme fonksiyonları yazılacak
Boş PDF kontrolü yapılacak
Temizlenmiş metin ekranda gösterilecek
```

Çıktı:

```text
PDF → temiz metin dönüşümü
Metin çıkarma testi
```

---

## 3. Aşama — 8 Mayıs - 11 Mayıs

Amaç: Cümle skorlama ve ders notu çıkarma.

Yapılacaklar:

```text
Metin cümlelere ayrılacak
Cümle puanlama algoritması yazılacak
En önemli cümleler seçilecek
Ders notu formatı oluşturulacak
Anahtar kavram çıkarma yapılacak
```

Çıktı:

```text
PDF → anlamlı ders notu
Konu bazlı not yapısı
```

---

## 4. Aşama — 12 Mayıs - 15 Mayıs

Amaç: Soru-cevap üretme.

Yapılacaklar:

```text
Tanım cümlesinden soru üretme
Amaç cümlesinden soru üretme
Avantaj/dezavantaj soruları üretme
Liste/sınıflandırma soruları üretme
Her soruya cevap ekleme
Kalite kontrol filtresi yazma
```

Çıktı:

```text
PDF → ders notu + soru-cevap listesi
```

---

## 5. Aşama — 16 Mayıs - 18 Mayıs

Amaç: Veritabanı ve bulut entegrasyonu.

Yapılacaklar:

```text
SQLite tabloları oluşturulacak
Yüklenen PDF bilgileri kaydedilecek
Oluşturulan notlar kaydedilecek
Sorular kaydedilecek
AWS S3 veya Google Cloud Storage bağlantısı kurulacak
PDF buluta yüklenecek
```

Çıktı:

```text
Bulut destekli çalışan sistem
Veritabanı kayıtları
```

---

## 6. Aşama — 19 Mayıs - 21 Mayıs

Amaç: Deneysel testler.

Yapılacaklar:

```text
En az 5 farklı PDF ile test yapılacak
İşlem süresi ölçülecek
Üretilen soru sayısı ölçülecek
Anlamlı soru oranı hesaplanacak
Başarısız durumlar not edilecek
Tablolar hazırlanacak
```

Çıktı:

```text
Deneysel sonuç tablosu
Başarı oranı değerlendirmesi
```

---

## 7. Aşama — 22 Mayıs - 24 Mayıs

Amaç: Rapor, video ve teslim.

Yapılacaklar:

```text
Word raporu hazırlanacak
PDF hali alınacak
10-15 dakikalık video çekilecek
Kodlar düzenlenecek
Drive/OneDrive bağlantısı hazırlanacak
Rapor içine paylaşım linki yazılacak
Teslim dosyası sıkıştırılacak
```

Çıktı:

```text
Word raporu
PDF raporu
Kaynak kodlar
Video
Paylaşım bağlantısı
```

PDF’te kaynak kod, video, Word/PDF rapor ve paylaşım bağlantısı isteniyor; bağlantının herkes tarafından indirilebilir olması gerektiği de özellikle belirtilmiş. 

---

# 18. Proje Dosya Yapısı

Şöyle bir yapı yapalım:

```text
cloud-note-question-system/
│
├── app.py
├── requirements.txt
├── README.md
├── .env
│
├── static/
│   ├── style.css
│   └── script.js
│
├── templates/
│   ├── index.html
│   ├── result.html
│   └── history.html
│
├── uploads/
│
├── services/
│   ├── pdf_service.py
│   ├── text_cleaner.py
│   ├── sentence_scorer.py
│   ├── note_generator.py
│   ├── question_generator.py
│   ├── quality_filter.py
│   └── cloud_storage.py
│
├── database/
│   ├── db.py
│   └── models.sql
│
├── experiments/
│   ├── test_results.xlsx
│   └── evaluation_notes.md
│
└── docs/
    ├── report.docx
    ├── report.pdf
    └── diagrams/
```

Bu yapı hem düzenli hem de teslim için uygun olur.

---

# 19. Rapor Planı

Rapor başlıkları şöyle olmalı:

```text
1. Giriş
2. Problem Tanımı
3. Literatür Taraması
4. Bulut Bilişim ve Kullanılan Bulut Altyapısı
5. Önerilen Sistem
6. Kullanılan Materyal, Metot ve Mimari
7. Önerilen Yöntem
   7.1 PDF Metin Çıkarma
   7.2 Metin Temizleme
   7.3 Cümle Skorlama
   7.4 Ders Notu Oluşturma
   7.5 Soru-Cevap Üretme
   7.6 Kalite Kontrol
8. Sistem Tasarımı
   8.1 Sistem Mimarisi
   8.2 Flow-chart
   8.3 Sözde Kod
   8.4 Varlık İlişki Diyagramı
   8.5 Durum Diyagramı
9. Uygulama Geliştirme Süreci
10. Deneysel Sonuçlar
11. Sonuçlar ve Tartışma
12. Karşılaşılan Zorluklar
13. Kaynakça
```

Bu yapı hocanın PDF’te istediği başlıklarla uyumlu olur. Raporda Word, Times New Roman 12 punto, iki yana yaslı paragraf, şekil ve tablo açıklaması gibi biçimsel kurallar da isteniyor. 

---

# 20. Projenin Savunma Cümlesi

Sunumda projeyi şöyle savunabiliriz:

> Bu projede hazır bir özetleme aracına doğrudan PDF vermek yerine, PDF dokümanlarından çıkarılan metin önce temizlenmiş, ardından cümleler önem skoruna göre değerlendirilmiştir. Sistem, tanım, amaç, avantaj, sınıflandırma ve neden-sonuç içeren cümleleri önceliklendirerek konu bazlı ders notları oluşturur. Soru üretimi ise sadece kaynak cümlesi bulunan ve cevaplanabilir bilgiler üzerinden yapılır. Böylece öğrencilerin ders çalışmasına daha uygun, açıklanabilir ve kontrol edilebilir bir bulut tabanlı not çıkarma sistemi geliştirilmiştir.

Bu cümle projenin ana fikri olur.

---

# 21. Nihai Plan Özeti

Bu projeyi şu sırayla yapacağız:

```text
1. Flask tabanlı web uygulaması kur.
2. PDF yükleme ekranı yap.
3. PDF’ten metni çıkar.
4. Metni temizle.
5. Cümlelere ayır.
6. Cümle skorlama algoritması yaz.
7. Önemli cümlelerden ders notu oluştur.
8. Anahtar kavramları çıkar.
9. Soru-cevap çiftleri üret.
10. Kalite filtresiyle kötü soruları ele.
11. Sonuçları veritabanına kaydet.
12. PDF’i bulut depolamaya gönder.
13. En az 5 PDF ile deneysel test yap.
14. Sonuçları tablo ve grafikle raporla.
15. Word raporu, video ve teslim klasörünü hazırla.
```

Bence bu planla proje hem **mantıklı**, hem **yapılabilir**, hem de hocanın ödev isterlerini karşılayacak seviyede olur. Bundan sonraki en doğru adım: **projenin klasör yapısını ve ilk çalışan Flask uygulamasını kurmak.**
