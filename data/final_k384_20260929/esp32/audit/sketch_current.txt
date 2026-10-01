/*
 * PQCBAS_ESP32_Bench.ino — PQ-CBAS-DSH pada ESP32 (Arduino IDE)
 *
 * Mengukur, memakai implementasi referensi PQClean Dilithium3
 * (= ML-DSA-65, FIPS 204) dan SHAKE256 domain-separated hashing:
 *
 *   A. Operasi inti  : keypair / sign / verify
 *   B. Overhead DSH  : Hcert + Hsign per pesan (klaim E2 pada naskah)
 *   C. Kelayakan OBU : sign vs anggaran BSM 5/10/20 msg/s
 *   D. Kelayakan RSU : verifikasi batch m = 1,2,5,10 — DIUKUR
 *
 * PAPAN  : DOIT ESP32 DEVKIT V1
 * SETUP  : jalankan setup_arduino.sh dulu untuk mengisi folder src/
 *
 * CATATAN STACK: sign ML-DSA-65 butuh ~84 KB. loopTask Arduino hanya 8 KB,
 * jadi benchmark dijalankan di task FreeRTOS terpisah berstack besar.
 */

#include <Arduino.h>
#include <math.h>
#include <esp_timer.h>
#include <esp_system.h>
#include <esp_random.h>

extern "C" {
  #include "src/api.h"
  #include "src/fips202.h"
}

/* ---- parameter benchmark ---- */
#define N_KEYPAIR    20
#define N_SIGN       500
#define N_VERIFY     50
#define N_DSH       200
#define N_BATCH      10        /* repetisi per ukuran batch */
#define MSG_LEN     100        /* payload BSM tipikal (naskah: 100 B) */
#define MAX_BATCH    10
#define BENCH_STACK (110 * 1024)
#define DEADLINE_MS 100.0
#define W_MS         90.0

/* ---- alias PQClean ---- */
#ifndef PK_BYTES
  #define PK_BYTES  PQCLEAN_DILITHIUM3_CLEAN_CRYPTO_PUBLICKEYBYTES
  #define SK_BYTES  PQCLEAN_DILITHIUM3_CLEAN_CRYPTO_SECRETKEYBYTES
  #define SIG_BYTES PQCLEAN_DILITHIUM3_CLEAN_CRYPTO_BYTES
  #define KEYPAIR   PQCLEAN_DILITHIUM3_CLEAN_crypto_sign_keypair
  #define SIGNATURE PQCLEAN_DILITHIUM3_CLEAN_crypto_sign_signature
  #define VERIFYSIG PQCLEAN_DILITHIUM3_CLEAN_crypto_sign_verify
#endif

/* prefiks domain PQ-CBAS-DSH, Persamaan (1)-(2) pada naskah */
static const char DOM_CERT[] = "PQ-CBAS-DSH/CERT";
static const char DOM_SIGN[] = "PQ-CBAS-DSH/SIGN";

/* ---- buffer statis (.bss), terlalu besar untuk stack ---- */
static uint8_t pk[MAX_BATCH][PK_BYTES];
static uint8_t sig[MAX_BATCH][SIG_BYTES];
static uint8_t mu[MAX_BATCH][64];
static uint8_t sk_buf[SK_BYTES];        /* tunggal: sk hanya dipakai saat sign */
static uint8_t msg[MSG_LEN];
static size_t  siglen[MAX_BATCH];

typedef struct { double mn, mx, sum, sumsq; int n; } stat_t;

static void st_add(stat_t *s, double v) {
  if (s->n == 0 || v < s->mn) s->mn = v;
  if (s->n == 0 || v > s->mx) s->mx = v;
  s->sum += v; s->sumsq += v * v; s->n++;
}
static double st_mean(const stat_t *s) { return s->n ? s->sum / s->n : 0.0; }
static double st_sd(const stat_t *s) {
  if (s->n < 2) return 0.0;
  double m = st_mean(s), v = s->sumsq / s->n - m * m;
  return v > 0 ? sqrt(v) : 0.0;
}
static void st_print(const char *name, const stat_t *s) {
  Serial.printf("  %-12s n=%3d  mean=%9.3f ms  sd=%8.3f  min=%9.3f  max=%9.3f\n",
                name, s->n, st_mean(s), st_sd(s), s->mn, s->mx);
}
static inline double now_ms() { return (double)esp_timer_get_time() / 1000.0; }

