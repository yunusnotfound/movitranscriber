# MoviTranscriber

Japonca ses ve video dosyalarını **tamamen bilgisayarınızda**, ücretsiz olarak Japonca metne çeviren
basit bir masaüstü aracı. Tarayıcıda açılan tek ekranlı bir arayüzü vardır.

- Motor: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper'ın CPU için
  optimize edilmiş sürümü, int8)
- Arayüz: Gradio (localhost, dışarıya kapalı)
- ffmpeg kurmanız gerekmez; ses ve video çözümleme PyAV ile gelir.

## Gereksinimler

- Windows 10/11
- Python 3.11 veya üstü (3.14 ile test edildi) — <https://www.python.org/downloads/>
  Kurulumda "Add python.exe to PATH" kutusunu işaretleyin.
- İnternet yalnızca ilk kurulumda (paketler) ve ilk model indirmesinde gerekir.
- Disk: paketler ~450 MB (taşınabilir pakette Python ile birlikte ~470 MB), her model 0.5–1.6 GB
  (`models/` klasörüne iner).
- RAM: 8 GB yeterli. 4 GB'lık makinelerde `small` modelini tercih edin.

## Kurulum ve çalıştırma

İki yol vardır. `run.bat` hangisinin mevcut olduğunu kendisi anlar.

### Yol 1: Taşınabilir paket (şirket bilgisayarları için önerilen, internet gerekmez)

Klasörün içinde `python/`, `packages/` ve `models/` alt klasörleri varsa paket hazırdır:
klasörü hedef bilgisayara kopyalayın ve `run.bat` dosyasına çift tıklayın. Python kurulumu,
yönetici hakkı ve internet gerekmez; tarayıcıda <http://127.0.0.1:7860> açılır.

Paketi hazırlamak için (internet erişimi olan bir makinede, bir kez):

```powershell
python tools\build_offline_package.py                # python/ + packages/ + turbo ve small modelleri
python tools\build_offline_package.py --model small  # sadece small (zayıf bilgisayarlar için küçük paket)
python tools\build_offline_package.py --all-models   # dört modelin hepsi (~5 GB)
```

(`build_offline_package.bat` aynı şeyi çift tıkla yapar.) Betik şunları yapar: gömülebilir Python'u
indirir (`python/`), paketleri `packages/` altına kurar, seçilen modelleri `models/` altına indirir ve
paketi doğrular. Uygulama açılışta hangi modellerin indirilmiş olduğunu listede "✓ hazır" olarak
gösterir ve indirilmiş ilk modeli varsayılan yapar; yani sadece small ile hazırlanan paket doğrudan
small ile açılır. Ağ kararsızsa her adımı birkaç kez
dener; yarım kalırsa aynı komutu tekrar çalıştırın, kaldığı yerden devam eder. Paketleme makinesinde
kurulu Python sürümü hangisiyse gömülebilir Python da o sürüm olur (3.11+ önerilir, 3.14 test edildi).

Kopyalarken `python/`, `packages/`, `models/`, `transcriber/`, `app.py` ve `run.bat` birlikte
taşınmalıdır; `.venv/` klasörü kopyalanmaz (taşınabilir değildir).

### Yol 2: Geliştirici kurulumu (sistemde Python kurulu, internet var)

`run.bat` sanal ortam oluşturur, paketleri kurar (birkaç dakika) ve uygulamayı başlatır. Elle:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

Uygulamayı kapatmak için terminal penceresini kapatın.

### Şirket proxy'si / Hugging Face engeli

Uygulama modeli yerelde bulduğunda ağa hiç çıkmaz; bu yüzden taşınabilir pakette proxy sorunu
yaşanmaz. Modelin bir makinede yeniden indirilmesi gerekirse iki seçenek vardır: hazır bir
kurulumdan `models/` klasörünü kopyalamak, ya da `run.bat` içindeki `HTTPS_PROXY` satırını açıp
şirket proxy adresini yazmak.

## Kullanım

1. Ses veya video dosyasını kutuya sürükleyin (ya da tıklayıp seçin).
2. Model seçin (varsayılan: `large-v3-turbo`).
3. **Transkript Et**'e basın. Metin segment segment canlı olarak dolar; ilerleme yüzdesi durum
   satırında görünür.
