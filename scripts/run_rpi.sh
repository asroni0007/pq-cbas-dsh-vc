#!/usr/bin/env bash
# run_rpi.sh — benchmark PQ-CBAS-DSH pada Raspberry Pi (kelas RSU/OBU).
#
# Tujuan utama: menguji apakah temuan E1 (CertValidate ML-DSA-65 lebih cepat
# daripada verify ECDSA-P256) BERTAHAN di ARM tanpa SIMD selebar Apple M2.
#
#   bash run_rpi.sh              # default: 20 seed, W=90 ms
#   bash run_rpi.sh 20 90
#
# Apa pun hasilnya, itu layak dilaporkan:
#   - inversi bertahan  -> klaim naik jadi "lintas kelas ARM"
#   - inversi hilang    -> temuan platform-specific yang jujur, dan jauh lebih
#                          baik Anda yang menemukan daripada reviewer.

set -euo pipefail
cd "$(dirname "$0")"

SEEDS="${1:-20}"
W="${2:-90}"
OQS_PREFIX="${OQS_PREFIX:-$HOME/oqs}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="results_rpi_${STAMP}"
mkdir -p "$OUT"

echo "=============================================="
echo " PQ-CBAS-DSH — benchmark Raspberry Pi"
echo "=============================================="

# ---------- 1. Rekam identitas platform (WAJIB untuk naskah) ----------
{
  echo "timestamp   : $(date -Is)"
  echo "hostname    : $(hostname)"
  echo "uname       : $(uname -a)"
  echo "model       : $(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo n/a)"
  echo "cpu         : $(grep -m1 'model name' /proc/cpuinfo 2>/dev/null || \
                        grep -m1 'Model' /proc/cpuinfo 2>/dev/null || echo n/a)"
  echo "cores       : $(nproc)"
  echo "arch        : $(uname -m)"
  echo "features    : $(grep -m1 'Features' /proc/cpuinfo 2>/dev/null || echo n/a)"
  echo "os          : $(lsb_release -ds 2>/dev/null || cat /etc/os-release | head -1)"
  echo "python      : $(python3 -V)"
  echo "governor    : $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo n/a)"
  echo "freq_max_kHz: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq 2>/dev/null || echo n/a)"
  echo "throttled   : $(vcgencmd get_throttled 2>/dev/null || echo n/a)"
  echo "temp        : $(vcgencmd measure_temp 2>/dev/null || echo n/a)"
} | tee "$OUT/platform.txt"
echo

# ---------- 2. Cek higienis pengukuran ----------
GOV="$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unknown)"
if [ "$GOV" != "performance" ]; then
  echo "PERINGATAN: governor = '$GOV', bukan 'performance'."
  echo "  Hasil akan berayun. Jalankan:"
  echo "    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
  read -r -p "  Lanjut tetap? [y/N] " a; [ "$a" = "y" ] || exit 1
fi

THR="$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2 || echo 0x0)"
if [ "$THR" != "0x0" ] && [ "$THR" != "n/a" ]; then
  echo "PERINGATAN: throttling terdeteksi ($THR) — pasang heatsink/fan, dinginkan, ulangi."
  read -r -p "  Lanjut tetap? [y/N] " a; [ "$a" = "y" ] || exit 1
fi

if [ ! -d "$OQS_PREFIX/lib" ]; then
  echo "liboqs tidak ada di $OQS_PREFIX — jalankan 'bash run_bench.sh' dulu." >&2
  exit 1
fi
# shellcheck disable=SC1091
[ -d venv ] && source venv/bin/activate

# ---------- 3. Benchmark operasi (di sinilah E1 diuji) ----------
echo "--- [1/3] Benchmark operasi + baseline ECDSA ---"
OQS_INSTALL_PATH="$OQS_PREFIX" python3 src/bench_pqcbas.py 2>&1 | tee "$OUT/bench.log"
[ -f bench_results.json ] && cp bench_results.json "$OUT/"
echo

# ---------- 4. E2E kedua mode ----------
echo "--- [2/3] E2E, $SEEDS seed, W=$W ms ---"
for FLAG in "" "--digest"; do
  LBL=$([ -z "$FLAG" ] && echo full || echo digest)
  echo "  mode: $LBL"
  OQS_INSTALL_PATH="$OQS_PREFIX" \
    python3 src/e2e_workflow.py --window "$W" --seeds "$SEEDS" $FLAG \
    2>&1 | tee "$OUT/e2e_$LBL.log"
  [ -f "e2e_results_W${W}_${LBL}.json" ] && cp "e2e_results_W${W}_${LBL}.json" "$OUT/"
done
echo

# ---------- 5. Ringkasan E1 ----------
echo "--- [3/3] Ringkasan E1 ---"
python3 - "$OUT" <<'PY'
import json, os, sys
d = sys.argv[1]
p = os.path.join(d, "bench_results.json")
if not os.path.exists(p):
    print("bench_results.json tidak ada — baca bench.log manual."); raise SystemExit

j = json.load(open(p))

def first_num(o):
    """Nilai numerik pertama di dalam struktur (prioritas kunci *_ms/mean)."""
    if isinstance(o, (int, float)):
        return o
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (int, float)) and ("ms" in k.lower() or "mean" in k.lower()):
                return v
        for v in o.values():
            r = first_num(v)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = first_num(v)
            if r is not None:
                return r
    return None


def dig(o, *keys):
    """Cari nilai numerik untuk kunci yang cocok, termasuk yang bersarang."""
    if isinstance(o, dict):
        for k, v in o.items():
            if all(t in k.lower() for t in keys):
                n = first_num(v)
                if n is not None:
                    return n
            r = dig(v, *keys)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = dig(v, *keys)
            if r is not None:
                return r
    return None

cv = dig(j, "certvalidate") or dig(j, "cert", "validate")
ec = dig(j, "ecdsa", "verify")

print(f"  CertValidate (ML-DSA-65) : {cv} ms")
print(f"  ECDSA-P256 verify        : {ec} ms")
if cv and ec:
    print()
    if cv < ec:
        print(f"  >>> E1 BERTAHAN: ML-DSA {ec/cv:.2f}x lebih cepat dari ECDSA.")
        print("      Klaim naik dari platform-specific ke lintas kelas ARM.")
    else:
        print(f"  >>> E1 TIDAK bertahan: ML-DSA {cv/ec:.2f}x lebih LAMBAT.")
        print("      Ini temuan sah: inversi bergantung pada lebar SIMD.")
        print("      Laporkan sebagai tabel dua-platform, JANGAN ganti angka M2.")
else:
    print("  (kunci tidak terdeteksi otomatis — ambil manual dari bench.log)")
PY

echo
echo "=============================================="
echo " Selesai. Semua hasil di: $OUT/"
echo "=============================================="
echo "Kirimkan isi folder ini dan saya susun tabel dua-platformnya."
