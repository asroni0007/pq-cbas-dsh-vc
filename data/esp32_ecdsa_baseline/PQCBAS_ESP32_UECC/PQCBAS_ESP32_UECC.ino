#include <Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <esp_timer.h>
#include <esp_system.h>
#include <esp_random.h>

#include <uECC.h>
#include "mbedtls/sha256.h"

/*
 * PQ-CBAS-DSH ESP32 ECDSA-P256 BASELINE #2: micro-ecc (uECC)  (companion to PQCBAS_ESP32_ECDSA)
 *
 * Second classical baseline: micro-ecc (secp256r1), a compact C library written
 * for small CPUs, in place of the mbedTLS build shipped with the core. SHA-256 is
 * still taken from the core (mbedtls_sha256), so only the ECC arithmetic differs.
 * Signature is raw r||s (64 B), not DER.
 *
 * Mirrors the structure of PQCBAS_ESP32_Final.ino:
 *   same CPU frequency (240 MHz), same task priority, same N (20/500/500),
 *   same timer (esp_timer, ms), vTaskDelay(1) between timed iterations,
 *   same 7,353-byte length-equivalent signing transcript.
 *
 * Operations:
 *   KEYGEN       ECDSA-P256 key pair                              (n = 20)
 *   SIGN_DIGEST  ECDSA sign of a 32-byte SHA-256 digest           (n = 500)  ~ "core sign"
 *   FRAME_SIGN   SHA-256 over the 7,353-byte transcript + sign    (n = 500)  ~ "framework sign"
 *   VERIFY       ECDSA verify of the 32-byte digest               (n = 500)
 *   SHA256_7353  SHA-256 over the transcript only                 (n = 200)
 *
 * NOTE: ML-DSA framework signing uses SHAKE256 over the transcript, ECDSA uses
 * SHA-256. The comparison is therefore "classical stack vs PQ stack", not
 * "same hash".
 */

#define N_KEYGEN        20
#define N_SIGN         500
#define N_FRAME_SIGN   500
#define N_VERIFY       500
#define N_HASH         200

#define MSG_LEN        100
#define PK_BYTES      1952
#define SIG_BYTES     3309
#define FRAME_SIGN_INPUT_LEN (16 + MSG_LEN + PK_BYTES + 16 + PK_BYTES + SIG_BYTES + 8) /* 7353 */
#define BENCH_STACK   (32 * 1024)

static uint8_t frame_input[FRAME_SIGN_INPUT_LEN];
static uint8_t digest[32];
static uint8_t sigbuf[64];
static uint8_t privkey[32], pubkey[64];
static const struct uECC_Curve_t *curve;
static size_t  siglen;

static double a_keygen[N_KEYGEN], a_sign[N_SIGN], a_frame[N_FRAME_SIGN], a_verify[N_VERIFY], a_hash[N_HASH];

static inline double now_ms() { return (double)esp_timer_get_time() / 1000.0; }

static int rng_cb(uint8_t *out, unsigned len) {
  esp_fill_random(out, len);
  return 1;
}

static int cmp_d(const void *a, const void *b) {
  double x = *(const double *)a, y = *(const double *)b;
  return (x > y) - (x < y);
}

static void stats(const char *name, const double *v, int n) {
  static double tmp[N_SIGN];
  double sum = 0, sumsq = 0, mn = v[0], mx = v[0];
  for (int i = 0; i < n; i++) {
    sum += v[i]; sumsq += v[i] * v[i];
    if (v[i] < mn) mn = v[i];
    if (v[i] > mx) mx = v[i];
    tmp[i] = v[i];
  }
  qsort(tmp, n, sizeof(double), cmp_d);
  double m = sum / n, var = sumsq / n - m * m, sd = var > 0 ? sqrt(var) : 0;
  auto pct = [&](double p) {
    double pos = p * (n - 1); int lo = (int)floor(pos), hi = (int)ceil(pos);
    return lo == hi ? tmp[lo] : tmp[lo] * (1 - (pos - lo)) + tmp[hi] * (pos - lo);
  };
  Serial.printf("%-14s n=%d mean=%.6f sd=%.6f min=%.6f median=%.6f p95=%.6f p99=%.6f max=%.6f ms\n",
                name, n, m, sd, mn, pct(0.5), pct(0.95), pct(0.99), mx);
}

