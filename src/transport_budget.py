#!/usr/bin/env python3
"""
transport_budget.py — anggaran latensi lengkap + kelayakan kanal.

Menutup kritik "transport excluded" dengan menambahkan suku transmisi ke
anggaran E2E, dan memeriksa apakah beban agregat muat di kanal DSRC.

Murni analitik, tanpa dependensi. Jalankan:

    python3 src/transport_budget.py                  # tabel ke stdout
    python3 src/transport_budget.py --latex          # + kode LaTeX siap tempel

Angka default diambil dari naskah:
  tuple full-cert 10,662 B / digest 3,465 B   (Bagian V-E)
  W = 90 ms, T_proc,max = 2.4 ms              (Tabel VIII)
  25 kendaraan serentak @ 10 msg/s            (Bagian V-E, Little's Law)
"""

import argparse

TUPLE_FULL_B = 10_662
TUPLE_DIGEST_B = 3_465
W_MS = 90.0
T_PROC_MAX_MS = 2.4
DEADLINE_MS = 100.0
N_CONCURRENT = 25
MSG_RATE_HZ = 10

# (label, bitrate bps, efisiensi MAC) — efisiensi memodelkan overhead CSMA/CA
MCS = [
    ("DSRC 6 Mbit/s", 6e6, 1.00),
    ("DSRC 12 Mbit/s", 12e6, 1.00),
    ("DSRC 27 Mbit/s", 27e6, 1.00),
    ("DSRC 27 Mbit/s (MAC 0.6)", 27e6, 0.60),
]


def tx_ms(size_b, bitrate, eff=1.0):
    """Waktu transmisi satu pesan, ms."""
    return size_b * 8 / (bitrate * eff) * 1e3


def offered_load_mbps(size_b, n=N_CONCURRENT, rate=MSG_RATE_HZ):
    """Beban agregat yang ditawarkan ke kanal, Mbit/s."""
    return n * rate * size_b * 8 / 1e6


def budget(size_b, bitrate, eff=1.0):
    t = tx_ms(size_b, bitrate, eff)
    total = W_MS + T_PROC_MAX_MS + t
    return t, total, DEADLINE_MS - total


def report():
    print("=" * 74)
    print("1. ANGGARAN LATENSI LENGKAP  (W + T_proc,max + T_tx)")
    print("=" * 74)
    print(f"   W = {W_MS:.0f} ms, T_proc,max = {T_PROC_MAX_MS} ms, deadline = {DEADLINE_MS:.0f} ms\n")
    print(f"{'mode':<10}{'kanal':<28}{'T_tx':>8}{'total':>9}{'margin':>9}  status")
    print("-" * 74)
    for mode, size in (("full-cert", TUPLE_FULL_B), ("digest", TUPLE_DIGEST_B)):
        for label, br, eff in MCS:
            t, tot, marg = budget(size, br, eff)
            print(f"{mode:<10}{label:<28}{t:>7.2f}m{tot:>8.2f}m{marg:>8.2f}m  "
                  f"{'OK' if marg > 0 else 'MISS'}")
    print()
    print("   Catatan: klaim lama W + T_proc,max = 92.4 ms memberi margin 7.6 ms.")
    print("   Dengan transport, margin menyusut - itulah hasil yang jujur.\n")

    print("=" * 74)
    print("2. KELAYAKAN KANAL  (beban yang ditawarkan vs kapasitas)")
    print("=" * 74)
    print(f"   {N_CONCURRENT} kendaraan serentak @ {MSG_RATE_HZ} msg/s\n")
    print(f"{'mode':<10}{'ukuran':>10}{'beban':>14}   kanal minimum yang dibutuhkan")
    print("-" * 74)
    for mode, size in (("full-cert", TUPLE_FULL_B), ("digest", TUPLE_DIGEST_B)):
        load = offered_load_mbps(size)
        need = [lbl for lbl, br, eff in MCS if br * eff >= load * 1e6]
        print(f"{mode:<10}{size:>9,}B{load:>12.2f} Mb/s   "
              f"{need[0] if need else 'TIDAK ADA MCS DSRC YANG CUKUP'}")
    print()
    print("   PENTING: digest mode (6.93 Mbit/s) MELEBIHI batas bawah DSRC 6 Mbit/s.")
    print("   Naskah memakai digest sebagai solusi kelayakan kanal, jadi asumsi MCS")
    print("   harus dinaikkan ke >=12 Mbit/s, atau message rate diturunkan.\n")

    print("=" * 74)
    print("3. MESSAGE RATE MAKSIMUM PER MCS  (mode digest)")
    print("=" * 74)
    print(f"{'kanal':<28}{'rate maks/kendaraan':>22}")
    print("-" * 74)
    for label, br, eff in MCS:
        r = br * eff / (N_CONCURRENT * TUPLE_DIGEST_B * 8)
        print(f"{label:<28}{r:>19.1f} msg/s")
    print()


