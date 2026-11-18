"""SQLite veritabanı (3. hafta tasarımının ilk sürümü): sorular ve puanlama sonuçları.

Kullanıcı ve puan düzeltme geçmişi tabloları sonraki haftalarda eklenecek.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

SEMA = """
CREATE TABLE IF NOT EXISTS soru (
    soru_no      TEXT PRIMARY KEY,
    soru         TEXT NOT NULL,
    referans     TEXT NOT NULL,
    eklenme      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sonuc (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ogrenci_no       TEXT NOT NULL,
    soru_no          TEXT NOT NULL REFERENCES soru(soru_no),
    cevap            TEXT NOT NULL,
    puan             REAL NOT NULL,
    puan_5           REAL NOT NULL,
    belirsizlik      REAL NOT NULL,
    inceleme_gerekli INTEGER NOT NULL,
    eksik_kavramlar  TEXT NOT NULL,
    tarih            TEXT NOT NULL
);
"""


class Veritabani:
    def __init__(self, yol: str | Path):
        self.baglanti = sqlite3.connect(str(yol), check_same_thread=False)
        self.baglanti.row_factory = sqlite3.Row
        self.baglanti.executescript(SEMA)

    def soru_ekle(self, soru_no: str, soru: str, referans: str) -> None:
        """FR-01: Soru ve referans cevabı kaydeder; aynı numaralı soru varsa günceller."""
        with self.baglanti:
            self.baglanti.execute(
                "INSERT INTO soru VALUES (?, ?, ?, ?) ON CONFLICT(soru_no) DO UPDATE SET soru=excluded.soru, "
                "referans=excluded.referans", (soru_no.strip(), soru.strip(), referans.strip(),
                                               datetime.now().isoformat(timespec="seconds")))

    def sorular(self) -> list[dict]:
        return [dict(r) for r in self.baglanti.execute("SELECT * FROM soru ORDER BY soru_no")]

    def soru(self, soru_no: str) -> dict | None:
        r = self.baglanti.execute("SELECT * FROM soru WHERE soru_no = ?", (soru_no,)).fetchone()
        return dict(r) if r else None

    def sonuc_ekle(self, kayitlar: list[dict]) -> None:
        zaman = datetime.now().isoformat(timespec="seconds")
        with self.baglanti:
            self.baglanti.executemany(
                "INSERT INTO sonuc (ogrenci_no, soru_no, cevap, puan, puan_5, belirsizlik, inceleme_gerekli, "
                "eksik_kavramlar, tarih) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(k["ogrenci_no"], k["soru_no"], k["cevap"], k["puan"], k["puan_5"], k["belirsizlik"],
                  int(k["inceleme_gerekli"]), json.dumps(k["eksik_kavramlar"], ensure_ascii=False), zaman)
                 for k in kayitlar])

    def sonuclar(self, ogrenci_no: str | None = None, soru_no: str | None = None,
                 sadece_inceleme: bool = False, en_az: float | None = None, en_cok: float | None = None) -> list[dict]:
        """FR-07 / FR-08: Sonuçları öğrenciye, soruya, inceleme durumuna ve puan aralığına (0-5) göre filtreler."""
        kosul, deger = [], []
        for alan, v in [("ogrenci_no", ogrenci_no), ("soru_no", soru_no)]:
            if v:
                kosul.append(f"{alan} = ?"); deger.append(v)
        if sadece_inceleme:
            kosul.append("inceleme_gerekli = 1")
        if en_az is not None:
            kosul.append("puan_5 >= ?"); deger.append(en_az)
        if en_cok is not None:
            kosul.append("puan_5 <= ?"); deger.append(en_cok)
        sorgu = "SELECT * FROM sonuc" + (" WHERE " + " AND ".join(kosul) if kosul else "") + " ORDER BY id"
        sonuc = []
        for r in self.baglanti.execute(sorgu, deger):
            d = dict(r)
            d["inceleme_gerekli"] = bool(d["inceleme_gerekli"])
            d["eksik_kavramlar"] = json.loads(d["eksik_kavramlar"])
            sonuc.append(d)
        return sonuc
