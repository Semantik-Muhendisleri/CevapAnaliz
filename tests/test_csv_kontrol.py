"""2. hafta test planındaki girdi kontrolü testi: boş cevap, eksik sütun, hatalı dosya biçimi ve geçerli CSV."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.girdi.csv_kontrol import csv_kontrol  # noqa: E402

SORULAR = {"S1", "S2"}


def kontrol(metin, ad="cevaplar.csv", kodlama="utf-8"):
    return csv_kontrol(metin.encode(kodlama), ad, SORULAR)


def test_gecerli_csv():
    s = kontrol("ogrenci_no,soru_no,cevap\n101,S1,Bir prototip yazılımın bir kısmını taklit eder.\n102,S2,Soyutlama.\n")
    assert s.basarili and not s.hatalar
    assert len(s.gecerli) == 2


def test_bos_cevap_puanlanmaz_ve_mesaj_verilir():
    s = kontrol("ogrenci_no,soru_no,cevap\n101,S1,\n102,S1,Geçerli cevap\n")
    assert s.basarili
    assert list(s.gecerli["ogrenci_no"]) == ["102"]
    assert s.hatalar == [{"satir": 2, "sutun": "cevap", "mesaj": "Cevap boş; bu satır puanlanmayacak."}]


def test_eksik_sutun_dosyayi_reddeder():
    s = kontrol("ogrenci_no,cevap\n101,Cevap\n")
    assert not s.basarili and "soru_no" in s.dosya_hatasi


def test_hatali_dosya_bicimi():
    assert not kontrol("ogrenci_no,soru_no,cevap\n", ad="cevaplar.xlsx").basarili
    assert not kontrol("", ad="cevaplar.csv").basarili


def test_kayitli_olmayan_soru_ve_yinelenen_satir():
    s = kontrol("ogrenci_no,soru_no,cevap\n101,S9,Cevap\n102,S1,Cevap\n102,S1,Tekrar\n")
    assert len(s.gecerli) == 1
    assert {h["satir"] for h in s.hatalar} == {2, 4}


def test_noktali_virgul_ve_turkce_excel_kodlamasi():
    s = kontrol("ogrenci_no;soru_no;cevap\n101;S1;Işık enerjisi kimyasal enerjiye dönüşür\n", kodlama="cp1254")
    assert s.basarili and len(s.gecerli) == 1
    assert s.gecerli.loc[0, "cevap"].startswith("Işık")