static void benchTask(void *arg) {
  (void)arg;
  curve = uECC_secp256r1();
  uECC_set_rng(&rng_cb);

  esp_fill_random(frame_input, sizeof(frame_input));
  Serial.printf("[ECDSA] transcript input = %d bytes\n", (int)FRAME_SIGN_INPUT_LEN);

  /* [1/5] keygen */
  Serial.printf("[1/5] ECDSA-P256 keygen n=%d\n", N_KEYGEN);
  for (int i = 0; i < N_KEYGEN; i++) {
    double t0 = now_ms();
    int rc = uECC_make_key(pubkey, privkey, curve) ? 0 : -1;
    double dt = now_ms() - t0;
    if (rc != 0) { Serial.printf("KEYGEN_FAIL,%d,%d\n", i, rc); vTaskDelete(NULL); return; }
    a_keygen[i] = dt;
    Serial.printf("KG,%d,%.6f\n", i, dt);
    vTaskDelay(5);
  }
  /* privkey/pubkey hold the last generated key, used for all later operations */

  mbedtls_sha256(frame_input, 32, digest, 0); /* digest for the 32-byte-digest cases */

  /* [2/5] sign of a 32-byte digest */
  Serial.printf("[2/5] ECDSA sign (32-byte digest) n=%d\n", N_SIGN);
  for (int i = 0; i < N_SIGN; i++) {
    double t0 = now_ms();
    int rc = uECC_sign(privkey, digest, sizeof(digest), sigbuf, curve) ? 0 : -1; siglen = 64;
    double dt = now_ms() - t0;
    if (rc != 0) { Serial.printf("SIGN_FAIL,%d,%d\n", i, rc); vTaskDelete(NULL); return; }
    a_sign[i] = dt;
    Serial.printf("S,%d,%.6f\n", i, dt);
    vTaskDelay(5);
  }
  Serial.printf("[ECDSA] raw r||s signature length (last) = %d bytes\n", (int)siglen);

  /* [3/5] framework-equivalent sign: SHA-256 over transcript + sign */
  Serial.printf("[3/5] ECDSA framework sign (SHA-256 over %d B + sign) n=%d\n", (int)FRAME_SIGN_INPUT_LEN, N_FRAME_SIGN);
  for (int i = 0; i < N_FRAME_SIGN; i++) {
    double t0 = now_ms();
    mbedtls_sha256(frame_input, sizeof(frame_input), digest, 0);
    int rc = uECC_sign(privkey, digest, sizeof(digest), sigbuf, curve) ? 0 : -1; siglen = 64;
    double dt = now_ms() - t0;
    if (rc != 0) { Serial.printf("FSIGN_FAIL,%d,%d\n", i, rc); vTaskDelete(NULL); return; }
    a_frame[i] = dt;
    Serial.printf("F,%d,%.6f\n", i, dt);
    vTaskDelay(5);
  }

  /* [4/5] verify (valid signature over the current digest) + one negative control */
  Serial.printf("[4/5] ECDSA verify (32-byte digest) n=%d\n", N_VERIFY);
  for (int i = 0; i < N_VERIFY; i++) {
    double t0 = now_ms();
    int rc = uECC_verify(pubkey, digest, sizeof(digest), sigbuf, curve) ? 0 : -1;
    double dt = now_ms() - t0;
    if (rc != 0) { Serial.printf("VERIFY_FAIL,%d,%d\n", i, rc); vTaskDelete(NULL); return; }
    a_verify[i] = dt;
    Serial.printf("V,%d,%.6f\n", i, dt);
    vTaskDelay(5);
  }
  uint8_t bad[32]; memcpy(bad, digest, 32); bad[0] ^= 0x01;
  int neg = uECC_verify(pubkey, bad, sizeof(bad), sigbuf, curve) ? 0 : -1;
  Serial.printf("NEGATIVE_CONTROL,tampered_digest_rc=%d,%s\n", neg, neg != 0 ? "REJECTED_OK" : "ACCEPTED_BAD");

  /* [5/5] hashing only */
  Serial.printf("[5/5] SHA-256 over %d B n=%d\n", (int)FRAME_SIGN_INPUT_LEN, N_HASH);
  for (int i = 0; i < N_HASH; i++) {
    double t0 = now_ms();
    mbedtls_sha256(frame_input, sizeof(frame_input), digest, 0);
    a_hash[i] = now_ms() - t0;
    Serial.printf("H,%d,%.6f\n", i, a_hash[i]);
    vTaskDelay(2);
  }

  Serial.println();
  Serial.println("--- SUMMARY ---");
  stats("KEYGEN", a_keygen, N_KEYGEN);
  stats("SIGN_DIGEST", a_sign, N_SIGN);
  stats("FRAME_SIGN", a_frame, N_FRAME_SIGN);
  stats("VERIFY", a_verify, N_VERIFY);
  stats("SHA256_7353", a_hash, N_HASH);
  int over100 = 0; for (int i = 0; i < N_FRAME_SIGN; i++) if (a_frame[i] > 100.0) over100++;
  Serial.printf("FRAME_SIGN_over_100ms=%d/%d\n", over100, N_FRAME_SIGN);
  Serial.printf("heap free=%u min=%u\n", (unsigned)ESP.getFreeHeap(), (unsigned)ESP.getMinFreeHeap());
  Serial.println("ESP32_UECC_BASELINE_OK");

  vTaskDelete(NULL);
}

void setup() {
  Serial.begin(57600);
  delay(2000);
  setCpuFrequencyMhz(240);
  Serial.printf("[PLATFORM] ESP32 | %d MHz | %d core | SDK %s\n",
                (int)getCpuFrequencyMhz(), ESP.getChipCores(), ESP.getSdkVersion());
  Serial.printf("[PLATFORM] flash=%u B heap=%u B\n", (unsigned)ESP.getFlashChipSize(), (unsigned)ESP.getFreeHeap());
  if (xTaskCreate(benchTask, "pqcbas-uecc", BENCH_STACK, NULL, 5, NULL) != pdPASS)
    Serial.println("TASK_CREATE_FAILED");
}

void loop() { vTaskDelay(pdMS_TO_TICKS(1000)); }
