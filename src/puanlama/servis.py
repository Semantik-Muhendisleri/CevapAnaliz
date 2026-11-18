"""API ile arayüzün ortak kullandığı iş akışı: CSV kontrolü → puanlama → kayıt."""
from src.girdi.csv_kontrol import csv_kontrol


def toplu_puanla(vt, puanlayici, icerik: bytes, dosya_adi: str) -> dict:
    """FR-02: CSV ile gelen cevapları kontrol eder (FR-06), puanlar ve veritabanına kaydeder.

    Dönen sözlük: {"dosya_hatasi": str | None, "sonuclar": [...], "uyarilar": [...]}
    """
    sorular = {s["soru_no"]: s for s in vt.sorular()}
    kontrol = csv_kontrol(icerik, dosya_adi, set(sorular))
    if not kontrol.basarili:
        return {"dosya_hatasi": kontrol.dosya_hatasi, "sonuclar": [], "uyarilar": []}

    kayitlar = []
    for soru_no, grup in kontrol.gecerli.groupby("soru_no", sort=False):
        s = sorular[soru_no]
        puanlar = puanlayici.puanla(s["referans"], list(grup["cevap"]), soru=s["soru"])
        for satir, sonuc in zip(grup.itertuples(index=False), puanlar):
            kayitlar.append({"ogrenci_no": satir.ogrenci_no, "soru_no": soru_no, "cevap": satir.cevap, **sonuc})
    vt.sonuc_ekle(kayitlar)
    return {"dosya_hatasi": None, "sonuclar": kayitlar, "uyarilar": kontrol.hatalar}
