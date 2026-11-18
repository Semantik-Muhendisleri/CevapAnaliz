"""Puanlama servisi testleri. Gerçek model yerine sahte bir puanlayıcı kullanılır."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import app, puanlayici_al, vt_al  # noqa: E402
from src.puanlama.kavram import kavramlar  # noqa: E402
from src.veritabani.db import Veritabani  # noqa: E402


class SahtePuanlayici:
    ince_ayarli = True

    def puanla(self, referans, cevaplar, soru=None):
        # Referansla ortak kelime oranını puan sayar; belirsizliği kısa cevaplarda yüksek verir.
        ref = set(referans.lower().split())
        sonuc = []
        for c in cevaplar:
            p = len(ref & set(c.lower().split())) / max(1, len(ref))
            b = 0.2 if len(c.split()) < 3 else 0.01
            sonuc.append({"puan": p, "puan_5": round(p * 10) / 2, "belirsizlik": b, "inceleme_gerekli": b > 0.1,
                          "kavramlar": [], "eksik_kavramlar": [] if p > 0.5 else [referans]})
        return sonuc


@pytest.fixture
def istemci(tmp_path):
    vt = Veritabani(tmp_path / "test.db")
    app.dependency_overrides[vt_al] = lambda: vt
    app.dependency_overrides[puanlayici_al] = lambda: SahtePuanlayici()
    yield TestClient(app)
    app.dependency_overrides.clear()


def soru_ekle(istemci):
    r = istemci.post("/sorular", json={"soru_no": "S1", "soru": "What is a prototype?",
                                       "referans": "a prototype simulates the software"})
    assert r.status_code == 201


def test_saglik(istemci):
    assert istemci.get("/saglik").json()["model"] == "ince ayarlı"


def test_tek_cevap_puanlama(istemci):
    soru_ekle(istemci)
    r = istemci.post("/puanla", json={"soru_no": "S1", "cevap": "a prototype simulates the software"})
    assert r.status_code == 200 and r.json()["puan"] == 1.0
    assert istemci.post("/puanla", json={"soru_no": "S9", "cevap": "x"}).status_code == 404
    assert istemci.post("/puanla", json={"soru_no": "S1", "cevap": "   "}).status_code == 422


def test_toplu_puanlama_hatali_satirlari_atlar_ve_kaydeder(istemci):
    soru_ekle(istemci)
    csv = "ogrenci_no,soru_no,cevap\n101,S1,a prototype simulates the software\n102,S1,\n103,S1,no idea\n"
    r = istemci.post("/toplu", files={"dosya": ("cevaplar.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200
    govde = r.json()
    assert [s["ogrenci_no"] for s in govde["sonuclar"]] == ["101", "103"]
    assert govde["uyarilar"][0]["satir"] == 3
    assert len(istemci.get("/sonuclar").json()) == 2
    assert [s["ogrenci_no"] for s in istemci.get("/sonuclar", params={"sadece_inceleme": True}).json()] == ["103"]
    assert [s["ogrenci_no"] for s in istemci.get("/sonuclar", params={"ogrenci_no": "101"}).json()] == ["101"]


def test_toplu_puanlama_hatali_dosya(istemci):
    r = istemci.post("/toplu", files={"dosya": ("cevaplar.xlsx", b"...", "application/octet-stream")})
    assert r.status_code == 400 and "CSV" in r.json()["detail"]


def test_kavramlara_bolme():
    assert kavramlar("Terminals 1, 2 and 3 are connected to the negative battery terminal") == \
        ["Terminals 1 2 3 are connected to the negative battery terminal"]
    assert len(kavramlar("The harder mineral will leave a scratch on the less hard mineral. "
                         "If the black mineral is harder, the brown mineral will have a scratch.")) == 3
