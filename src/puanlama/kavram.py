"""NFR-03: Eksik kavram analizi.

Referans cevap kavramlara bölünür; her kavramın öğrenci cevabında anlam olarak geçip geçmediği
Sentence-BERT (MiniLM) ile bulunur. Yöntem ve eşik seçimi: notebooks/07_guven_eksik_kavram_girdi.ipynb
"""
import re

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

KORUNACAK = {"not", "no", "nor", "never", "none", "without", "more", "less", "most", "before", "after",
             "above", "below", "same", "only", "all"}
GEREKSIZ = set(ENGLISH_STOP_WORDS) - KORUNACAK
_KELIME = re.compile(r"[A-Za-z0-9çğıöşüÇĞİÖŞÜ']+")
_BOL = re.compile(r"[.;:!?]|,|\band\b|\bor\b|\bbecause\b|\bso\b", flags=re.I)
VARSAYILAN_ESIK = 0.55


def kavramlar(referans: str) -> list[str]:
    """Referans cevabı kavramlara böler. En az iki anlamlı kelime içermeyen parçalar (örneğin
    "Terminals 1, 2 and 3" listesindeki "2") bir sonraki parçayla birleştirilir."""
    parcalar = [_KELIME.findall(p) for p in _BOL.split(referans.replace("...", " "))]
    parcalar = [p for p in parcalar if p]
    anlamli = lambda p: sum(k.isalpha() and len(k) > 1 and k.lower() not in GEREKSIZ for k in p)
    sonuc, bekleyen = [], []
    for p in parcalar:
        bekleyen += p
        if anlamli(bekleyen) >= 2:
            sonuc.append(" ".join(bekleyen))
            bekleyen = []
    if bekleyen:
        if sonuc:
            sonuc[-1] += " " + " ".join(bekleyen)
        else:
            sonuc.append(" ".join(bekleyen))
    return sonuc or [referans]


def pencereler(cevap: str, uzunluk: int) -> list[str]:
    """Öğrenci cevabını, verilen kelime uzunluğunda kayan parçalara böler."""
    k = _KELIME.findall(cevap)
    if len(k) <= uzunluk:
        return [" ".join(k)]
    return [" ".join(k[i:i + uzunluk]) for i in range(len(k) - uzunluk + 1)]


def pencere_uzunlugu(kavram: str) -> int:
    return max(3, min(10, len(kavram.split()) + 2))


class KavramAnalizci:
    def __init__(self, model_adi: str = "all-MiniLM-L6-v2", esik: float = VARSAYILAN_ESIK, cihaz: str | None = None):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_adi, device=cihaz)
        self.esik = esik

    def analiz(self, referans: str, cevaplar: list[str]) -> list[list[dict]]:
        """Her cevap için [{"kavram", "benzerlik", "var"}] listesi döndürür."""
        kv = kavramlar(referans)
        kv_vektor = self.model.encode(kv, normalize_embeddings=True)
        parcalar = sorted({p for c in cevaplar for k in kv for p in pencereler(c, pencere_uzunlugu(k))})
        pv = dict(zip(parcalar, self.model.encode(parcalar, normalize_embeddings=True, batch_size=256)))
        sonuc = []
        for c in cevaplar:
            satir = []
            for k, vektor in zip(kv, kv_vektor):
                benzerlik = float(np.max(np.stack([pv[p] for p in pencereler(c, pencere_uzunlugu(k))]) @ vektor))
                satir.append({"kavram": k, "benzerlik": round(benzerlik, 3), "var": benzerlik >= self.esik})
            sonuc.append(satir)
        return sonuc
