"""Ortak veri tablosunun temizlenmesi.

Kurallar (sırasıyla uygulanır):
1. Çelişkili etiket: Aynı bölümde aynı soru ve aynı cevap farklı puanlarla geçiyorsa hepsi çıkarılır.
2. Yinelenen satır: Aynı bölümde aynı soru ve aynı cevap birden fazla geçiyorsa biri bırakılır.
3. Eğitimle aynı test cevabı: Test kümesindeki cevap, aynı sorunun eğitim kümesinde birebir varsa çıkarılır.
4. Sızan soru: "Görülmemiş sorular" test kümesinde olup eğitim kümesinde de geçen sorular çıkarılır.
"""
import pandas as pd

ANAHTAR = ["veri_seti", "bolum", "soru", "referans_cevap", "ogrenci_cevap"]


def temizle(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Temizlenmiş tabloyu ve her kuralla çıkarılan satır sayısını döndürür. Satır numaraları (index) korunur."""
    rapor = {"başlangıç": len(df)}

    celiskili = df.groupby(ANAHTAR)["puan"].transform("nunique") > 1
    df = df[~celiskili]
    rapor["çelişkili etiket"] = int(celiskili.sum())

    yinelenen = df.duplicated(ANAHTAR)
    df = df[~yinelenen]
    rapor["yinelenen satır"] = int(yinelenen.sum())

    egitim = df[df["bolum"] == "train"]
    egitim_cevap = set(zip(egitim["veri_seti"], egitim["soru"], egitim["ogrenci_cevap"]))
    egitim_soru = set(zip(egitim["veri_seti"], egitim["soru"]))
    test = df["bolum"].str.startswith("test")

    ayni_cevap = test & pd.Series([(v, s, c) in egitim_cevap for v, s, c in
                                   zip(df["veri_seti"], df["soru"], df["ogrenci_cevap"])], index=df.index)
    df = df[~ayni_cevap]
    rapor["eğitimle aynı test cevabı"] = int(ayni_cevap.sum())

    sizan = (df["bolum"] == "test_uq") & pd.Series([(v, s) in egitim_soru for v, s in
                                                    zip(df["veri_seti"], df["soru"])], index=df.index)
    df = df[~sizan]
    rapor["sızan soru (görülmemiş sorular testi)"] = int(sizan.sum())

    rapor["kalan"] = len(df)
    return df, rapor
