#!/usr/bin/env bash
# patch_n500.sh — tingkatkan benchmark ESP32 ke n=500 dengan statistik ekor.
#
# Jalankan dari folder sketch:
#     cd ~/Documents/Arduino/PQCBAS_ESP32_Bench
#     bash patch_n500.sh
#
# Perubahan:
#   N_SIGN 50 -> 500
#   simpan seluruh 500 waktu tanda tangan (2 KB)
#   hitung persentil p50/p90/p95/p99/maks
#   hitung fraksi yang MELEWATI deadline pada 5/10/20 msg/s
#   histogram jumlah iterasi Fiat-Shamir
#
# Kenapa penting: dengan n=50 klaim E4 hanya "rentangnya 37.8-356.8 ms".
# Dengan n=500 klaim menjadi "X% tanda tangan melewati deadline 100 ms,
# CI95 +-4 pp" -- angka yang bisa dipertahankan reviewer.

set -euo pipefail
cd "$(dirname "$0")"
F=PQCBAS_ESP32_Bench.ino
[ -f "$F" ] || { echo "ERROR: $F tidak ditemukan"; exit 1; }
if grep -q "sign_samples" "$F"; then
  echo "Sketch sudah dipatch (sign_samples ditemukan)."
  echo "Menormalkan N_SIGN ke 500 saja, tanpa menyisipkan ulang."
  python3 - "$F" <<'PYNORM'
import sys, io, re
p = sys.argv[1]; s = io.open(p, encoding='utf-8').read()
io.open(p, 'w', encoding='utf-8').write(re.sub(r'#define N_SIGN\s+\d+', '#define N_SIGN      500', s))
print("N_SIGN dinormalkan ke 500")
PYNORM
  grep -n "#define N_SIGN" "$F"
  exit 0
fi
cp "$F" "$F.bak.n50"

python3 - "$F" <<'PY'
import sys, io
p = sys.argv[1]
s = io.open(p, encoding='utf-8').read()

# --- 1. naikkan jumlah sampel (idempoten: aman dijalankan berulang) ---
import re as _re
assert _re.search(r'#define N_SIGN\s+\d+', s), "anchor N_SIGN tidak cocok"
s = _re.sub(r'#define N_SIGN\s+\d+', '#define N_SIGN      500', s)

# --- 2. buffer penyimpan seluruh sampel ---
anchor = "static size_t  siglen[MAX_BATCH];"
assert anchor in s
s = s.replace(anchor, anchor + "\nstatic float   sign_samples[N_SIGN];   /* 500 x 4 B = 2 KB */")

# --- 3. rekam tiap sampel di loop sign ---
old_sg = """    SIGNATURE(sig[0], &siglen[0], mu[0], 64, sk_buf);
    st_add(&s_sg, now_ms() - t0);"""
new_sg = """    SIGNATURE(sig[0], &siglen[0], mu[0], 64, sk_buf);
    double dt = now_ms() - t0;
    st_add(&s_sg, dt);
    sign_samples[i] = (float)dt;"""
assert old_sg in s, "anchor loop sign tidak cocok"
s = s.replace(old_sg, new_sg)

# --- 4. fungsi persentil + analisis ekor, sisipkan sebelum benchTask ---
helpers = r"""
/* ---- analisis ekor distribusi tanda tangan ---- */
static int cmp_float(const void *a, const void *b) {
  float x = *(const float*)a, y = *(const float*)b;
  return (x > y) - (x < y);
}
static float pct(const float *sorted, int n, double q) {
  double idx = q * (n - 1);
  int lo = (int)idx; int hi = lo + 1 < n ? lo + 1 : lo;
  double f = idx - lo;
  return sorted[lo] * (1.0 - f) + sorted[hi] * f;
}

static void benchTask(void *arg);
"""
s = s.replace("static void benchTask(void *arg) {", helpers + "\nstatic void benchTask(void *arg) {", 1)

