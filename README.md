# CevapAnaliz

Açık uçlu öğrenci cevaplarını, öğretmenin referans cevabıyla **anlam bakımından** karşılaştırarak otomatik puanlayan, puanın nedenini (eksik kavramları) gösteren ve emin olamadığı cevapları öğretmenin kontrolüne bırakan bir değerlendirme sistemi.

Fırat Üniversitesi Bilgisayar Mühendisliği Tasarım Dersi projesi · **Semantik Mühendisleri**


## Klasör yapısı

```
data/raw/          Ham veri setleri (depoya yüklenmez, betikle indirilir)
data/processed/    Ortak biçime çevrilmiş veri (depoya yüklenmez)
scripts/           Çalıştırılabilir betikler (veri indirme, dönüştürme, deneyler)
src/veri/          Veri setlerini ortak biçime çeviren kod
src/puanlama/      Puanlama motoru: özellikler (FR-03) ve başarı ölçütleri (NFR-01)
src/arayuz/        Web arayüzü (Streamlit) — geliştirilecek
tests/             Birim testleri
sonuclar/          Deney sonuçları
```

## Kurulum

Python 3.10 veya üzeri gerekir.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

## Veri

```bash
python scripts/veri_indir.py     # Mohler ve SemEval-2013 veri setlerini data/raw/ altına indirir
python scripts/ortak_bicim.py    # Hepsini data/processed/ortak_veri.csv dosyasında birleştirir
```

| Veri seti | Cevap | Soru | Puan / etiket | 0–1 puana çevirme |
|---|---|---|---|---|
| Mohler (UNT) | 2.273 | 81 | 0–5 (iki puanlayıcının ortalaması) | puan / 5 |
| SemEval-2013 SciEntsBank | 10.804 | 195 | 5 etiket | doğru = 1, kısmen doğru = 0,5, diğerleri = 0 |
| SemEval-2013 Beetle | 5.199 | 42 | 5 etiket | aynı |

Ortak biçimin sütunları: `veri_seti, bolum, soru_id, soru, referans_cevap, ogrenci_cevap, orijinal_puan, puan`

Veri dosyaları lisans koşulları nedeniyle depoya eklenmez; herkes yukarıdaki betikle kendi bilgisayarına indirir.

## İlk deney: TF-IDF temel yöntemi

```bash
python scripts/ilk_deney_tfidf.py
```

İki yöntem karşılaştırılır: yalnız TF-IDF kosinüs benzerliği ve üç özelliğin (kosinüs, n-gram örtüşmesi, uzunluk oranı) doğrusal regresyonla birleştirilmesi. Mohler'de soru bazlı 5 katlı çapraz doğrulama, SemEval'de veri setinin kendi test kümeleri kullanılır. Ayrıntılı sonuçlar: [`sonuclar/ilk_deney_tfidf.csv`](sonuclar/ilk_deney_tfidf.csv)

| Veri seti (test) | Yöntem | Pearson | QWK |
|---|---|---|---|
| Mohler (5 katlı ÇD) | Yalnız kosinüs | 0,451 | 0,098 |
| Mohler (5 katlı ÇD) | Üç özellik | 0,499 | 0,328 |
| SciEntsBank (görülmemiş cevaplar) | Üç özellik | 0,423 | 0,166 |
| Beetle (görülmemiş cevaplar) | Üç özellik | 0,539 | 0,240 |

Hedef (NFR-01): Pearson ≥ 0,70 ve QWK ≥ 0,70. Kelime tabanlı yöntem bu hedefin altında kalmaktadır; sonraki adım Sentence-BERT ile anlam benzerliğidir.

## Testler

```bash
python -m pytest
```

## Lisans

MIT
