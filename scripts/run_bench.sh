#!/usr/bin/env bash
# run_bench.sh — build liboqs (jika belum ada) lalu jalankan benchmark PQ-CBAS-DSH.
# Dipakai di macOS (Apple silicon/Intel) maupun Linux. Jalankan dari folder artifact:
#   bash run_bench.sh
set -euo pipefail
cd "$(dirname "$0")"

OQS_PREFIX="${OQS_PREFIX:-$HOME/oqs}"

# 1) Build liboqs sekali saja
if [ ! -d "$OQS_PREFIX/lib" ]; then
  echo "[1/3] Building liboqs ke $OQS_PREFIX ..."
  command -v cmake >/dev/null || { echo "cmake tidak ditemukan (macOS: brew install cmake ninja; Linux: apt install cmake ninja-build)"; exit 1; }
  [ -d liboqs ] || git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git
  cmake -S liboqs -B liboqs/build -GNinja \
    -DOQS_MINIMAL_BUILD="SIG_ml_dsa_44;SIG_ml_dsa_65;SIG_ml_dsa_87" \
    -DBUILD_SHARED_LIBS=ON -DOQS_USE_OPENSSL=OFF -DCMAKE_BUILD_TYPE=Release
  ninja -C liboqs/build
  cmake --install liboqs/build --prefix "$OQS_PREFIX"
else
  echo "[1/3] liboqs sudah ada di $OQS_PREFIX"
fi

# 2) Virtualenv + dependensi
echo "[2/3] Menyiapkan Python venv ..."
[ -d venv ] || python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install -q liboqs-python numpy

# 3) Jalankan benchmark (hasil: bench_results.json di folder ini)
echo "[3/3] Menjalankan benchmark ..."
OQS_INSTALL_PATH="$OQS_PREFIX" python3 src/bench_pqcbas.py
echo "Selesai. Hasil tersimpan di bench_results.json"
