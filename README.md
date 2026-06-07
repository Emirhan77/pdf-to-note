# PDF to Note

Bulut Tabanli Hibrit Metin Isleme Yaklasimi ile Ders Notu Ozetleme ve Soru Uretme Sistemi.

## Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Uygulama varsayilan olarak `http://127.0.0.1:5000` adresinde calisir.

## Calisma Modlari

Uygulama artik hibrit calisir: PDF metnini once kendi kurallariyla temizler, sonra final ders notu ve 10 soruyu LLM veya prompt export ile uretir.

Varsayilan ucretsiz mod Ollama'dir:

```powershell
ollama pull qwen2.5:7b
ollama serve
python app.py
```

Bilgisayar zayifsa `.env` icinde `OLLAMA_MODEL=qwen2.5:3b` secilebilir. Ollama calismiyorsa uygulama hata vermek yerine prompt export moduna duser ve ChatGPT'ye yapistirilacak hazir promptu sonuc ekraninda gosterir.

Yerel model yavas kalirsa `.env` icindeki varsayilan ayarlar kalite/hiz dengesi icin kisilabilir:

```text
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=3072
LLM_MAX_SOURCE_CHARS=9000
```

Opsiyonel OpenAI modu icin `.env`:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
```

OpenAI modu kullanilacaksa ayrica `pip install openai` gerekir.

`OPENAI_API_KEY` yoksa sistem yine prompt export'a duser.

## AWS S3 Bulut Depolama

Uygulama varsayilan olarak PDF'leri lokal `uploads/` klasorune kaydeder. Bulut altyapisi kaniti icin AWS S3 modu acilabilir. Bucket public olmamalidir; uygulama S3'e yukleme yapar ve sonuc ekraninda gecici presigned PDF baglantisi gosterir.

Once AWS tarafinda dusuk tutarli bir AWS Budgets alarmi kurun, tek region secin ve sadece ilgili S3 bucket icin yetkili bir IAM access key olusturun. Sonra `.env` icine su ayarlari ekleyin:

```text
CLOUD_STORAGE_PROVIDER=aws_s3
AWS_S3_BUCKET=pdf-to-note-example-bucket
AWS_REGION=eu-central-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_KEY_PREFIX=uploads
AWS_PRESIGNED_URL_EXPIRES=604800
```

AWS ayarlari eksikse veya `CLOUD_STORAGE_PROVIDER=local` ise sistem lokal kayitla calismaya devam eder. S3 yukleme hatasi analiz akisini durdurmaz; PDF lokal dosya uzerinden islenir.

IAM kullanicisi icin ornek en dar S3 policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::pdf-to-note-example-bucket/uploads/*"
    }
  ]
}
```

Bucket public access kapali kalabilir. Uygulama PDF indirme/gosterme icin gecici presigned URL uretir.

## MVP Kapsami

- PDF yukleme
- Lokal dosya kaydi
- Opsiyonel AWS S3 bulut depolama ve presigned PDF baglantisi
- PyMuPDF ile metin cikarma
- Blok bazli metin temizleme
- Cumle skorlama ve konu bazli dengeli kaynak paketi hazirlama
- LLM destekli ders notu ve soru-cevap uretimi
- 10 soru icin LLM tamamlama ve guvenli fallback
- Prompt export fallback
- SQLite kayitlari
- Gecmis analizler ekrani
- Her analiz icin `experiments/results/` altina Markdown ve JSON sonuc dosyasi
- PDF metni blok bazli okunur, madde isaretleri/slayt kalintilari temizlenir ve sorular kalite gerekcesiyle kaydedilir
