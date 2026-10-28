"""data/raw altındaki veri setlerini ortak biçime çevirip data/processed/ortak_veri.csv dosyasına yazar.

Kullanım:
    python scripts/ortak_bicim.py
"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from src.veri.donustur import hepsini_yukle  # noqa: E402


def main() -> int:
    df = hepsini_yukle(KOK / "data" / "raw")
    cikti = KOK / "data" / "processed" / "ortak_veri.csv"
    cikti.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cikti, index=False, encoding="utf-8")

    print(f"Yazıldı: {cikti.relative_to(KOK)}  ({len(df)} satır)\n")
    ozet = df.groupby(["veri_seti", "bolum"]).agg(
        cevap=("ogrenci_cevap", "size"), soru=("soru_id", "nunique"), ort_puan=("puan", "mean"))
    print(ozet.round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
