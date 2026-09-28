# RSU-Class Hardware Measurement — Raspberry Pi 5 (2026-09-28)

Raw results backing **Table 5** (Raspberry Pi 5 column), **Table 8** (`tab:rsu`, Agg/AggCheck
across batch sizes), and **Section 7.5 "RSU-Class Hardware Measurement (Raspberry Pi 5)"** of
the manuscript *"What Post-Quantum Authentication Costs in a VANET: Measuring ML-DSA-65 Across
Device Classes in a Certificate-Based Batched-Verification Framework"*.

This run supplied the third measured device class (desktop-class Apple M2 for CA/CS,
microcontroller-class ESP32 for the OBU, embedded Linux-class Raspberry Pi 5 for the RSU),
closing the measurement gap noted in earlier drafts (Figure 4, `hw_role_mapping`).

## Files

| File | Description |
|---|---|
| `rsu_results.csv` | Per-operation and per-batch-size timing (mean, median, std, 95% CI, p95, min, max, per-tuple cost), one row per operation × batch size. |
| `rsu_results_platform.json` | Platform identity and run parameters (hostname, CPU model, core count, Python version, CPU governor, max frequency, thermal-throttle status, CPU temperature, timestamp, algorithm, negative-control result). |
| `console_log.txt` | Console transcript of the run, reconstructed from the operator's terminal session. |

## Platform

| | |
|---|---|
| Device | Raspberry Pi 5 Model B Rev 1.0 |
| SoC / cores | Broadcom BCM2712, 4× ARM Cortex-A76, aarch64 |
| Clock | 2.4 GHz (`scaling_governor=ondemand`) |
| OS | Debian GNU/Linux 12 "bookworm" |
| Python | 3.11.2 |
| liboqs-python | 0.16.0.1 (prebuilt ARM64 wheel from piwheels.org — no source compile required) |
| Algorithm | ML-DSA-65 (FIPS 204) |
| Thermal | `throttled=0x0` (no under-voltage/frequency-capping/throttling), 53.2 °C at run time |

## Method

The same liboqs-backed ML-DSA-65 measurement code path used for the Apple M2 desktop benchmark
(Table 5, Table 6) and the aggregation benchmark (Table 7, `tab:aggbeh`) was executed unmodified
on the Pi 5 — the RSU role requires no embedded/C port, unlike the ESP32 OBU benchmark, because
the Pi runs a full Linux + Python stack identical in kind to the Apple M2 host. Operations were
timed with `n = 200` repetitions (operation-level: keypair generation, the two SHAKE256
domain-separated hashes of Equations (1)-(3), Sign, CertValidate, MsgVerify) and `n = 100`
repetitions per batch size for Agg/AggCheck across `m = 1, 2, 4, 8, 16, 32, 64`. A negative
control (a tampered challenge list, expected to be rejected under the AggCheck conditions of
Equation (26)) was run once and **passed**.

## Headline numbers

| Operation | Raspberry Pi 5 | Apple M2 (Table 5) | ESP32 (Table 6) |
|---|---|---|---|
| CertValidate | 0.129 ± 0.001 ms | 0.054 ± 0.002 ms | 27.673 ± 0.013 ms |
| Sign | 0.320 ± 0.162 ms | 0.117 ± 0.061 ms | 84.436 ± 53.775 ms |
| AggCheck (m = 64) | 9.105 ± 0.017 ms | — (Table 7 stops at m = 10) | not evaluated |

CertValidate on the Pi 5 is 2.4× slower than the Apple M2 host but 215× faster than the ESP32,
placing the RSU feasibility boundary close to the desktop end of the previously reported 512×
span (see Finding E4 and Section 7.5 of the manuscript).

## Reproducing this run

This run used the operator's local copy of the canonical benchmark script (the same measurement
code as `src/bench_pqcbas.py` in this artifact repository, run via the Raspberry Pi path
described in `docs/RPI_GUIDE.md`). If the exact script version used for this run differs from
the one currently checked into `src/`, request the version-matched copy from the corresponding
author; the output schema (`rsu_results.csv` columns, `rsu_results_platform.json` fields) is
stable and documented above regardless of script revision.

## Provenance

Collected by the corresponding author on their own Raspberry Pi 5 hardware and relayed to this
repository for archiving alongside the Apple M2 and ESP32 raw results. Not independently
re-executed by a third party; the negative-control pass and the internal-consistency checks
(Agg and AggCheck both linear in `m`, matching the Apple M2 trend of Table 7) are the available
correctness evidence for this specific run.
