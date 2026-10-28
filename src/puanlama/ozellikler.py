"""FR-03: Puanın hesaplandığı üç özellik.

1. Kosinüs benzerliği (TF-IDF vektörleri arasında)
2. N-gram örtüşmesi (referanstaki 1'li ve 2'li kelime gruplarından kaçı öğrenci cevabında geçiyor)
3. Uzunluk oranı (öğrenci cevabı kelime sayısı / referans cevap kelime sayısı)
"""
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

_KELIME_RE = re.compile(r"[a-z0-9çğıöşü]+")
UZUNLUK_UST_SINIR = 3.0  # Çok uzun cevapların oranı aşırı büyümesin diye üst sınır


def kelimeler(metin: str) -> list[str]:
    return _KELIME_RE.findall(metin.lower())


def ngramlar(tokenlar: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokenlar[i:i + n]) for i in range(len(tokenlar) - n + 1)}


def ngram_ortusme(referans: str, cevap: str) -> float:
    """Referanstaki 1-gram ve 2-gramların öğrenci cevabında geçme oranı (0-1)."""
    ref, cvp = kelimeler(referans), kelimeler(cevap)
    ref_ng = ngramlar(ref, 1) | ngramlar(ref, 2)
    if not ref_ng:
        return 0.0
    cvp_ng = ngramlar(cvp, 1) | ngramlar(cvp, 2)
    return len(ref_ng & cvp_ng) / len(ref_ng)


def uzunluk_orani(referans: str, cevap: str) -> float:
    ref_uz = len(kelimeler(referans))
    if ref_uz == 0:
        return 0.0
    return min(len(kelimeler(cevap)) / ref_uz, UZUNLUK_UST_SINIR)


class TfidfKosinus:
    """TF-IDF sözlüğünü eğitim verisinden öğrenir, sonra referans-cevap çiftlerinin kosinüs benzerliğini verir."""

    def __init__(self):
        self.vektorlestirici = TfidfVectorizer(lowercase=True, sublinear_tf=True)

    def ogren(self, metinler) -> "TfidfKosinus":
        self.vektorlestirici.fit(metinler)
        return self

    def benzerlik(self, referanslar, cevaplar) -> np.ndarray:
        r = self.vektorlestirici.transform(referanslar)
        c = self.vektorlestirici.transform(cevaplar)
        # TF-IDF vektörleri birim uzunlukta olduğu için nokta çarpım = kosinüs benzerliği
        return np.asarray(r.multiply(c).sum(axis=1)).ravel()


def ozellik_tablosu(df: pd.DataFrame, kosinus: TfidfKosinus) -> pd.DataFrame:
    """Ortak biçimdeki her satır için üç özelliği hesaplar."""
    return pd.DataFrame({
        "kosinus": kosinus.benzerlik(df["referans_cevap"], df["ogrenci_cevap"]),
        "ngram": [ngram_ortusme(r, c) for r, c in zip(df["referans_cevap"], df["ogrenci_cevap"])],
        "uzunluk": [uzunluk_orani(r, c) for r, c in zip(df["referans_cevap"], df["ogrenci_cevap"])],
    }, index=df.index)