/* XOF(prefix || data) */
static void dsh(const char *dom, size_t dlen, const uint8_t *in, size_t inlen,
                uint8_t *out, size_t outlen) {
  shake256incctx ctx;
  shake256_inc_init(&ctx);
  shake256_inc_absorb(&ctx, (const uint8_t *)dom, dlen);
  shake256_inc_absorb(&ctx, in, inlen);
  shake256_inc_finalize(&ctx);
  shake256_inc_squeeze(out, outlen, &ctx);
  shake256_inc_ctx_release(&ctx);
}

static void benchTask(void *arg) {
  (void)arg;
  stat_t s_kp = {}, s_sg = {}, s_vf = {}, s_dsh = {};
  stat_t s_batch[MAX_BATCH + 1];
  memset(s_batch, 0, sizeof(s_batch));

  Serial.println("\n========================================================");
  Serial.println(" PQ-CBAS-DSH benchmark - ESP32 (kelas OBU)");
  Serial.println("========================================================");
  Serial.printf("  pk=%d B  sk=%d B  sig=%d B  msg=%d B\n\n",
                PK_BYTES, SK_BYTES, SIG_BYTES, MSG_LEN);

  for (int i = 0; i < MSG_LEN; i++) msg[i] = (uint8_t)(i & 0xFF);

  /* ---------- A. keypair ---------- */
  Serial.printf("[1/5] keypair (n=%d)...\n", N_KEYPAIR);
  for (int i = 0; i < N_KEYPAIR; i++) {
    double t0 = now_ms();
    KEYPAIR(pk[0], sk_buf);
    st_add(&s_kp, now_ms() - t0);
    vTaskDelay(1);
  }

  /* ---------- B. overhead DSH ---------- */
  Serial.printf("[2/5] domain-separated hashing (n=%d)...\n", N_DSH);
  for (int i = 0; i < N_DSH; i++) {
    double t0 = now_ms();
    dsh(DOM_CERT, sizeof(DOM_CERT) - 1, pk[0], PK_BYTES, mu[0], 32);
    dsh(DOM_SIGN, sizeof(DOM_SIGN) - 1, msg, MSG_LEN, mu[0], 64);
    st_add(&s_dsh, now_ms() - t0);
  }

  /* ---------- C. sign ---------- */
  Serial.printf("[3/5] sign (n=%d)...\n", N_SIGN);
  for (int i = 0; i < N_SIGN; i++) {
    dsh(DOM_SIGN, sizeof(DOM_SIGN) - 1, msg, MSG_LEN, mu[0], 64);
    double t0 = now_ms();
    SIGNATURE(sig[0], &siglen[0], mu[0], 64, sk_buf);
    st_add(&s_sg, now_ms() - t0);
    vTaskDelay(1);
  }

  /* ---------- D. verify tunggal ---------- */
  Serial.printf("[4/5] verify (n=%d)...\n", N_VERIFY);
  for (int i = 0; i < N_VERIFY; i++) {
    double t0 = now_ms();
    int rc = VERIFYSIG(sig[0], siglen[0], mu[0], 64, pk[0]);
    st_add(&s_vf, now_ms() - t0);
    if (rc != 0) { Serial.printf("  !! VERIFY GAGAL (i=%d)\n", i); break; }
    vTaskDelay(1);
  }

  /* ---------- E. batch verify sisi-RSU (DIUKUR) ---------- */
  Serial.println("[5/5] batch verify m=1,2,5,10...");
  Serial.printf("      menyiapkan %d penandatangan berbeda...\n", MAX_BATCH);
  for (int i = 0; i < MAX_BATCH; i++) {
    KEYPAIR(pk[i], sk_buf);
    msg[0] = (uint8_t)i;                       /* pesan unik per signer */
    dsh(DOM_SIGN, sizeof(DOM_SIGN) - 1, msg, MSG_LEN, mu[i], 64);
    SIGNATURE(sig[i], &siglen[i], mu[i], 64, sk_buf);
    vTaskDelay(1);
  }

  const int sizes[] = {1, 2, 5, 10};
  for (int si = 0; si < 4; si++) {
    int m = sizes[si];
    for (int r = 0; r < N_BATCH; r++) {
      double t0 = now_ms();
      for (int i = 0; i < m; i++) {
        if (VERIFYSIG(sig[i], siglen[i], mu[i], 64, pk[i]) != 0)
          Serial.printf("  !! batch verify gagal (m=%d,i=%d)\n", m, i);
      }
      st_add(&s_batch[m], now_ms() - t0);
      vTaskDelay(1);
    }
  }

  /* ================= HASIL ================= */
  Serial.println("\n--- A. Operasi inti ---");
  st_print("keypair", &s_kp);
  st_print("sign",    &s_sg);
  st_print("verify",  &s_vf);
  st_print("2x DSH",  &s_dsh);

  double sign_ms = st_mean(&s_sg);

  Serial.println("\n--- B. Kelayakan OBU (sign vs anggaran BSM) ---");
  const int rates[] = {5, 10, 20};
  for (int i = 0; i < 3; i++) {
    double budget = 1000.0 / rates[i];
    Serial.printf("  %2d msg/s : anggaran %6.1f ms | sign %7.2f ms = %5.1f%% | %s\n",
                  rates[i], budget, sign_ms, sign_ms / budget * 100.0,
                  sign_ms < budget ? "LAYAK" : "TIDAK LAYAK");
  }

  Serial.println("\n--- C. Verifikasi batch sisi-RSU (terukur) ---");
  Serial.printf("  %3s %12s %12s %12s\n", "m", "batch (ms)", "per-tuple", "W+proc");
  for (int si = 0; si < 4; si++) {
    int m = sizes[si];
    double b = st_mean(&s_batch[m]);
    Serial.printf("  %3d %12.2f %12.3f %12.1f  %s\n",
                  m, b, b / m, W_MS + b,
                  (W_MS + b) < DEADLINE_MS ? "OK" : "MISS");
  }

  Serial.println("\n--- D. Proyeksi ke beban skenario naskah ---");
  double per_tuple = st_mean(&s_batch[10]) / 10.0;
  const int ts[] = {18, 25, 64};
  for (int i = 0; i < 3; i++) {
    double proc = per_tuple * ts[i];
    Serial.printf("  t=%2d : proc %8.1f ms | W+proc %8.1f ms | %s\n",
                  ts[i], proc, W_MS + proc,
                  (W_MS + proc) < DEADLINE_MS ? "OK" : "MISS");
  }
  Serial.printf("  (per-tuple %.3f ms dari batch m=10 terukur)\n", per_tuple);

  Serial.println("\n--- E. Memori ---");
  Serial.printf("  heap bebas   : %u B\n", (unsigned)ESP.getFreeHeap());
  Serial.printf("  heap minimum : %u B\n", (unsigned)ESP.getMinFreeHeap());
  Serial.printf("  stack sisa   : %u B dari %d B\n",
                (unsigned)uxTaskGetStackHighWaterMark(NULL) * 4, BENCH_STACK);

  /* ---- JSON: salin blok ini untuk dikirim ---- */
  Serial.println("\n--- F. JSON (salin baris di bawah) ---");
  Serial.printf("{\"platform\":\"esp32\",\"cpu_mhz\":%d,"
                "\"keypair_ms\":%.4f,\"keypair_sd\":%.4f,"
                "\"sign_ms\":%.4f,\"sign_sd\":%.4f,"
                "\"verify_ms\":%.4f,\"verify_sd\":%.4f,"
                "\"dsh2_ms\":%.4f,",
                (int)getCpuFrequencyMhz(),
                st_mean(&s_kp), st_sd(&s_kp), sign_ms, st_sd(&s_sg),
                st_mean(&s_vf), st_sd(&s_vf), st_mean(&s_dsh));
  Serial.print("\"batch\":{");
  for (int si = 0; si < 4; si++)
    Serial.printf("\"%d\":%.4f%s", sizes[si], st_mean(&s_batch[sizes[si]]),
                  si < 3 ? "," : "");
  Serial.printf("},\"heap_free\":%u,\"pk\":%d,\"sk\":%d,\"sig\":%d}\n",
                (unsigned)ESP.getFreeHeap(), PK_BYTES, SK_BYTES, SIG_BYTES);

  Serial.println("\n=== Selesai ===");
  vTaskDelete(NULL);
}

void setup() {
  Serial.begin(115200);
  delay(2000);                       /* beri waktu monitor serial terhubung */

  setCpuFrequencyMhz(240);           /* pastikan 240 MHz penuh */

  Serial.printf("\n[PLATFORM] ESP32 | %d MHz | %d core | SDK %s\n",
                (int)getCpuFrequencyMhz(), ESP.getChipCores(), ESP.getSdkVersion());
  Serial.printf("[PLATFORM] flash %u B | heap awal %u B\n",
                (unsigned)ESP.getFlashChipSize(), (unsigned)ESP.getFreeHeap());

  xTaskCreate(benchTask, "bench", BENCH_STACK, NULL, 5, NULL);
}

void loop() {
  vTaskDelay(pdMS_TO_TICKS(1000));   /* semua kerja ada di benchTask */
}
