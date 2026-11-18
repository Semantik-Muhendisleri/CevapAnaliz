"""Puanlama servisi (FastAPI).

Çalıştırma (proje klasöründe):
    uvicorn src.api.main:app --reload
Belgeler: http://127.0.0.1:8000/docs

Ortam değişkenleri:
    CEVAPANALIZ_MODEL  ince ayarlı model klasörü (varsayılan: modeller/ince_ayar_v1)
    CEVAPANALIZ_DB     SQLite dosyası (varsayılan: data/cevapanaliz.db)
"""
import os
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from src.puanlama.servis import toplu_puanla
from src.veritabani.db import Veritabani

KOK = Path(__file__).resolve().parents[2]
app = FastAPI(title="CevapAnaliz Puanlama Servisi", version="0.7")


@lru_cache
def vt_al() -> Veritabani:
    yol = Path(os.environ.get("CEVAPANALIZ_DB", KOK / "data" / "cevapanaliz.db"))
    yol.parent.mkdir(parents=True, exist_ok=True)
    return Veritabani(yol)


@lru_cache
def puanlayici_al():
    from src.puanlama.puanlayici import CevapPuanlayici
    return CevapPuanlayici(os.environ.get("CEVAPANALIZ_MODEL", KOK / "modeller" / "ince_ayar_v1"))


class SoruGirdisi(BaseModel):
    soru_no: str = Field(min_length=1)
    soru: str = Field(min_length=1)
    referans: str = Field(min_length=1)


class PuanlaGirdisi(BaseModel):
    cevap: str
    soru_no: str | None = None      # kayıtlı bir soru için
    soru: str | None = None         # ya da soru ve referans doğrudan verilir
    referans: str | None = None


@app.get("/saglik")
def saglik(puanlayici=Depends(puanlayici_al)):
    return {"durum": "çalışıyor", "model": "ince ayarlı" if puanlayici.ince_ayarli else "hazır model (demo modu)"}


@app.post("/sorular", status_code=201)
def soru_ekle(girdi: SoruGirdisi, vt: Veritabani = Depends(vt_al)):
    vt.soru_ekle(girdi.soru_no, girdi.soru, girdi.referans)
    return vt.soru(girdi.soru_no.strip())


@app.get("/sorular")
def sorular(vt: Veritabani = Depends(vt_al)):
    return vt.sorular()


@app.post("/puanla")
def puanla(girdi: PuanlaGirdisi, vt: Veritabani = Depends(vt_al), puanlayici=Depends(puanlayici_al)):
    if not girdi.cevap.strip():
        raise HTTPException(422, "Cevap boş; puanlanamaz.")                     # FR-06
    if girdi.soru_no:
        s = vt.soru(girdi.soru_no)
        if s is None:
            raise HTTPException(404, f"'{girdi.soru_no}' numaralı soru sistemde kayıtlı değil.")
        soru, referans = s["soru"], s["referans"]
    elif girdi.referans:
        soru, referans = girdi.soru, girdi.referans
    else:
        raise HTTPException(422, "soru_no ya da referans verilmeli.")
    return puanlayici.puanla(referans, [girdi.cevap.strip()], soru=soru)[0]


@app.post("/toplu")
async def toplu(dosya: UploadFile = File(...), vt: Veritabani = Depends(vt_al), puanlayici=Depends(puanlayici_al)):
    sonuc = toplu_puanla(vt, puanlayici, await dosya.read(), dosya.filename or "")
    if sonuc["dosya_hatasi"]:
        raise HTTPException(400, sonuc["dosya_hatasi"])
    return sonuc


@app.get("/sonuclar")
def sonuclar(ogrenci_no: str | None = None, soru_no: str | None = None, sadece_inceleme: bool = False,
             en_az: float | None = Query(None, ge=0, le=5), en_cok: float | None = Query(None, ge=0, le=5),
             vt: Veritabani = Depends(vt_al)):
    return vt.sonuclar(ogrenci_no, soru_no, sadece_inceleme, en_az, en_cok)
