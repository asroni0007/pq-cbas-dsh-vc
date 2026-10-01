#include <Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <esp_timer.h>
#include <esp_system.h>
#include <esp_random.h>

extern "C" {
  #include "src/api.h"
  #include "src/fips202.h"
}

#include "src/pqclean_commit.h"

/*
 * PQ-CBAS-DSH ESP32 FINAL BENCHMARK
 *
 * Algorithm       : ML-DSA-65
 * PQ-CBAS profile : kappa = 384 bit = 48 bytes
 *
 * RAW_SIGN:
 *   ML-DSA signing of the 48-byte PQ-CBAS-DSH digest.
 *
 * RAW_FRAME_SIGN:
 *   framework-side SHAKE256 domain-separated hashing over a
 *   length-equivalent signing transcript, followed by ML-DSA signing.
 *
 * RAW_VERIFY:
 *   ML-DSA verification of a 48-byte digest.
 *
 * SEQ_VERIFY:
 *   m independent ML-DSA verifications performed sequentially.
 *   This is NOT PQ-CBAS AggVerify.
 */

#define N_KEYPAIR      20
#define N_SIGN        500
#define N_FRAME_SIGN  500
#define N_VERIFY      500
#define N_DSH         200

#define N_SEQ          10
#define MAX_BATCH      10

#define MSG_LEN       100
#define KAPPA_BYTES    48
#define BENCH_STACK   (96 * 1024)

#define PK_BYTES \
  PQCLEAN_MLDSA65_CLEAN_CRYPTO_PUBLICKEYBYTES

#define SK_BYTES \
  PQCLEAN_MLDSA65_CLEAN_CRYPTO_SECRETKEYBYTES

#define SIG_BYTES \
  PQCLEAN_MLDSA65_CLEAN_CRYPTO_BYTES

#define KEYPAIR \
  PQCLEAN_MLDSA65_CLEAN_crypto_sign_keypair

#define SIGNATURE \
  PQCLEAN_MLDSA65_CLEAN_crypto_sign_signature

#define VERIFYSIG \
  PQCLEAN_MLDSA65_CLEAN_crypto_sign_verify

/*
 * Current framework signing input:
 * ID || m || pk || cert.ID || cert.pk || cert.gamma || freshness
 *
 * 16 + 100 + 1952 + 16 + 1952 + 3309 + 8 = 7353 bytes.
 *
 * The buffer below is length-equivalent for timing the SHAKE256
 * preprocessing cost. It is not claimed to be a serialized certificate.
 */
#define FRAME_SIGN_INPUT_LEN \
  (16 + MSG_LEN + PK_BYTES + 16 + PK_BYTES + SIG_BYTES + 8)

static const char DOM_SIGN[] =
  "PQ-CBAS-DSH/SIGN";

static uint8_t pk[MAX_BATCH][PK_BYTES];
static uint8_t sig[MAX_BATCH][SIG_BYTES];
static uint8_t mu[MAX_BATCH][KAPPA_BYTES];

static uint8_t sk_buf[SK_BYTES];
static uint8_t msg[MSG_LEN];

static uint8_t frame_input[FRAME_SIGN_INPUT_LEN];

static size_t siglen[MAX_BATCH];

static double raw_sign[N_SIGN];
static double raw_frame_sign[N_FRAME_SIGN];
static double raw_verify[N_VERIFY];

static double pct_buf[
  (N_SIGN > N_VERIFY ? N_SIGN : N_VERIFY)
];

typedef struct {
  double mn;
  double mx;
  double sum;
  double sumsq;
  int n;
} stat_t;

static void st_add(stat_t *s, double v) {
  if (s->n == 0 || v < s->mn) s->mn = v;
  if (s->n == 0 || v > s->mx) s->mx = v;

  s->sum += v;
  s->sumsq += v * v;
  s->n++;
}

static double st_mean(const stat_t *s) {
  return s->n ? s->sum / s->n : 0.0;
}

