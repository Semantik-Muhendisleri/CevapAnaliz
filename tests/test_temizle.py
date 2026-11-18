import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.veri.temizle import temizle  # noqa: E402


def satir(bolum, soru, cevap, puan, veri_seti="beetle"):
    return {"veri_seti": veri_seti, "bolum": bolum, "soru_id": soru, "soru": soru, "referans_cevap": "ref",
            "ogrenci_cevap": cevap, "orijinal_puan": puan, "puan": puan}


def test_temizlik_kurallari():
    df = pd.DataFrame([
        satir("train", "Q1", "a", 1.0),
        satir("train", "Q1", "a", 1.0),      # yinelenen -> biri kalır
        satir("train", "Q1", "b", 1.0),
        satir("train", "Q1", "b", 0.0),      # çelişkili -> ikisi de çıkar
        satir("test_ua", "Q1", "a", 1.0),    # eğitimdeki cevabın aynısı -> çıkar
        satir("test_ua", "Q1", "c", 0.5),    # kalır
        satir("test_uq", "Q1", "d", 0.0),    # soru eğitimde var -> sızan soru, çıkar
        satir("test_uq", "Q2", "e", 1.0),    # kalır
    ])
    temiz, rapor = temizle(df)
    assert rapor["çelişkili etiket"] == 2
    assert rapor["yinelenen satır"] == 1
    assert rapor["eğitimle aynı test cevabı"] == 1
    assert rapor["sızan soru (görülmemiş sorular testi)"] == 1
    assert sorted(temiz["ogrenci_cevap"]) == ["a", "c", "e"]
    assert rapor["kalan"] == 3
