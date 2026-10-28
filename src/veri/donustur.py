"""Veri setlerini 3. hafta raporunda tasarlanan ortak biçime dönüştürür.

Ortak biçimin sütunları:
    veri_seti, bolum, soru_id, soru, referans_cevap, ogrenci_cevap, orijinal_puan, puan

- bolum: veri setinin kendi eğitim/test ayrımı (Mohler'de resmi ayrım olmadığı için "tum").
- orijinal_puan: veri setindeki puan ya da etiket, olduğu gibi.
- puan: 0-1 aralığına çevrilmiş puan.
"""
import re
from pathlib import Path

import pandas as pd

SUTUNLAR = ["veri_seti", "bolum", "soru_id", "soru", "referans_cevap",
            "ogrenci_cevap", "orijinal_puan", "puan"]

# SemEval-2013 5'li etiketleri (Hugging Face sırası) ve 0-1 puan karşılıkları:
# doğru = 1, kısmen doğru = 0,5, yanlış/çelişkili/alakasız/alan dışı = 0
SEMEVAL_ETIKETLER = {
    0: ("correct", 1.0),
    1: ("contradictory", 0.0),
    2: ("partially_correct_incomplete", 0.5),
    3: ("irrelevant", 0.0),
    4: ("non_domain", 0.0),
}

_ETIKET_RE = re.compile(r"<[^>]+>")
_BOSLUK_RE = re.compile(r"\s+")


def _temizle(metin: str) -> str:
    """HTML etiketlerini (<br> vb.) ve fazla boşlukları kaldırır."""
    return _BOSLUK_RE.sub(" ", _ETIKET_RE.sub(" ", metin)).strip()


def _satirlari_oku(yol: Path) -> list[str]:
    # Mohler dosyalarında birkaç ASCII dışı karakter var; okunamayanları atla.
    return [s for s in yol.read_text(encoding="utf-8", errors="replace").splitlines() if s.strip()]


def _id_ve_metin(satir: str) -> tuple[str, str]:
    soru_id, _, metin = satir.partition(" ")
    return soru_id, _temizle(metin)


def mohler_yukle(kok: Path) -> pd.DataFrame:
    """Mohler veri setini yükler. kok: .../data/raw/mohler/data"""
    sorular = dict(_id_ve_metin(s) for s in _satirlari_oku(kok / "raw" / "questions"))
    referanslar = dict(_id_ve_metin(s) for s in _satirlari_oku(kok / "raw" / "answers"))
    # '#' ile başlayan sorular, yazarların da kullanmadığı seçmeli/sıralamalı sorulardır.
    soru_idler = [s for s in _satirlari_oku(kok / "docs" / "files") if not s.startswith("#")]

    kayitlar = []
    for soru_id in soru_idler:
        cevaplar = [_id_ve_metin(s)[1] for s in _satirlari_oku(kok / "raw" / soru_id)]
        puanlar = [float(s) for s in _satirlari_oku(kok / "scores" / soru_id / "ave")]
        if len(cevaplar) != len(puanlar):
            raise ValueError(f"Mohler {soru_id}: {len(cevaplar)} cevap, {len(puanlar)} puan")
        for cevap, puan in zip(cevaplar, puanlar):
            kayitlar.append({
                "veri_seti": "mohler", "bolum": "tum", "soru_id": f"mohler-{soru_id}",
                "soru": sorular[soru_id], "referans_cevap": referanslar[soru_id],
                "ogrenci_cevap": cevap, "orijinal_puan": puan, "puan": puan / 5.0,
            })
    return pd.DataFrame(kayitlar, columns=SUTUNLAR)


def semeval_yukle(klasor: Path, veri_seti: str) -> pd.DataFrame:
    """SciEntsBank veya Beetle parquet dosyalarını yükler."""
    parcalar = []
    dosyalar = sorted(klasor.glob("train-*.parquet")) + sorted(klasor.glob("test-*.parquet"))
    for dosya in dosyalar:
        bolum = dosya.stem.rsplit("-", 1)[0].replace("-", "_")  # train-00001 -> train, test-ua-00001 -> test_ua
        df = pd.read_parquet(dosya)
        df["bolum"] = bolum
        parcalar.append(df)
    df = pd.concat(parcalar, ignore_index=True)

    # Aynı soru metni = aynı soru. Soru numarasını soru metninden üretiyoruz.
    soru_no = {soru: i for i, soru in enumerate(sorted(df["question"].unique()), 1)}
    return pd.DataFrame({
        "veri_seti": veri_seti,
        "bolum": df["bolum"],
        "soru_id": df["question"].map(lambda q: f"{veri_seti}-{soru_no[q]}"),
        "soru": df["question"].map(_temizle),
        "referans_cevap": df["reference_answer"].map(_temizle),
        "ogrenci_cevap": df["student_answer"].map(_temizle),
        "orijinal_puan": df["label"].map(lambda e: SEMEVAL_ETIKETLER[e][0]),
        "puan": df["label"].map(lambda e: SEMEVAL_ETIKETLER[e][1]),
    }, columns=SUTUNLAR)


def hepsini_yukle(ham: Path) -> pd.DataFrame:
    """data/raw altındaki tüm veri setlerini tek tabloda birleştirir."""
    return pd.concat([
        mohler_yukle(ham / "mohler" / "data"),
        semeval_yukle(ham / "semeval2013" / "scientsbank", "scientsbank"),
        semeval_yukle(ham / "semeval2013" / "beetle", "beetle"),
    ], ignore_index=True)