4. Bitince **Kopyala** simgesiyle panoya alın veya **TXT olarak indir** ile kaydedin.
5. Uzun sürerse **Durdur** ile iptal edebilirsiniz; o ana kadarki metin ekranda kalır.

İlk kullanımda seçilen model Hugging Face'ten indirilir; indirme ilerlemesi terminal penceresinde
görünür. Sonraki çalıştırmalar çevrimdışıdır.

## Model rehberi

Hızlar 4 çekirdekli bir dizüstü CPU'su (i5-8300H) içindir; turbo değeri ölçülmüş, diğerleri tahmindir.
İlk transkripsiyonda ~15 saniyelik bir ısınma süresi eklenir.

| Model | İndirme | Japonca kalitesi | Hız (gerçek zamana göre) | Not |
|---|---|---|---|---|
| large-v3-turbo (varsayılan) | ~1.6 GB | Çok iyi, noktalama var | ~1.1× (1 dk ses ≈ 50 sn) | Genel kullanım için en iyi denge |
| kotoba-whisper-v2.0 | ~1.4 GB | Japonca'ya özel, çok iyi | ~1–1.5× | Çıktıda 。、 gibi noktalama yok |
| medium | ~1.5 GB | İyi | ~0.7–1× | Turbo'dan yavaş ve düşük; yedek |
| small | ~480 MB | Orta | ~3–4× | Zayıf makineler / hızlı ön izleme |

### Zayıf bilgisayarlar için öneri

2-4 çekirdekli, 8 GB RAM'li ofis bilgisayarlarında turbo çalışır ama yavaştır (10 dk ses ≈ 15-25 dk).
Pratik yol: önce **small** ile hızlı bir taslak alın (10 dk ses ≈ 4-8 dk), metin önemliyse aynı
dosyayı **turbo** ile bir kez daha çalıştırın. Durum satırı işlem sırasında kalan süreyi tahmin eder;
uzun dosyaları öğle arası veya mesai sonuna bırakmak da işe yarar. Uygulama aynı anda tek
transkripsiyon yapar; bekleyen dosyaları sırayla yükleyin.

## Desteklenen dosya türleri

- Ses: mp3, wav, m4a, flac, ogg, aac, wma, opus
- Video: mp4, mkv, webm, mov, avi, m4v (ses kanalı otomatik çıkarılır)

## Sık karşılaşılan sorunlar

- **"Python bulunamadı"**: Python'u PATH'e ekleyerek kurun, sonra `run.bat`'ı tekrar çalıştırın.
- **İlk indirme çok yavaş / yarım kaldı**: Uygulamayı kapatıp tekrar açın; indirme kaldığı yerden devam
  eder. Alternatif olarak önce `small` ile deneyin.
- **Aynı cümle defalarca tekrarlanıyor**: `transcriber/config.py` içinde
  `CONDITION_ON_PREVIOUS_TEXT = False` yapın.
- **Noktalama çok az**: `config.py` içindeki `INITIAL_PROMPT` satırını açın (Japonca noktalamalı
  örnek cümle modeli noktalama kullanmaya yönlendirir).
- **Bellek yetersiz**: Daha küçük model seçin; uygulama aynı anda tek model tutar.
- **Tarayıcı açılmadı**: Terminaldeki adresi (<http://127.0.0.1:7860>) elle açın.

## Proje yapısı

```
app.py                          Gradio arayüzü
transcriber/config.py           Model listesi ve transkripsiyon ayarları
transcriber/engine.py           Model yükleme ve transkripsiyon (faster-whisper)
tools/build_offline_package.py  Taşınabilir (çevrimdışı) paket üretici
requirements.txt                Bağımlılıklar
run.bat                         Tek tıkla başlatma (taşınabilir paket veya sanal ortam)
models/                         Whisper modelleri (indirilir veya kopyalanır)
python/                         Gömülebilir Python (sadece taşınabilir pakette)
packages/                       Kurulu paketler (sadece taşınabilir pakette)
```

## Ayarlar

Tüm ince ayarlar `transcriber/config.py` dosyasındadır: model listesi, varsayılan model,
beam size, VAD (sessizlik atlama), CPU iş parçacığı sayısı.
