"""Tek puanlama modülü: ince ayarlı çapraz kodlayıcıyla puan, belirsizlik (FR-04) ve eksik kavramlar (NFR-03).

Model klasöründe Hugging Face model dosyalarının yanında isteğe bağlı bir `ayar.json` bulunabilir:
    {"soru_ekle": false, "guven_esigi": 0.06, "kavram_esigi": 0.55}
Bu dosya notebooks/08_soru_esik_son_model.ipynb tarafından yazılır.
"""
import json
from pathlib import Path

import numpy as np

from src.puanlama.kavram import VARSAYILAN_ESIK, KavramAnalizci

HAZIR_MODEL = "cross-encoder/stsb-distilroberta-base"   # ince ayar yapılmamış yedek model (demo modu)


class CevapPuanlayici:
    def __init__(self, model_yolu: str | Path | None = None, cihaz: str | None = None, mc_tur: int = 10,
                 kavram_analizi: bool = True):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.cihaz = cihaz or ("cuda" if torch.cuda.is_available() else "cpu")
        yol = Path(model_yolu) if model_yolu else None
        self.ince_ayarli = bool(yol and (yol / "config.json").exists())
        kaynak = str(yol) if self.ince_ayarli else HAZIR_MODEL
        ayar = json.loads((yol / "ayar.json").read_text(encoding="utf-8")) if self.ince_ayarli and (yol / "ayar.json").exists() else {}

        self.tokenizer = AutoTokenizer.from_pretrained(kaynak)
        self.model = AutoModelForSequenceClassification.from_pretrained(kaynak).to(self.cihaz).eval()
        self.soru_ekle = bool(ayar.get("soru_ekle", False))
        self.guven_esigi = ayar.get("guven_esigi")          # None ise hiçbir cevap işaretlenmez
        self.mc_tur = mc_tur
        self.kavram = KavramAnalizci(esik=ayar.get("kavram_esigi", VARSAYILAN_ESIK), cihaz=self.cihaz) \
            if kavram_analizi else None

    def _girdi(self, soru, referans):
        return f"{soru} {referans}" if self.soru_ekle and soru else referans

    def _puanla(self, birinci, cevaplar):
        torch = self.torch
        sonuc = []
        with torch.no_grad():
            for i in range(0, len(cevaplar), 64):
                g = self.tokenizer(birinci[i:i + 64], cevaplar[i:i + 64], truncation=True, max_length=160,
                                   padding=True, return_tensors="pt").to(self.cihaz)
                sonuc.append(torch.sigmoid(self.model(**g).logits.squeeze(-1).float()).cpu().numpy())
        return np.concatenate(sonuc)

    def puanla(self, referans: str, cevaplar: list[str], soru: str | None = None) -> list[dict]:
        """Aynı soruya verilmiş cevapları puanlar. Puan 0-1 aralığında; `puan_5` öğretmene gösterilecek 0-5 puanıdır."""
        if not cevaplar:
            return []
        birinci = [self._girdi(soru, referans)] * len(cevaplar)
        self.model.eval()
        puan = self._puanla(birinci, cevaplar)
        self.model.train()                                   # Monte Carlo dropout: dropout açık
        self.torch.manual_seed(0)
        belirsizlik = np.stack([self._puanla(birinci, cevaplar) for _ in range(self.mc_tur)]).std(axis=0)
        self.model.eval()
        kavramlar = self.kavram.analiz(referans, cevaplar) if self.kavram else [[] for _ in cevaplar]
        return [{
            "puan": round(float(p), 3),
            "puan_5": round(float(p) * 5 * 2) / 2,           # yarım puan hassasiyetinde
            "belirsizlik": round(float(b), 4),
            "inceleme_gerekli": bool(self.guven_esigi is not None and b >= self.guven_esigi),
            "kavramlar": k,
            "eksik_kavramlar": [x["kavram"] for x in k if not x["var"]],
        } for p, b, k in zip(puan, belirsizlik, kavramlar)]
