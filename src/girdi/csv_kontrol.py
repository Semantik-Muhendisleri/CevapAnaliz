"""FR-06: Öğretmenin yüklediği CSV dosyasının puanlamadan önce kontrol edilmesi.

Kabul kriteri: Boş cevaplar puanlamaya alınmaz ve kullanıcıya hata mesajı gösterilir.
NFR-06: Hatalı satırlar dosyanın geri kalanının puanlanmasını engellemez.

Beklenen sütunlar: ogrenci_no, soru_no, cevap
"""
import csv
import io
from dataclasses import dataclass, field

import pandas as pd

ZORUNLU_SUTUNLAR = ["ogrenci_no", "soru_no", "cevap"]
EN_BUYUK_BOYUT = 5 * 1024 * 1024  # 5 MB
KODLAMALAR = ["utf-8-sig", "cp1254"]  # Excel'in Türkçe Windows'ta kaydettiği dosyalar cp1254 olabilir


@dataclass
class KontrolSonucu:
    gecerli: pd.DataFrame                       # puanlamaya gönderilecek satırlar
    hatalar: list[dict] = field(default_factory=list)   # {"satir": .., "sutun": .., "mesaj": ..}
    dosya_hatasi: str | None = None             # dosyanın tamamını reddettiren hata

    @property
    def basarili(self) -> bool:
        return self.dosya_hatasi is None


def _bos_sonuc(mesaj: str) -> KontrolSonucu:
    return KontrolSonucu(gecerli=pd.DataFrame(columns=ZORUNLU_SUTUNLAR), dosya_hatasi=mesaj)


def _coz(icerik: bytes) -> str | None:
    for kodlama in KODLAMALAR:
        try:
            return icerik.decode(kodlama)
        except UnicodeDecodeError:
            continue
    return None


def csv_kontrol(icerik: bytes, dosya_adi: str, kayitli_sorular: set[str]) -> KontrolSonucu:
    """Yüklenen dosyayı kontrol eder; geçerli satırları ve satır satır hata listesini döndürür.

    Satır numaraları, öğretmenin dosyayı Excel'de açtığında göreceği numaralardır (başlık = 1. satır).
    """
    if not dosya_adi.lower().endswith(".csv"):
        return _bos_sonuc("Dosya CSV biçiminde değil. Lütfen .csv uzantılı bir dosya yükleyin.")
    if len(icerik) == 0:
        return _bos_sonuc("Dosya boş.")
    if len(icerik) > EN_BUYUK_BOYUT:
        return _bos_sonuc("Dosya 5 MB'tan büyük. Lütfen dosyayı bölerek yükleyin.")

    metin = _coz(icerik)
    if metin is None:
        return _bos_sonuc("Dosyanın karakter kodlaması okunamadı. Dosyayı 'CSV UTF-8' olarak kaydedin.")

    try:
        ayirici = csv.Sniffer().sniff(metin.splitlines()[0], delimiters=",;\t").delimiter
    except csv.Error:
        ayirici = ","
    try:
        df = pd.read_csv(io.StringIO(metin), sep=ayirici, dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as hata:
        return _bos_sonuc(f"Dosya okunamadı: {hata}")

    df.columns = [s.strip().lower() for s in df.columns]
    eksik = [s for s in ZORUNLU_SUTUNLAR if s not in df.columns]
    if eksik:
        return _bos_sonuc(f"Eksik sütun: {', '.join(eksik)}. Beklenen sütunlar: {', '.join(ZORUNLU_SUTUNLAR)}.")
    if df.empty:
        return _bos_sonuc("Dosyada başlık satırı dışında hiç satır yok.")

    df = df[ZORUNLU_SUTUNLAR].apply(lambda s: s.str.strip())
    hatalar, gecerli_mi = [], []
    gorulen = set()
    for i, satir in enumerate(df.itertuples(index=False), start=2):
        sorunlar = []
        if not satir.ogrenci_no:
            sorunlar.append(("ogrenci_no", "Öğrenci numarası boş."))
        if not satir.soru_no:
            sorunlar.append(("soru_no", "Soru numarası boş."))
        elif satir.soru_no not in kayitli_sorular:
            sorunlar.append(("soru_no", f"'{satir.soru_no}' numaralı soru sistemde kayıtlı değil."))
        if not satir.cevap:
            sorunlar.append(("cevap", "Cevap boş; bu satır puanlanmayacak."))
        if not sorunlar and (satir.ogrenci_no, satir.soru_no) in gorulen:
            sorunlar.append(("ogrenci_no", "Bu öğrencinin bu soruya cevabı dosyada birden fazla kez var; "
                                           "yalnızca ilki puanlanacak."))
        gorulen.add((satir.ogrenci_no, satir.soru_no))
        hatalar += [{"satir": i, "sutun": s, "mesaj": m} for s, m in sorunlar]
        gecerli_mi.append(not sorunlar)

    return KontrolSonucu(gecerli=df[gecerli_mi].reset_index(drop=True), hatalar=hatalar)
