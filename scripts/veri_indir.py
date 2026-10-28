"""Açık veri setlerini data/raw/ klasörüne indirir.

Kullanım:
    python scripts/veri_indir.py

İndirilenler:
    - Mohler (UNT Computer Science Short Answer Dataset v2.0)
    - SemEval-2013 Görev 7: SciEntsBank ve Beetle (Hugging Face, CC BY 4.0)
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
HAM = KOK / "data" / "raw"

MOHLER_URL = "https://web.eecs.umich.edu/~mihalcea/downloads/ShortAnswerGrading_v2.0.zip"
HF_URL = "https://huggingface.co/datasets/nkazi/{ad}/resolve/main/data/{dosya}.parquet"
SEMEVAL = {
    "scientsbank": ("SciEntsBank", ["train-00001", "test-ua-00001", "test-uq-00001", "test-ud-00001"]),
    "beetle": ("Beetle", ["train-00001", "test-ua-00001", "test-uq-00001"]),
}


def indir(url: str, hedef: Path) -> None:
    if hedef.exists():
        print(f"  zaten var: {hedef.relative_to(KOK)}")
        return
    hedef.parent.mkdir(parents=True, exist_ok=True)
    print(f"  indiriliyor: {url}")
    urllib.request.urlretrieve(url, hedef)


def main() -> int:
    print("Mohler")
    zip_yolu = HAM / "mohler" / "ShortAnswerGrading_v2.0.zip"
    indir(MOHLER_URL, zip_yolu)
    if not (HAM / "mohler" / "data").exists():
        with zipfile.ZipFile(zip_yolu) as z:
            z.extractall(HAM / "mohler")

    for klasor, (hf_ad, dosyalar) in SEMEVAL.items():
        print(f"SemEval-2013 / {hf_ad}")
        for dosya in dosyalar:
            indir(HF_URL.format(ad=hf_ad, dosya=dosya), HAM / "semeval2013" / klasor / f"{dosya}.parquet")

    print("Tamamlandı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
