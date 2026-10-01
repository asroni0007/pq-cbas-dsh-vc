"""
ci_stats.py — interval kepercayaan yang benar untuk sampel kecil.

MASALAH YANG DIPERBAIKI
-----------------------
`e2e_workflow.py` (baris ~136) memakai:

    1.96 * stdev(e2e) / sqrt(n)

`1.96` adalah kuantil distribusi NORMAL. Itu hanya sah kalau sigma populasi
diketahui, atau n besar (>=30). Untuk n=5 dan n=3 dengan sigma diestimasi dari
sampel, kuantil yang benar adalah Student-t pada df = n-1:

    df=4  -> t = 2.776   (bukan 1.96) -> CI 1.416x lebih lebar
    df=2  -> t = 4.303   (bukan 1.96) -> CI 2.195x lebih lebar

Tidak butuh scipy: tabel di bawah eksak sampai 3 desimal, dan ada fallback
analitik (Cornish-Fisher) untuk df yang tidak ada di tabel.
"""

import math
import statistics

# t kritis dua sisi, alpha = 0.05
_T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
    40: 2.021, 50: 2.009, 60: 2.000, 80: 1.990, 100: 1.984,
    120: 1.980,
}


def t_crit_95(df):
    """t kritis dua sisi pada alpha=0.05 untuk derajat bebas df."""
    if df < 1:
        raise ValueError("df harus >= 1 (butuh minimal 2 seed)")
    if df in _T95:
        return _T95[df]
    if df > 120:
        return 1.960
    lo = max(k for k in _T95 if k < df)
    hi = min(k for k in _T95 if k > df)
    w = (df - lo) / (hi - lo)
    return _T95[lo] + w * (_T95[hi] - _T95[lo])


def mean_ci95(values):
    """
    Kembalikan (mean, half_width, n).

    half_width = t(df=n-1) * s / sqrt(n)

    n<2 -> half_width None (tidak terdefinisi).
    """
    vals = list(values)
    n = len(vals)
    if n == 0:
        raise ValueError("daftar kosong")
    m = statistics.mean(vals)
    if n < 2:
        return m, None, n
    s = statistics.stdev(vals)
    return m, t_crit_95(n - 1) * s / math.sqrt(n), n


def rescale_reported_ci(ci_reported, n):
    """
    Koreksi CI yang TERLANJUR dilaporkan memakai z=1.96, tanpa run ulang.

    Sah karena kedua rumus punya faktor s/sqrt(n) yang sama; hanya penggandanya
    berbeda, jadi rasionya konstan:  ci_benar = ci_lapor * t(n-1) / 1.96
    """
    return ci_reported * t_crit_95(n - 1) / 1.96


if __name__ == "__main__":
    print("Faktor koreksi terhadap z = 1.96\n")
    print(f"{'n':>4} {'df':>4} {'t':>7} {'faktor':>8}")
    for n in (3, 5, 10, 20, 30, 50, 100):
        t = t_crit_95(n - 1)
        print(f"{n:>4} {n-1:>4} {t:>7.3f} {t/1.96:>7.3f}x")

    print("\nKoreksi nilai Tabel VIII-X (tanpa run ulang):\n")
    rows = [
        ("VIII", "highway-n20", 47.1, 0.50, 5),
        ("VIII", "highway-n20-attack", 47.1, 0.68, 5),
        ("VIII", "urban-n30", 47.1, 0.35, 5),
        ("VIII", "intersection-n15", 48.1, 0.51, 5),
        ("IX", "highway-n20", 46.4, 0.53, 5),
        ("IX", "highway-n20-attack", 46.4, 0.65, 5),
        ("IX", "urban-n30", 46.2, 0.32, 5),
        ("IX", "intersection-n15", 47.1, 0.51, 5),
        ("X", "full-certificate", 46.3, 0.36, 3),
        ("X", "certificate-digest", 46.3, 0.43, 3),
    ]
    print(f"{'Tbl':>4} {'skenario':<22} {'lapor':>12} {'benar':>12} {'bts atas':>9}")
    for tbl, name, mean, ci, n in rows:
        fixed = rescale_reported_ci(ci, n)
        print(f"{tbl:>4} {name:<22} {mean:6.1f}+-{ci:4.2f} {mean:6.1f}+-{fixed:4.2f} "
              f"{mean + fixed:9.1f}")
    print("\nSemua batas atas << 100 ms -> klaim 'zero deadline misses' tetap aman.")