static double st_sd(const stat_t *s) {
  if (s->n < 2) return 0.0;

  double m = st_mean(s);
  double v = s->sumsq / s->n - m * m;

  return v > 0.0 ? sqrt(v) : 0.0;
}

static inline double now_ms() {
  return (double)esp_timer_get_time() / 1000.0;
}

static void dsh(
  const char *dom,
  size_t dlen,
  const uint8_t *in,
  size_t inlen,
  uint8_t *out,
  size_t outlen
) {
  shake256incctx ctx;

  shake256_inc_init(&ctx);
  shake256_inc_absorb(
    &ctx,
    (const uint8_t *)dom,
    dlen
  );
  shake256_inc_absorb(
    &ctx,
    in,
    inlen
  );
  shake256_inc_finalize(&ctx);
  shake256_inc_squeeze(
    out,
    outlen,
    &ctx
  );
  shake256_inc_ctx_release(&ctx);
}

static int cmp_double(
  const void *a,
  const void *b
) {
  double x = *(const double *)a;
  double y = *(const double *)b;

  if (x < y) return -1;
  if (x > y) return 1;
  return 0;
}

static double percentile(
  const double *values,
  int n,
  double p
) {
  if (n <= 0) return 0.0;

  for (int i = 0; i < n; i++) {
    pct_buf[i] = values[i];
  }

  qsort(
    pct_buf,
    n,
    sizeof(double),
    cmp_double
  );

  double pos = p * (n - 1);
  int lo = (int)floor(pos);
  int hi = (int)ceil(pos);

  if (lo == hi) return pct_buf[lo];

  double f = pos - lo;

  return pct_buf[lo] * (1.0 - f)
       + pct_buf[hi] * f;
}

static void print_stats(
  const char *name,
  const stat_t *s,
  const double *raw,
  int n
) {
  Serial.printf(
    "%-18s n=%d mean=%.6f sd=%.6f "
    "min=%.6f p95=%.6f p99=%.6f max=%.6f ms\n",
    name,
    n,
    st_mean(s),
    st_sd(s),
    s->mn,
    percentile(raw, n, 0.95),
    percentile(raw, n, 0.99),
    s->mx
  );
}

