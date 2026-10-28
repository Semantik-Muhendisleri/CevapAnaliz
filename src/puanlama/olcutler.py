"""NFR-01: Sistem puanı ile öğretmen puanı arasındaki uyumun ölçülmesi."""
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import cohen_kappa_score


def olc(gercek, tahmin, seviye: int) -> dict:
    """gercek ve tahmin 0-1 aralığında puanlardır.

    seviye: QWK için puanların kaç basamağa yuvarlanacağı
            (Mohler 0-5 arası tam sayı => 5, SemEval 0 / 0,5 / 1 => 2).
    """
    gercek, tahmin = np.asarray(gercek, float), np.clip(np.asarray(tahmin, float), 0, 1)
    # Yarımları her zaman yukarı yuvarla (3,5 -> 4); np.rint 2,5'i 2'ye yuvarlıyor.
    basamak = lambda x: np.floor(x * seviye + 0.5).astype(int)
    return {
        "pearson": pearsonr(gercek, tahmin)[0],
        "spearman": spearmanr(gercek, tahmin)[0],
        "qwk": cohen_kappa_score(basamak(gercek), basamak(tahmin), weights="quadratic"),
        "mae": np.mean(np.abs(gercek - tahmin)),
    }
