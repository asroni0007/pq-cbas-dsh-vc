#!/usr/bin/env bash
# run_seeds.sh — jalankan sweep E2E dengan jumlah seed yang memadai.
#
#   bash run_seeds.sh            # default 20 seed, W=90 ms, kedua mode
#   bash run_seeds.sh 30 90      # 30 seed, W=90 ms
#
# Prasyarat: liboqs + venv sudah disiapkan (jalankan run_bench.sh sekali dulu).
# Hasil: results_W<W>_<mode>.json di folder kerja.
#
# Kenapa 20 dan bukan 50: t(df=19)=2.093 vs t(df=49)=2.010 — hanya 4% beda.
# n=20 sudah menangkap ~96% manfaat penyempitan CI. Lihat src/ci_stats.py.

set -euo pipefail
cd "$(dirname "$0")"

SEEDS="${1:-20}"
W="${2:-90}"
OQS_PREFIX="${OQS_PREFIX:-$HOME/oqs}"

if [ ! -d "$OQS_PREFIX/lib" ]; then
  echo "liboqs tidak ditemukan di $OQS_PREFIX — jalankan 'bash run_bench.sh' dulu." >&2
  exit 1
fi

# shellcheck disable=SC1091
[ -d venv ] && source venv/bin/activate

echo "=== Sweep: $SEEDS seed, W = $W ms ==="
echo "Perkiraan durasi: ~$(( SEEDS * 2 )) menit untuk kedua mode."
echo

for MODE_FLAG in "" "--digest"; do
  LABEL=$([ -z "$MODE_FLAG" ] && echo "full-cert" || echo "digest")
  echo "--- mode: $LABEL ---"
  OQS_INSTALL_PATH="$OQS_PREFIX" \
    python3 src/e2e_workflow.py --window "$W" --seeds "$SEEDS" $MODE_FLAG
  echo
done

echo "=== Selesai ==="
echo "Verifikasi CI memakai Student-t (bukan 1.96):"
echo "  python3 src/ci_stats.py"
echo
echo "Kalau e2e_workflow.py BELUM dipatch, nilai ci95 di JSON masih memakai"
echo "z=1.96 dan understated. Lihat RUNBOOK.md bagian 1."
