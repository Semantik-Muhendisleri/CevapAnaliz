"""İlk deney: TF-IDF tabanlı temel (baseline) puanlama.

İki yöntem denenir:
  - Yalnız kosinüs: TF-IDF kosinüs benzerliği doğrudan puan kabul edilir.
  - Üç özellik: kosinüs + n-gram örtüşmesi + uzunluk oranı, doğrusal regresyonla puana çevrilir (FR-03).

Değerlendirme:
  - Mohler: Resmi bir eğitim/test ayrımı olmadığı için soru bazlı 5 katlı çapraz doğrulama
    (modelin test edildiği sorular eğitimde hiç görülmez).
  - SciEntsBank / Beetle: Veri setinin kendi eğitim kümesinde öğrenilir, kendi test kümelerinde ölçülür.

Kullanım:
    python scripts/ortak_bicim.py      (önce bir kez)
    python scripts/ilk_deney_tfidf.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from src.puanlama.olcutler import olc  # noqa: E402
from src.puanlama.ozellikler import TfidfKosinus, ozellik_tablosu  # noqa: E402

OZELLIKLER = ["kosinus", "ngram", "uzunluk"]
QWK_SEVIYE = {"mohler": 5, "scientsbank": 2, "beetle": 2}


def egit_ve_tahmin(egitim: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Eğitim kümesinden TF-IDF sözlüğünü ve regresyonu öğrenir, test kümesi için iki tahmin döndürür."""
    kosinus = TfidfKosinus().ogren(pd.concat([egitim["referans_cevap"], egitim["ogrenci_cevap"]]))
    oz_egitim, oz_test = ozellik_tablosu(egitim, kosinus), ozellik_tablosu(test, kosinus)
    model = LinearRegression().fit(oz_egitim[OZELLIKLER], egitim["puan"])
    return pd.DataFrame({
        "yalniz_kosinus": oz_test["kosinus"],
        "uc_ozellik": np.clip(model.predict(oz_test[OZELLIKLER]), 0, 1),
    }, index=test.index)


def main() -> int:
    df = pd.read_csv(KOK / "data" / "processed" / "ortak_veri.csv")
    satirlar = []

    # Mohler: soru bazlı 5 katlı çapraz doğrulama
    mohler = df[df["veri_seti"] == "mohler"]
    tahminler = []
    for egitim_i, test_i in GroupKFold(n_splits=5).split(mohler, groups=mohler["soru_id"]):
        tahminler.append(egit_ve_tahmin(mohler.iloc[egitim_i], mohler.iloc[test_i]))
    tahmin = pd.concat(tahminler).loc[mohler.index]
    for yontem in tahmin.columns:
        satirlar.append({"veri_seti": "mohler", "test": "5 katlı çapraz doğrulama", "yontem": yontem,
                         "n": len(mohler), **olc(mohler["puan"], tahmin[yontem], QWK_SEVIYE["mohler"])})

    # SemEval-2013: kendi eğitim / test ayrımı
    for veri_seti in ["scientsbank", "beetle"]:
        alt = df[df["veri_seti"] == veri_seti]
        egitim = alt[alt["bolum"] == "train"]
        for bolum in sorted(alt["bolum"].unique()):
            if bolum == "train":
                continue
            test = alt[alt["bolum"] == bolum]
            tahmin = egit_ve_tahmin(egitim, test)
            for yontem in tahmin.columns:
                satirlar.append({"veri_seti": veri_seti, "test": bolum, "yontem": yontem, "n": len(test),
                                 **olc(test["puan"], tahmin[yontem], QWK_SEVIYE[veri_seti])})

    sonuc = pd.DataFrame(satirlar)
    klasor = KOK / "sonuclar"
    klasor.mkdir(exist_ok=True)
    sonuc.round(4).to_csv(klasor / "ilk_deney_tfidf.csv", index=False, encoding="utf-8")
    print(sonuc.round(3).to_string(index=False))
    print(f"\nKaydedildi: {(klasor / 'ilk_deney_tfidf.csv').relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
