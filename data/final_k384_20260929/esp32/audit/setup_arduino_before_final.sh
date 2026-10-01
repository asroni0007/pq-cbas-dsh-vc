#!/usr/bin/env bash
# setup_arduino.sh — isi folder src/ sketch Arduino dengan sumber PQClean.
#
# Jalankan SEKALI dari folder PQCBAS_ESP32_Bench/ sebelum Verify di Arduino IDE.
#
# Arduino IDE mengompilasi semua .c/.cpp di dalam subfolder src/ secara
# rekursif, jadi PQClean bisa dipakai langsung tanpa membuat library.

set -euo pipefail
cd "$(dirname "$0")"

DEST="src"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "=== Mengambil PQClean Dilithium3 (ML-DSA-65) ==="
git clone --depth 1 https://github.com/PQClean/PQClean.git "$TMP/PQClean" 2>&1 | tail -2

SRC=""
for cand in ml-dsa-65 dilithium3; do
  if [ -d "$TMP/PQClean/crypto_sign/$cand/clean" ]; then
    SRC="$TMP/PQClean/crypto_sign/$cand/clean"; break
  fi
done
if [ -z "$SRC" ]; then
  echo "ERROR: folder skema tidak ditemukan. Isi crypto_sign/:" >&2
  ls "$TMP/PQClean/crypto_sign/" >&2
  exit 1
fi
echo "  sumber: $(basename "$(dirname "$SRC")")"

mkdir -p "$DEST"
cp "$SRC"/*.c "$SRC"/*.h "$DEST"/
cp "$TMP/PQClean/common/fips202.c" "$TMP/PQClean/common/fips202.h" "$DEST"/

# ---- shim RNG: pakai hardware RNG ESP32 ----
cat > "$DEST/randombytes.h" << 'EOF'
#ifndef RANDOMBYTES_H
#define RANDOMBYTES_H
#include <stddef.h>
#include <stdint.h>
int randombytes(uint8_t *output, size_t n);
#endif
EOF

cat > "$DEST/randombytes.c" << 'EOF'
/* RNG ESP32 untuk PQClean.
 * esp_fill_random() baru kriptografis penuh saat WiFi/BT aktif atau
 * bootloader_random_enable() dipanggil. Untuk benchmark timing ini cukup;
 * untuk deployment nyata pastikan sumber entropi aktif. */
#include "randombytes.h"
#include "esp_random.h"

int randombytes(uint8_t *output, size_t n) {
    esp_fill_random(output, n);
    return 0;
}
EOF

# ---- alias bila PQClean memakai prefiks MLDSA65 ----
if grep -rq "PQCLEAN_MLDSA65_CLEAN" "$DEST"/api.h 2>/dev/null; then
  echo "  [info] prefiks ML-DSA-65 terdeteksi; menambahkan alias."
  cat >> "$DEST/api.h" << 'EOF'

/* alias kompatibilitas ditambahkan oleh setup_arduino.sh */
#ifndef PQCBAS_ALIAS
#define PQCBAS_ALIAS
#define PQCLEAN_DILITHIUM3_CLEAN_CRYPTO_PUBLICKEYBYTES PQCLEAN_MLDSA65_CLEAN_CRYPTO_PUBLICKEYBYTES
#define PQCLEAN_DILITHIUM3_CLEAN_CRYPTO_SECRETKEYBYTES PQCLEAN_MLDSA65_CLEAN_CRYPTO_SECRETKEYBYTES
#define PQCLEAN_DILITHIUM3_CLEAN_CRYPTO_BYTES          PQCLEAN_MLDSA65_CLEAN_CRYPTO_BYTES
#define PQCLEAN_DILITHIUM3_CLEAN_crypto_sign_keypair   PQCLEAN_MLDSA65_CLEAN_crypto_sign_keypair
#define PQCLEAN_DILITHIUM3_CLEAN_crypto_sign_signature PQCLEAN_MLDSA65_CLEAN_crypto_sign_signature
#define PQCLEAN_DILITHIUM3_CLEAN_crypto_sign_verify    PQCLEAN_MLDSA65_CLEAN_crypto_sign_verify
#endif
EOF
fi

echo
echo "=== Selesai: $(ls "$DEST"/*.c "$DEST"/*.h 2>/dev/null | wc -l | tr -d ' ') file di $DEST/ ==="
echo
echo "Langkah berikutnya di Arduino IDE:"
echo "  1. Buka PQCBAS_ESP32_Bench.ino"
echo "  2. Tools > Board          : DOIT ESP32 DEVKIT V1"
echo "  3. Tools > Partition Scheme: Huge APP (3MB No OTA/1MB SPIFFS)"
echo "  4. Tools > CPU Frequency  : 240MHz"
echo "  5. Tools > Port           : /dev/cu.usbserial-0001"
echo "  6. Upload, lalu buka Serial Monitor @115200"