static void benchTask(void *arg) {
  (void)arg;

  stat_t s_kp = {};
  stat_t s_dsh = {};
  stat_t s_sign = {};
  stat_t s_frame_sign = {};
  stat_t s_verify = {};

  stat_t s_seq[MAX_BATCH + 1];
  memset(s_seq, 0, sizeof(s_seq));

  Serial.println();
  Serial.println(
    "=============================================="
  );
  Serial.println(
    " PQ-CBAS-DSH ESP32 FINAL BENCHMARK"
  );
  Serial.println(
    "=============================================="
  );

  Serial.printf(
    "PQClean commit : %s\n",
    PQCLEAN_COMMIT
  );

  Serial.printf(
    "Algorithm      : ML-DSA-65\n"
  );

  Serial.printf(
    "kappa          : 384 bit / %d B\n",
    KAPPA_BYTES
  );

  Serial.printf(
    "pk/sk/sig      : %d / %d / %d B\n",
    PK_BYTES,
    SK_BYTES,
    SIG_BYTES
  );

  Serial.printf(
    "frame input    : %d B\n",
    FRAME_SIGN_INPUT_LEN
  );

  Serial.printf(
    "CPU            : %d MHz\n\n",
    (int)getCpuFrequencyMhz()
  );

  for (int i = 0; i < MSG_LEN; i++) {
    msg[i] = (uint8_t)(i & 0xFF);
  }

  for (int i = 0; i < FRAME_SIGN_INPUT_LEN; i++) {
    frame_input[i] =
      (uint8_t)((i * 131 + 17) & 0xFF);
  }

  /* ---------- keypair ---------- */

  Serial.printf(
    "[1/6] keypair n=%d\n",
    N_KEYPAIR
  );

  for (int i = 0; i < N_KEYPAIR; i++) {
    double t0 = now_ms();

    int rc = KEYPAIR(
      pk[0],
      sk_buf
    );

    double dt = now_ms() - t0;

    if (rc != 0) {
      Serial.printf(
        "KEYPAIR_FAIL,%d,%d\n",
        i,
        rc
      );
      vTaskDelete(NULL);
      return;
    }

    st_add(&s_kp, dt);
    vTaskDelay(1);
  }

  /* ---------- DSH κ=384 ---------- */

  Serial.printf(
    "[2/6] SHAKE256 DSH n=%d input=%d B output=%d B\n",
    N_DSH,
    FRAME_SIGN_INPUT_LEN,
    KAPPA_BYTES
  );

  for (int i = 0; i < N_DSH; i++) {
    double t0 = now_ms();

    dsh(
      DOM_SIGN,
      sizeof(DOM_SIGN) - 1,
      frame_input,
      FRAME_SIGN_INPUT_LEN,
      mu[0],
      KAPPA_BYTES
    );

    st_add(
      &s_dsh,
      now_ms() - t0
    );
  }

  /* Prepare valid digest. */

  dsh(
    DOM_SIGN,
    sizeof(DOM_SIGN) - 1,
    frame_input,
    FRAME_SIGN_INPUT_LEN,
    mu[0],
    KAPPA_BYTES
  );

  /* ---------- ML-DSA core sign ---------- */

  Serial.printf(
    "[3/6] ML-DSA sign core n=%d\n",
    N_SIGN
  );

  for (int i = 0; i < N_SIGN; i++) {
    double t0 = now_ms();

    int rc = SIGNATURE(
      sig[0],
      &siglen[0],
      mu[0],
      KAPPA_BYTES,
      sk_buf
    );

    double dt = now_ms() - t0;

    if (rc != 0) {
      Serial.printf(
        "SIGN_FAIL,%d,%d\n",
        i,
        rc
      );
      vTaskDelete(NULL);
      return;
    }

    raw_sign[i] = dt;
    st_add(&s_sign, dt);

    vTaskDelay(1);
  }

  /* ---------- framework Sign ---------- */

  Serial.printf(
    "[4/6] framework sign n=%d\n",
    N_FRAME_SIGN
  );

  for (int i = 0; i < N_FRAME_SIGN; i++) {
    double t0 = now_ms();

    dsh(
      DOM_SIGN,
      sizeof(DOM_SIGN) - 1,
      frame_input,
      FRAME_SIGN_INPUT_LEN,
      mu[0],
      KAPPA_BYTES
    );

    int rc = SIGNATURE(
      sig[0],
      &siglen[0],
      mu[0],
      KAPPA_BYTES,
      sk_buf
    );

    double dt = now_ms() - t0;

    if (rc != 0) {
      Serial.printf(
        "FRAME_SIGN_FAIL,%d,%d\n",
        i,
        rc
      );
      vTaskDelete(NULL);
      return;
    }

    raw_frame_sign[i] = dt;
    st_add(&s_frame_sign, dt);

    vTaskDelay(1);
  }

  /* ---------- verify ---------- */

  Serial.printf(
    "[5/6] verify n=%d\n",
    N_VERIFY
  );

  for (int i = 0; i < N_VERIFY; i++) {
    double t0 = now_ms();

    int rc = VERIFYSIG(
      sig[0],
      siglen[0],
      mu[0],
      KAPPA_BYTES,
      pk[0]
    );

    double dt = now_ms() - t0;

    if (rc != 0) {
      Serial.printf(
        "VERIFY_FAIL,%d,%d\n",
        i,
        rc
      );
      vTaskDelete(NULL);
      return;
    }

    raw_verify[i] = dt;
    st_add(&s_verify, dt);

    vTaskDelay(1);
  }

  /* ---------- sequential verification ---------- */

  Serial.println(
    "[6/6] sequential verify m=1,2,5,10"
  );

  for (int i = 0; i < MAX_BATCH; i++) {
    int rc = KEYPAIR(
      pk[i],
      sk_buf
    );

    if (rc != 0) {
      Serial.printf(
        "SEQ_KEYPAIR_FAIL,%d,%d\n",
        i,
        rc
      );
      vTaskDelete(NULL);
      return;
    }

    msg[0] = (uint8_t)i;

    dsh(
      DOM_SIGN,
      sizeof(DOM_SIGN) - 1,
      msg,
      MSG_LEN,
      mu[i],
      KAPPA_BYTES
    );

    rc = SIGNATURE(
      sig[i],
      &siglen[i],
      mu[i],
      KAPPA_BYTES,
      sk_buf
    );

    if (rc != 0) {
      Serial.printf(
        "SEQ_SIGN_FAIL,%d,%d\n",
        i,
        rc
      );
      vTaskDelete(NULL);
      return;
    }

    vTaskDelay(1);
  }

  const int sizes[] = {
    1, 2, 5, 10
  };

  for (int si = 0; si < 4; si++) {
    int m = sizes[si];

    for (int r = 0; r < N_SEQ; r++) {
      double t0 = now_ms();

      bool ok = true;

      for (int i = 0; i < m; i++) {
        if (
          VERIFYSIG(
            sig[i],
            siglen[i],
            mu[i],
            KAPPA_BYTES,
            pk[i]
          ) != 0
        ) {
          ok = false;
          break;
        }
      }

      double dt = now_ms() - t0;

      if (!ok) {
        Serial.printf(
          "SEQ_VERIFY_FAIL,%d,%d\n",
          m,
          r
        );
        vTaskDelete(NULL);
        return;
      }

      st_add(
        &s_seq[m],
        dt
      );

      vTaskDelay(1);
    }
  }

  Serial.println();
  Serial.println("--- SUMMARY ---");

  Serial.printf(
    "keypair            mean=%.6f sd=%.6f "
    "min=%.6f max=%.6f ms\n",
    st_mean(&s_kp),
    st_sd(&s_kp),
    s_kp.mn,
    s_kp.mx
  );

  Serial.printf(
    "DSH-48             mean=%.6f sd=%.6f "
    "min=%.6f max=%.6f ms\n",
    st_mean(&s_dsh),
    st_sd(&s_dsh),
    s_dsh.mn,
    s_dsh.mx
  );

  print_stats(
    "sign-core",
    &s_sign,
    raw_sign,
    N_SIGN
  );

  print_stats(
    "framework-sign",
    &s_frame_sign,
    raw_frame_sign,
    N_FRAME_SIGN
  );

  print_stats(
    "verify",
    &s_verify,
    raw_verify,
    N_VERIFY
  );

  Serial.println();
  Serial.println(
    "--- SEQUENTIAL VERIFY (not AggVerify) ---"
  );

  for (int si = 0; si < 4; si++) {
    int m = sizes[si];

    Serial.printf(
      "m=%d n=%d mean=%.6f sd=%.6f "
      "min=%.6f max=%.6f ms per_tuple=%.6f ms\n",
      m,
      s_seq[m].n,
      st_mean(&s_seq[m]),
      st_sd(&s_seq[m]),
      s_seq[m].mn,
      s_seq[m].mx,
      st_mean(&s_seq[m]) / m
    );
  }

  Serial.println();
  Serial.println("--- RAW SIGN CORE ---");

  for (int i = 0; i < N_SIGN; i++) {
    Serial.printf(
      "RAW_SIGN,%d,%.6f\n",
      i,
      raw_sign[i]
    );
  }

  Serial.println();
  Serial.println("--- RAW FRAMEWORK SIGN ---");

  for (int i = 0; i < N_FRAME_SIGN; i++) {
    Serial.printf(
      "RAW_FRAME_SIGN,%d,%.6f\n",
      i,
      raw_frame_sign[i]
    );
  }

  Serial.println();
  Serial.println("--- RAW VERIFY ---");

  for (int i = 0; i < N_VERIFY; i++) {
    Serial.printf(
      "RAW_VERIFY,%d,%.6f\n",
      i,
      raw_verify[i]
    );
  }

  Serial.println();
  Serial.println("--- FINAL JSON ---");

  Serial.printf(
    "{"
    "\"platform\":\"esp32\","
    "\"algorithm\":\"ML-DSA-65\","
    "\"pqclean_commit\":\"%s\","
    "\"cpu_mhz\":%d,"
    "\"kappa_bytes\":%d,"
    "\"pk_bytes\":%d,"
    "\"sk_bytes\":%d,"
    "\"sig_bytes\":%d,"
    "\"frame_sign_input_bytes\":%d,"
    "\"n_sign\":%d,"
    "\"n_frame_sign\":%d,"
    "\"n_verify\":%d,"
    "\"sign_core_mean_ms\":%.6f,"
    "\"sign_core_sd_ms\":%.6f,"
    "\"sign_core_p95_ms\":%.6f,"
    "\"sign_core_p99_ms\":%.6f,"
    "\"sign_core_max_ms\":%.6f,"
    "\"framework_sign_mean_ms\":%.6f,"
    "\"framework_sign_sd_ms\":%.6f,"
    "\"framework_sign_p95_ms\":%.6f,"
    "\"framework_sign_p99_ms\":%.6f,"
    "\"framework_sign_max_ms\":%.6f,"
    "\"verify_mean_ms\":%.6f,"
    "\"verify_sd_ms\":%.6f,"
    "\"verify_p95_ms\":%.6f,"
    "\"verify_p99_ms\":%.6f,"
    "\"verify_max_ms\":%.6f,"
    "\"heap_free\":%u,"
    "\"heap_min\":%u"
    "}\n",
    PQCLEAN_COMMIT,
    (int)getCpuFrequencyMhz(),
    KAPPA_BYTES,
    PK_BYTES,
    SK_BYTES,
    SIG_BYTES,
    FRAME_SIGN_INPUT_LEN,
    N_SIGN,
    N_FRAME_SIGN,
    N_VERIFY,
    st_mean(&s_sign),
    st_sd(&s_sign),
    percentile(raw_sign, N_SIGN, 0.95),
    percentile(raw_sign, N_SIGN, 0.99),
    s_sign.mx,
    st_mean(&s_frame_sign),
    st_sd(&s_frame_sign),
    percentile(
      raw_frame_sign,
      N_FRAME_SIGN,
      0.95
    ),
    percentile(
      raw_frame_sign,
      N_FRAME_SIGN,
      0.99
    ),
    s_frame_sign.mx,
    st_mean(&s_verify),
    st_sd(&s_verify),
    percentile(raw_verify, N_VERIFY, 0.95),
    percentile(raw_verify, N_VERIFY, 0.99),
    s_verify.mx,
    (unsigned)ESP.getFreeHeap(),
    (unsigned)ESP.getMinFreeHeap()
  );

  Serial.println();
  Serial.println("ESP32_FINAL_BENCHMARK_OK");

  vTaskDelete(NULL);
}

void setup() {
  Serial.begin(57600);
  delay(2000);

  setCpuFrequencyMhz(240);

  Serial.printf(
    "[PLATFORM] ESP32 | %d MHz | %d core | SDK %s\n",
    (int)getCpuFrequencyMhz(),
    ESP.getChipCores(),
    ESP.getSdkVersion()
  );

  Serial.printf(
    "[PLATFORM] flash=%u B heap=%u B\n",
    (unsigned)ESP.getFlashChipSize(),
    (unsigned)ESP.getFreeHeap()
  );

  BaseType_t rc = xTaskCreate(
    benchTask,
    "pqcbas-final",
    BENCH_STACK,
    NULL,
    5,
    NULL
  );

  if (rc != pdPASS) {
    Serial.printf(
      "TASK_CREATE_FAILED rc=%d\n",
      (int)rc
    );
  }
}

void loop() {
  vTaskDelay(
    pdMS_TO_TICKS(1000)
  );
}
