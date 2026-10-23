# Supplementary material — PQ-CBAS-DSH (round 14, final κ = 384 profile)

All numbers in the paper come from `final_k384_20260929/` (final profile: 48 B hash
outputs, full wire object 8,694 B, digest object 3,465 B), except the PHY/MAC
study. NOTE: `tables/` and `final_k384_20260929/phymac_processed/` still hold the LEGACY 10,662 B run; the final canonical-wire matrix (8,694 B full) reported in Section 7.13 must be added here (pending upload of its processed archive). The earlier κ = 256 data are kept unmodified in
`legacy_k256_20260928/` and are not used for any reported value.

## Contents
- `final_k384_20260929/mac_sumo/` — Apple M2 benchmark (`stack_B/bench_results_k384.json`), E2E
  full-path harness output (20 seeds, both modes), SUMO 1.26.0 controlled run (`sumo/primary_126`;
  the 62 MB FCD file is omitted, its checksum is in that folder's `SHA256SUMS.txt`), SUMO full-path
  E2E (`sumo/fullpath`), cross-device tables and plot sources.
- `final_k384_20260929/pi5/` — Raspberry Pi 5 benchmark, E2E full path (20 seeds, both modes),
  environment and pip freeze (liboqs 0.16.0, Python 3.11.2, governor `performance`; thermal state
  was not recorded).
- `pi5_unit2_20261003/` — run of a **second Raspberry Pi 5** (same model and board revision, different serial) with the byte-identical liboqs file and package pins: micro-benchmark, end-to-end full/digest (20 seeds), 5-s thermal log; agrees with unit 1 within 0.5% (see its `README.txt`; supplementary, not pooled).
- `x86_laptop_20261003/` — **x86-64 laptop cross-check** (Core i7-6500U, Ubuntu 22.04.5): three runs (`run1_DEVIATION`, `run2_DEVIATION`, `run3_REPORTED`), environment records, thermal/frequency/AC logs; run 3 is the reported run, runs 1 and 2 overlapped with commands issued on the machine and are kept with all values. Miss counts vary 230-1,308 (full mode) between runs; see its `README.txt`. Run-time path probe: `environment_records/runtime_path_probe/x86_probe_output_excerpt.txt`.
- `esp32_two_unit_20261003/` — **current ESP32 data**: 12 validated raw serial logs (ML-DSA-65, mbedTLS ECDSA-P256, micro-ecc ECDSA-P256; two units, two runs each) with MAC records, firmware binaries and hashes, sketches, recorder scripts, the analysis script that regenerates `tab:esp32` and `fig:esp32budget`, and the statistics (`analysis/stats_final.{json,txt}`). `analysis/compose_obu_to_verdict.py` composes the measured signing samples with the collection-window wait (Table `tab:composed`, Section 7.9); its output is `analysis/compose_obu_to_verdict_output.txt`. It supersedes the single-unit ESP32 data below; see its `README.md`.
- `final_k384_20260929/esp32/` — (superseded by the folder above, kept unmodified) firmware sources (PQClean commit 0586a824…), serial logs
  (`final/esp32_final_success_run.log` with RAW_SIGN, RAW_FRAME_SIGN, RAW_VERIFY samples; the log
  holds 498 of the 500 verification samples, the on-device summary covers 500), audit and
  diagnostic files. Build artifacts and logs over 2 MB are omitted.
- `final_k384_20260929/mac_src/` — benchmark and harness sources. `transport_budget.py` there is
  stale (10,662 B, 25 vehicles) and unused.
- `final_k384_20260929/phymac_processed/` and `tables/` — processed 120-run PHY/MAC results
  (identical files). The 324 MB raw legacy PHY/MAC archive is not included (SHA-256
  0ed015e55e05de963c3cdb88210ee2b43d66c52d29bf…6bf6 as uploaded).
- `final_k384_20260929/SHA256SUMS_ARCHIVE_ROOT.txt` — checksums of the files copied here.
- `legacy_k256_20260928/` — earlier κ = 256 Raspberry Pi data (historical, unmodified).
- `security_experiments_v2.py/json` — earlier security-experiment script (superseded by the
  `security` block of each `bench_results_k384.json`).
- `StudyAreNetwork.net.xml`, `macmetrics_confirmatory.pdf` — SUMO network and Figure 7 source.

## Table → source map
Operation and aggregation tables: `bench_results_k384.json` (M2, Pi 5). ESP32 table and budget figure: `esp32_two_unit_20261003/` (12 raw logs; `analysis/analyze_esp32.py` recomputes every value from the raw samples; bootstrap 20,000 resamples, seed 20261003; Wilson CIs). The single-unit serial log of 29 September is superseded and not used for any ESP32 number in the paper.
E2E tables: `e2e_fullpath_W90_{full,digest}_20seeds.json` (M2, Pi 5). SUMO table: `sumo/fullpath`.
Transport table: Little's law N = 42.1739 from `primary_126/mobility_validation.json`.

## PHY/MAC final matrix (added 2026-10-01, round 16)
- `phymac_final_8694_20261001/` holds the final-profile matched 120-run PHY/MAC analysis
  (SMALL 300 B / DIGEST 3,465 B / FULL 8,694 B; targets 10/25/50/100; seeds 1-10; 6 Mbit/s, 10 Hz, 120 s):
  per-run CSV (`P0-7_FINAL_120_RUNS.csv`), 12-cell summary, paper table, paired differences,
  exact sign tests, extraction audit, analysis script, run matrix and preparation provenance.
- `tables/` now contains these final tables. The manuscript's Table `tab:macconfirm`, the Appendix
  sign-audit table and the headline ranges were re-derived from the per-run CSV (SHA-256 of the
  per-run, cell-summary and paired-difference files match `P0-7_FINAL_SHA256.txt`).
- `legacy_phymac_tables/` keeps the earlier (10,662 B FULL) tables for traceability only; they are
  NOT used in the manuscript.
- Raw `.sca/.vec` runs, rendered ini files and logs of the final matrix are not included in this
  folder (large); they remain on the authors' archive and are to be deposited with the DOI release.

## Environment records (round 16)
`environment_records/` keeps the Pi 5 and M2 software/hardware snapshots (OS, kernel, CPU max 2.4 GHz and
`performance` governor on the Pi, Python, liboqs 0.16.0, liboqs-python 0.16.0.1, pip freeze).
liboqs build headers (oqsconfig.h) are recorded for both hosts (liboqs_build_config_*.txt): generic distribution builds with the aarch64 ML-DSA
variants compiled in; the Pi build uses OpenSSL (OQS_USE_OPENSSL=1), the M2 build does not. Not verified: which ML-DSA implementation executes at
run time. Pi 5 temperature / throttling was not logged in the reported 29 Sep run (see pi5_repeat_20261001/ for the logged repeat).

## Pi 5 logged repeat (round 16)
`pi5_repeat_20261001/` documents an independent repeat of the Pi 5 end-to-end harness with a 5-s thermal/throttling log
(no throttling, max 67.0 C, 2.4 GHz throughout). It is supplementary and is not pooled with the reported 29 September data.

Analysis-only scripts added in v1.4.1 (no new measurements): `esp32_two_unit_20261003/analysis/sign_tail_mechanism.py` (repetition-lattice and geometric fit of the ESP32 signing tail), `phymac_final_8694_20261001/fragment_independence_check.py` (observed completion vs. independent-loss prediction p^n), , `ratio_between_run_spread.py` (per-run ECDSA/ML-DSA verification ratios across all archived benchmark runs), and `recompute_audit.py` (recomputes headline numbers from raw files; prints `mismatches: 0`). Each has a saved `*_output.txt`.

ESP32 source-hash note: every ESP32 number in the paper comes from `esp32_two_unit_20261003/` (flashed sketch `sketches/src_final.ino`, SHA-256 prefix ab6d071d, firmware image `fw_final.bin`; the same sketch is also in `final_k384_20260929/esp32/firmware_src/`). The earlier single-unit record `final_k384_20260929/esp32/final/SOURCE_SHA256.txt` lists a different sketch hash (prefix b4c4fb62) that could not be reconciled with an archived file; no paper number is taken from that record.

## Veins MAC-metrics patch (added 2026-10-23)
- `phymac_final_8694_20261001/veins_macmetrics/` holds the patch to two Veins 5.3.1 files (`Mac1609_4.cc`, `Mac1609_4.h`) used for the final 120-run PHY/MAC matrix, and its provenance record. The patch only records statistics (queue-delay and queue-occupancy counters; no random numbers, no scheduling or queue-behaviour change). The original patched source was lost; this patch is a **reconstruction** and is not byte-identical to the original. Applied with `patch -p1` to the upstream `veins-5.3.1` tree it reproduces the patched SHA-256 values listed in `PROVENANCE.txt`. All 120 final raw result files were generated after the reconstruction (30 Sep 2026 22:02 to 1 Oct 2026 00:23).

## Harness scripts used for the final PHY/MAC matrix (added 2026-10-23)
- `phymac_final_8694_20261001/` was run with the harness scripts in its `source_snapshot/scripts/`. Their SHA-256 values for `env_mac_standalone.sh` (`6da82c82…`) and `preflight_mac_standalone.sh` (`ed8ad879…`) equal those of the first (V1) standalone package, not the later V2 fix. V2 only makes the environment script robust when the caller enables `set -u` and adds a package-location check in the preflight script; it changes no simulation setting, library, seed or path, so no reported value depends on it.
