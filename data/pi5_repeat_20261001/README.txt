Pi 5 repeat of the full-path E2E harness, 2026-10-01 (supplementary evidence, NOT pooled with the reported 2026-09-29 data)
- Host: same Raspberry Pi 5 (pi13), rebooted 2026-10-01 08:57:24; governor re-set to `performance` by hand before the run.
- Software: venv pqcbas-final-pi, liboqs 0.16.0 (~/_oqs), Python 3.11.2; command
  python src/e2e_workflow_full.py --window 90 --seeds 20 [--digest]   (run 09:04:34-09:08:05 WIB)
- Thermal log: vcgencmd measure_temp / get_throttled / measure_clock arm every 5 s, 09:01:40-09:08:42 WIB:
  85 samples, max 67.0 C, throttled=0x0 in 85/85, 2400 MHz in 85/85.
- Result vs reported run: mean processing times within 0.6%; deadline misses FULL 613 (0.429%) vs 587 (0.411%),
  DIGEST 23 (0.016%) vs 22 (0.015%) out of 142,780 messages each.
- Included here: raw_repeat_20261001/ (rerun JSON for both modes, console logs, 5-s thermal log, microbenchmark JSON), the console
  transcript, and original_29sep_copies/ (the reported run's JSON, byte-identical to the K384 archive). SHA256SUMS.txt covers all files.
  Of the 85 thermal samples (09:01:40-09:08:42), 42 fall inside the E2E runs (09:04:34-09:08:05); max in that window 67.0 C.
- An unintended extra run of src/bench_pqcbas.py (09:03:30, triggered by --help) is kept as bench_results_rerun_20261001.json:
  CertValidate 0.1365 +/- 0.0028 ms, ECDSA-P256 verify 0.1955 ms, Setup 0.1357 ms (reported: 0.136 / 0.196 / 0.135 ms).
