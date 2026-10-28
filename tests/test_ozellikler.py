import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.puanlama.olcutler import olc  # noqa: E402
from src.puanlama.ozellikler import TfidfKosinus, ngram_ortusme, uzunluk_orani  # noqa: E402
from src.veri.donustur import SEMEVAL_ETIKETLER, _temizle  # noqa: E402

REF = "A prototype simulates the behaviour of portions of the software product."


def test_ayni_cevap_tam_ortusme():
    assert ngram_ortusme(REF, REF) == pytest.approx(1.0)


def test_bos_cevap_sifir():
    assert ngram_ortusme(REF, "") == 0.0
    assert uzunluk_orani(REF, "") == 0.0


def test_uzunluk_orani_ust_sinir():
    assert uzunluk_orani("short answer", " ".join(["word"] * 100)) == 3.0


def test_kosinus_ayni_metin_bir():
    k = TfidfKosinus().ogren([REF, "Abstraction and reusability."])
    assert k.benzerlik([REF], [REF])[0] == pytest.approx(1.0)
    assert k.benzerlik([REF], ["Abstraction and reusability."])[0] == pytest.approx(0.0, abs=0.2)


def test_html_temizligi():
    assert _temizle("first line.<br><br>second   line ") == "first line. second line"


def test_semeval_puan_karsiliklari():
    puanlar = {ad: puan for ad, puan in SEMEVAL_ETIKETLER.values()}
    assert puanlar["correct"] == 1.0
    assert puanlar["partially_correct_incomplete"] == 0.5
    assert puanlar["contradictory"] == puanlar["irrelevant"] == puanlar["non_domain"] == 0.0


def test_olcutler_mukemmel_tahmin():
    gercek = [0.0, 0.2, 0.5, 0.7, 1.0]
    sonuc = olc(gercek, gercek, seviye=5)
    assert sonuc["pearson"] == pytest.approx(1.0)
    assert sonuc["qwk"] == pytest.approx(1.0)
    assert sonuc["mae"] == pytest.approx(0.0)
