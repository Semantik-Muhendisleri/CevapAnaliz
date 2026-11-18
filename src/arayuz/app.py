"""CevapAnaliz web arayüzü (Streamlit) – ilk ekranlar.

Çalıştırma (proje klasöründe):
    streamlit run src/arayuz/app.py

İnce ayarlı model `modeller/ince_ayar_v1` klasöründe (ya da CEVAPANALIZ_MODEL ortam değişkeninin gösterdiği yerde)
yoksa, ince ayar yapılmamış hazır model kullanılır ve ekranda "demo modu" uyarısı gösterilir.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from src.puanlama.servis import toplu_puanla  # noqa: E402
from src.veritabani.db import Veritabani  # noqa: E402

st.set_page_config(page_title="CevapAnaliz", page_icon="📝", layout="wide")


@st.cache_resource
def vt_al():
    yol = Path(os.environ.get("CEVAPANALIZ_DB", KOK / "data" / "cevapanaliz.db"))
    yol.parent.mkdir(parents=True, exist_ok=True)
    return Veritabani(yol)


@st.cache_resource(show_spinner="Model yükleniyor…")
def puanlayici_al():
    from src.puanlama.puanlayici import CevapPuanlayici
    return CevapPuanlayici(os.environ.get("CEVAPANALIZ_MODEL", KOK / "modeller" / "ince_ayar_v1"))


def sonuc_tablosu(kayitlar: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(kayitlar)
    if df.empty:
        return df
    df["inceleme"] = df["inceleme_gerekli"].map({True: "⚠️ öğretmen incelemesi gerekli", False: ""})
    df["eksik kavramlar"] = df["eksik_kavramlar"].map(lambda k: " · ".join(k) if k else "—")
    return df[["ogrenci_no", "soru_no", "cevap", "puan_5", "inceleme", "eksik kavramlar", "belirsizlik"]].rename(
        columns={"ogrenci_no": "öğrenci no", "soru_no": "soru no", "puan_5": "puan (0–5)"})


vt = vt_al()
puanlayici = puanlayici_al()

st.sidebar.title("📝 CevapAnaliz")
rol = st.sidebar.radio("Rol", ["Öğretmen", "Öğrenci"])
if rol == "Öğretmen":
    sayfa = st.sidebar.radio("Sayfa", ["Sorular", "CSV yükle ve puanla", "Sonuçlar"])
else:
    sayfa = "Sonuçlarım"
st.sidebar.caption("Model: " + ("ince ayarlı çapraz kodlayıcı" if puanlayici.ince_ayarli
                                else "⚠️ demo modu (ince ayar yapılmamış hazır model)"))

# ------------------------------------------------------------------ Öğretmen: Sorular (FR-01)
if sayfa == "Sorular":
    st.header("Sorular")
    with st.form("soru_ekle", clear_on_submit=True):
        st.subheader("Yeni soru ekle")
        soru_no = st.text_input("Soru numarası", placeholder="S1")
        soru = st.text_area("Soru", placeholder="What is the role of a prototype program in problem solving?")
        referans = st.text_area("Referans (doğru) cevap",
                                placeholder="To simulate the behaviour of portions of the desired software product.")
        if st.form_submit_button("Kaydet", type="primary"):
            if soru_no.strip() and soru.strip() and referans.strip():
                vt.soru_ekle(soru_no, soru, referans)
                st.success(f"'{soru_no.strip()}' numaralı soru kaydedildi.")
            else:
                st.error("Soru numarası, soru ve referans cevap boş bırakılamaz.")
    kayitli = vt.sorular()
    st.subheader(f"Kayıtlı sorular ({len(kayitli)})")
    if kayitli:
        st.dataframe(pd.DataFrame(kayitli)[["soru_no", "soru", "referans"]], hide_index=True, use_container_width=True)
    else:
        st.info("Henüz soru yok.")

# ------------------------------------------------------------------ Öğretmen: CSV yükle (FR-02, FR-06)
elif sayfa == "CSV yükle ve puanla":
    st.header("CSV yükle ve puanla")
    st.markdown("Dosyada **`ogrenci_no`**, **`soru_no`** ve **`cevap`** sütunları olmalı. "
                "Soru numaraları **Sorular** sayfasında kayıtlı olmalı.")
    st.download_button("Örnek CSV indir", "ogrenci_no,soru_no,cevap\n101,S1,A prototype simulates part of the software.\n",
                       "ornek_cevaplar.csv", "text/csv")
    dosya = st.file_uploader("CSV dosyası", type=None)
    if dosya is not None and st.button("Puanla", type="primary"):
        with st.spinner("Cevaplar puanlanıyor…"):
            sonuc = toplu_puanla(vt, puanlayici, dosya.getvalue(), dosya.name)
        if sonuc["dosya_hatasi"]:
            st.error(sonuc["dosya_hatasi"])
        else:
            st.success(f"{len(sonuc['sonuclar'])} cevap puanlandı ve kaydedildi.")
            if sonuc["uyarilar"]:
                st.warning(f"{len(sonuc['uyarilar'])} satır puanlanmadı:")
                st.dataframe(pd.DataFrame(sonuc["uyarilar"]).rename(columns={"satir": "satır", "sutun": "sütun",
                                                                              "mesaj": "açıklama"}),
                             hide_index=True, use_container_width=True)
            st.dataframe(sonuc_tablosu(sonuc["sonuclar"]), hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ Öğretmen: Sonuçlar (FR-08, FR-10)
elif sayfa == "Sonuçlar":
    st.header("Sonuçlar")
    s1, s2, s3 = st.columns([1, 1, 2])
    soru_sec = s1.selectbox("Soru", ["Tümü"] + [s["soru_no"] for s in vt.sorular()])
    sadece = s2.checkbox("Sadece öğretmen incelemesi gerekenler")
    aralik = s3.slider("Puan aralığı (0–5)", 0.0, 5.0, (0.0, 5.0), step=0.5)
    kayitlar = vt.sonuclar(soru_no=None if soru_sec == "Tümü" else soru_sec, sadece_inceleme=sadece,
                           en_az=aralik[0], en_cok=aralik[1])
    tablo = sonuc_tablosu(kayitlar)
    if tablo.empty:
        st.info("Seçilen filtreye uyan sonuç yok.")
    else:
        a, b, c = st.columns(3)
        a.metric("Cevap", len(tablo))
        b.metric("Ortalama puan", f"{tablo['puan (0–5)'].mean():.1f} / 5".replace(".", ","))
        c.metric("İnceleme gereken", int(sum(k["inceleme_gerekli"] for k in kayitlar)))
        st.dataframe(tablo, hide_index=True, use_container_width=True)
        st.download_button("Sonuçları CSV olarak indir", tablo.to_csv(index=False).encode("utf-8-sig"),
                           "sonuclar.csv", "text/csv")

# ------------------------------------------------------------------ Öğrenci: Sonuçlarım (FR-07)
else:
    st.header("Sonuçlarım")
    ogrenci_no = st.text_input("Öğrenci numaran")
    if ogrenci_no.strip():
        kayitlar = vt.sonuclar(ogrenci_no=ogrenci_no.strip())
        if not kayitlar:
            st.info("Bu numaraya ait sonuç bulunamadı.")
        for k in kayitlar:
            s = vt.soru(k["soru_no"]) or {"soru": k["soru_no"]}
            with st.container(border=True):
                st.markdown(f"**{k['soru_no']} – {s['soru']}**")
                st.markdown(f"Cevabın: _{k['cevap']}_")
                st.markdown(f"Puanın: **{k['puan_5']:g} / 5**".replace(".", ","))
                if k["eksik_kavramlar"]:
                    st.markdown("Cevabında eksik kalan kavramlar:\n" + "\n".join(f"- {e}" for e in k["eksik_kavramlar"]))
                else:
                    st.markdown("Referans cevaptaki bütün kavramlara değinmişsin. ✓")
                if k["inceleme_gerekli"]:
                    st.caption("Bu puan öğretmenin incelemesini bekliyor.")
