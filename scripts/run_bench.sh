#!/usr/bin/env bash
# run_bench.sh — build liboqs (jika belum ada) lalu jalankan benchmark PQ-CBAS-DSH.
# Dipakai di macOS (Apple silicon/Intel) maupun Linux. Jalankan dari folder artifact:
#   bash run_bench.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

OQS_PREFIX="${OQS_PREFIX:-$HOME/oqs-0.16.0}"

# 1) Build liboqs sekali saja
if [ ! -d "$OQS_PREFIX/lib" ]; then
  echo "[1/3] Building liboqs ke $OQS_PREFIX ..."
  command -v cmake >/dev/null || { echo "cmake tidak ditemukan (macOS: brew install cmake ninja; Linux: apt install cmake ninja-build)"; exit 1; }
  DEPS_DIR="$ROOT_DIR/.deps"
  OQS_SRC="$DEPS_DIR/liboqs"
  mkdir -p "$DEPS_DIR"
  if [ ! -d "$OQS_SRC/.git" ]; then
    git clone --depth 1 --branch 0.16.0 https://github.com/open-quantum-safe/liboqs.git "$OQS_SRC"
  fi
  cmake -S "$OQS_SRC" -B "$OQS_SRC/build" -GNinja \
    -DOQS_MINIMAL_BUILD="SIG_ml_dsa_44;SIG_ml_dsa_65;SIG_ml_dsa_87" \
    -DBUILD_SHARED_LIBS=ON -DOQS_USE_OPENSSL=OFF -DCMAKE_BUILD_TYPE=Release
  ninja -C "$OQS_SRC/build"
  cmake --install "$OQS_SRC/build" --prefix "$OQS_PREFIX"
else
  echo "[1/3] liboqs sudah ada di $OQS_PREFIX"
fi

# 2) Virtualenv + dependensi
echo "[2/3] Menyiapkan Python venv ..."
[ -d venv ] || python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install -q liboqs-python numpy cryptography

# Verify that the Python binding resolves the exact manuscript liboqs release.
OQS_INSTALL_PATH="$OQS_PREFIX" python3 - <<'PY_OQS'
import oqs
v = str(oqs.oqs_version())
print(f"liboqs runtime: {v}")
if not v.startswith("0.16.0"):
    raise SystemExit(f"ERROR: expected liboqs 0.16.0, got {v}")
PY_OQS

# 3) Jalankan benchmark (hasil: bench_results.json di folder ini)
echo "[3/3] Menjalankan benchmark ..."
OQS_INSTALL_PATH="$OQS_PREFIX" python3 src/bench_pqcbas.py
echo "Selesai. Hasil tersimpan di bench_results.json"
