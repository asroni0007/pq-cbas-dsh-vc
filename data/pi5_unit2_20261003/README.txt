Pi 5 unit 2 (second Raspberry Pi 5 Model B Rev 1.0), run of 2026-10-03, 07:15-07:19 WIB (supplementary evidence; NOT pooled with the reported unit-1 data of 2026-09-29)

Purpose: check that the Pi 5 results do not depend on one particular board.
- Unit 1 (host pi13): Revision d04170, serial 3f2cae06d88daa4f.  Unit 2 (host raspberrypi): Revision d04170, serial 337b3bda9c12961a. Same model, 8 GB, NVMe, Debian 12, kernel 6.6.51+rpt-rpi-2712.
- Software: byte-identical liboqs.so.0.16.0 copied from unit 1 (sha256 7ed56984...dde85, verified on unit 2 before the run), same venv package pins as unit 1 (pip freeze in environment.txt), same sources (bench_pqcbas.py, e2e_workflow_full.py, ci_stats.py: sha256 equal to the K384 archive on both units).
- Conditions: governor performance, 2400 MHz in 46/46 thermal samples, throttled=0x0 in 46/46, maximum 67.0 C. Firefox was closed before the run (it had used about 1.0 GB of memory); apt upgraded git 2.39.5-0+deb12u1 -> u3 before the run (unrelated to the benchmark).
- Commands: bench_pqcbas.py; e2e_workflow_full.py --window 90 --seeds 20 [--digest]. Unlike unit 1 there is no 1-seed digest sanity run.
- Edits to the raw files: only environment.txt (user name in one path replaced by USER). SHA256SUMS.txt was regenerated after that edit. The zip as received had sha256 03c3d1f1782c8e267780fa7efc79ef6035b31c5f8199d3d90b84a06c44f00b3e.

Result vs unit 1 (same arrival seeds, so the two E2E runs replay the same traffic):
- Microbenchmark means: CertValidate 0.1364 vs 0.1359 ms (+0.4%), ECDSA-P256 verify 0.1956 vs 0.1956 ms, Setup +0.1%. CertGen -9.9% and Sign -4.6% are within the sampling spread of those long-tailed operations (sd about 0.15 ms) but no test was run.
- E2E mean processing time: +0.0 to +0.5% in all 8 scenario/mode pairs.
- Deadline misses of 142,780 messages: FULL 611 (0.428%) vs 587 (0.411%); DIGEST 22 vs 22.
Scope: the units are the same SKU, board revision and software image, so agreement shows little board-to-board variation for this configuration and says nothing about other CPU classes. The E2E replay shares seeds and measured operation costs, so its agreement is not an independent confirmation beyond the microbenchmark.