# --- 5. laporan ekor, sisipkan sebelum blok memori ---
old_mem = '  Serial.println("\\n--- E. Memori ---");'
tail = r"""  /* ---------- F. Analisis ekor tanda tangan (E4) ---------- */
  Serial.println("\n--- F. Distribusi waktu tanda tangan (n=500) ---");
  static float srt[N_SIGN];
  memcpy(srt, sign_samples, sizeof(srt));
  qsort(srt, N_SIGN, sizeof(float), cmp_float);

  float p50 = pct(srt, N_SIGN, 0.50), p90 = pct(srt, N_SIGN, 0.90);
  float p95 = pct(srt, N_SIGN, 0.95), p99 = pct(srt, N_SIGN, 0.99);
  Serial.printf("  p50 %7.2f | p90 %7.2f | p95 %7.2f | p99 %7.2f | max %7.2f ms\n",
                p50, p90, p95, p99, srt[N_SIGN-1]);

  Serial.println("\n--- G. Pelanggaran deadline per laju BSM ---");
  const int rr[] = {5, 10, 20};
  float miss_frac[3];
  for (int r = 0; r < 3; r++) {
    float budget = 1000.0f / rr[r];
    int over = 0;
    for (int i = 0; i < N_SIGN; i++) if (sign_samples[i] > budget) over++;
    miss_frac[r] = (float)over / N_SIGN;
    float se = sqrtf(miss_frac[r] * (1 - miss_frac[r]) / N_SIGN);
    Serial.printf("  %2d msg/s : anggaran %6.1f ms | melewati %3d/%d = %5.1f%% "
                  "(CI95 +-%.1f pp)\n",
                  rr[r], budget, over, N_SIGN, miss_frac[r] * 100.0f, 1.96f * se * 100.0f);
  }

  Serial.println("\n--- H. Histogram iterasi Fiat-Shamir ---");
  float unit = srt[0];                      /* 1 iterasi = waktu minimum */
  int hist[12] = {0};
  for (int i = 0; i < N_SIGN; i++) {
    int k = (int)(sign_samples[i] / unit + 0.5f);
    if (k < 1) k = 1; if (k > 11) k = 11;
    hist[k]++;
  }
  Serial.printf("  1 iterasi = %.2f ms\n", unit);
  for (int k = 1; k <= 11; k++)
    if (hist[k]) Serial.printf("   k=%2d%s : %3d (%4.1f%%)\n",
                               k, k == 11 ? "+" : " ", hist[k],
                               100.0f * hist[k] / N_SIGN);

"""
assert old_mem in s, "anchor blok memori tidak cocok"
s = s.replace(old_mem, tail + old_mem)

# --- 6. tambahkan statistik ekor ke JSON ---
old_json = '''  Serial.printf("},\\"heap_free\\":%u,\\"pk\\":%d,\\"sk\\":%d,\\"sig\\":%d}\\n",'''
new_json = '''  Serial.printf("},\\"sign_p50\\":%.3f,\\"sign_p90\\":%.3f,\\"sign_p95\\":%.3f,"
                "\\"sign_p99\\":%.3f,\\"sign_max\\":%.3f,\\"sign_n\\":%d,"
                "\\"miss_5\\":%.4f,\\"miss_10\\":%.4f,\\"miss_20\\":%.4f,",
                p50, p90, p95, p99, srt[N_SIGN-1], N_SIGN,
                miss_frac[0], miss_frac[1], miss_frac[2]);
  Serial.printf("\\"heap_free\\":%u,\\"pk\\":%d,\\"sk\\":%d,\\"sig\\":%d}\\n",'''
assert old_json in s, "anchor JSON tidak cocok"
s = s.replace(old_json, new_json)

io.open(p, 'w', encoding='utf-8').write(s)
print("patch berhasil diterapkan")
PY

echo
echo "Verifikasi:"
grep -n "N_SIGN      500\|sign_samples\|sign_p50\|Histogram" "$F" | head -6
echo
echo "Langkah berikutnya:"
echo "  1. Arduino IDE: Cmd+R (reload), lalu Upload"
echo "  2. lsof -t /dev/cu.usbserial-0001 | xargs -r kill -9"
echo "  3. stty -f /dev/cu.usbserial-0001 115200"
echo "  4. cat /dev/cu.usbserial-0001 | tee ~/Desktop/esp32_n500.txt"
echo "  5. cabut-pasang USB, tunggu ~60 detik, Ctrl+C"
echo
echo "Cadangan n=50 tersimpan sebagai $F.bak.n50"