def latex():
    print(r"% ---- sisipkan di Bagian VII (evaluasi) ----")
    print(r"\begin{table}[!t]")
    print(r"\centering\footnotesize")
    print(r"\caption{Anggaran latensi lengkap termasuk transmisi, dan beban kanal "
          r"yang ditawarkan pada $25$ kendaraan serentak dengan $10$~msg/s. "
          r"$W = 90$~ms, $T_{\mathrm{proc,max}} = 2.4$~ms, deadline $100$~ms.}")
    print(r"\label{tab:transport}")
    print(r"\begin{tabular}{@{}llrrrr@{}}")
    print(r"\toprule")
    print(r"Mode & Kanal & $T_{\mathrm{tx}}$ & Total & Margin & Beban \\")
    print(r" & & (ms) & (ms) & (ms) & (Mbit/s) \\")
    print(r"\midrule")
    for mode, size in (("Full-cert", TUPLE_FULL_B), ("Digest", TUPLE_DIGEST_B)):
        load = offered_load_mbps(size)
        for label, br, eff in MCS:
            t, tot, marg = budget(size, br, eff)
            print(f"{mode} & {label} & {t:.2f} & {tot:.2f} & {marg:.2f} & {load:.2f} \\\\")
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")
    print()
    print(r"% ---- paragraf pendamping ----")
    t_dig, tot_dig, marg_dig = budget(TUPLE_DIGEST_B, 6e6)
    load_dig = offered_load_mbps(TUPLE_DIGEST_B)
    print(r"Anggaran latensi yang dilaporkan pada Tabel~\ref{tab:e2e} mengecualikan "
          r"transmisi nirkabel. Menambahkan suku transmisi satu pesan melengkapi "
          r"anggaran tersebut: pada mode sertifikat-digest ("
          f"{TUPLE_DIGEST_B:,}~B) dan DSRC 6~Mbit/s, $T_{{\\mathrm{{tx}}}} = {t_dig:.2f}$~ms, "
          f"sehingga $W + T_{{\\mathrm{{proc,max}}}} + T_{{\\mathrm{{tx}}}} = {tot_dig:.2f}$~ms "
          f"dan margin terhadap deadline $100$~ms menyusut dari $7.6$~ms menjadi "
          f"${marg_dig:.2f}$~ms. Kesimpulan kelayakan bersyarat tetap berlaku, tetapi "
          r"marginnya jauh lebih ketat, yang memperkuat temuan E4 bahwa pemilihan "
          r"$W$ merupakan parameter dominan.")
    print()
    print(r"Analisis beban kanal justru lebih membatasi. Pada $25$ kendaraan serentak "
          f"dengan $10$~msg/s, mode digest menghasilkan ${load_dig:.2f}$~Mbit/s, yang "
          r"melampaui batas bawah DSRC $6$~Mbit/s. Mode digest karena itu memerlukan "
          r"MCS minimal $12$~Mbit/s, dan dengan efisiensi MAC realistis $0.6$ "
          r"memerlukan $27$~Mbit/s. Batas ini bersifat struktural: ia berasal dari "
          f"ukuran tanda tangan ML-DSA-65 ($3{{,}}309$~B) dan bukan dari rancangan "
          r"agregasi.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--latex", action="store_true", help="cetak kode LaTeX siap tempel")
    a = ap.parse_args()
    report()
    if a.latex:
        latex()
