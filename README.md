# PQ-CBAS-DSH — Research Artifact (v1.4.4, final κ = 384 profile)

Reproducible measurement artifact for:

> **What Post-Quantum Authentication Costs in a VANET: Measuring ML-DSA-65 Across Device Classes in a Certificate-Based Batched-Verification Framework**
> Asroni, Selo Sulistyo, Sigit B. Wibowo — submitted to *Vehicular Communications*.

DOI (all versions, always resolves to the latest archived version): https://doi.org/10.5281/zenodo.21805962

## What is where

| Folder | Content |
|---|---|
| `data/` | All data behind the reported numbers (see `data/README_SUPPLEMENTARY.md` for the table-to-source map): final κ = 384 runs on Apple M2, Raspberry Pi 5 and ESP32; Pi 5 repeat with thermal log (1 Oct 2026); liboqs build configurations; final PHY/MAC matrix (120 runs, per-run CSV, cell summaries, sign test); ESP32 ECDSA-P256 baseline logs; ESP32 two-unit data, second Pi 5 run and x86-64 laptop cross-check (3 Oct 2026) |
| `src/` | Final benchmark and harness sources (Python). `transport_budget_STALE_unused.py` is kept for history only |
| `esp32/PQCBAS_ESP32_Final/` | ML-DSA-65 firmware (PQClean commit `0586a824`, arduino-cli 1.5.1, esp32 core 3.3.11) |
| `esp32/PQCBAS_ESP32_ECDSA_baseline/` | ECDSA-P256 (mbedTLS as shipped in the core) sketch, two serial logs, parse script |
| `sumo/` | StudyArea network, demand and SUMO configuration |
| `scripts/`, `docs/` | Run wrappers; Raspberry Pi guide |
| `legacy_v1.2.0_liboqs0.15/` | Superseded v1.2.0 results (liboqs 0.15.0). **Not used for any reported value** |

## Environment of the reported data

Apple M2: liboqs 0.16.0, liboqs-python 0.16.0.1, Python 3.13.15. Raspberry Pi 5: Debian 12, kernel 6.6.51, `performance` governor, Python 3.11.2. ESP32: Arduino-ESP32 core 3.3.11 (SDK v5.5.5). Both liboqs builds are generic distribution builds; the Pi build uses OpenSSL and the M2 build does not; which ML-DSA code path ran at run time was not verified (`data/environment_records/`). Pi-to-M2 ratios therefore compare builds as well as hardware. The x86-64 laptop cross-check used Ubuntu 22.04.5, Python 3.10.12 and a liboqs 0.16.0 built from the same tag with the Pi 5 options (see `data/x86_laptop_20261003/README.txt` for the differences).

## Known limitations of this artifact

- Unit counts: two ESP32 units and two Raspberry Pi 5 units (same model, board revision and software image; the second Pi 5 reproduces the first within 0.5%), one Apple M2. An x86-64 laptop (`data/x86_laptop_20261003/`) is a cross-check only: three runs under a desktop session whose deadline-miss counts differ strongly (full mode 230 to 1,308); two of the runs overlapped with commands issued on the machine and are labeled as deviations.
- Raw OMNeT++/Veins `.sca/.vec` files and the 62 MB SUMO FCD file are not included (checksums are recorded); the per-run PHY/MAC analysis is.
- `scripts/` were updated from liboqs 0.15.0 to 0.16.0 to match the reported data and were not re-run end to end after that change; the reported values come from the archived raw outputs in `data/`.
- ECDSA-P256 on the ESP32 is the unmodified mbedTLS of the core, not an optimized library.

## Integrity

```bash
sha256sum -c SHA256SUMS.txt
```

## Versions

- v1.4.3 (24 Oct 2026): Veins/SUMO reproducibility package for the final 8,694 B PHY/MAC matrix in data/veins_sumo_package_20261024: the recovered application project (30 Sep 2026) and two earlier versions, the 120 rendered run inputs, evidence of one full 120 s smoke run, and hash records of the compiled libraries and the Veins 5.3.1 toolchain tree. Limitations are stated in data/veins_sumo_package_20261024/README_VEINS_PACKAGE.md: the sources are the recovered version, hashes were computed at assembly time, compiled libraries are not deposited, and the raw outputs of the 120 final runs are not included. The v1.4.2 data are unchanged.
- v1.4.4 (25 Oct 2026): Rerun of the complete 120-run Veins/SUMO PHY/MAC matrix (data/veins_sumo_rerun_20261025): runner and comparison scripts, the matrix log, the raw scalar files of all 120 rerun runs (raw_scalars_120runs.tar.gz), the regenerated per-run table and summaries, and reconstructed paired-difference, sign-test and paper tables. The 120-row per-run table, the 12-cell summary and the compact table are identical to the archived ones; the other three tables were reconstructed (their original generating script is not archived) and match. Single host, not repeated on another platform.
- v1.4.2 (24 Oct 2026): Apple M2 CA/CS repeat data (24 Oct 2026) with two documented liboqs 0.16.0 builds: a source build without OpenSSL (build A, SHA-256 prefix 3a9a78ce6916094e) and the Homebrew package linking OpenSSL 4 (build B, SHA-256 prefix f2c030021056e1d6). Three build-A and two build-B runs of the CA/CS extension script (verification comparison, parallel certificate validation, sustained issuance) and six repeats of the unchanged benchmark are in `data/m2_repeat_20261024/`; library paths, hashes, linked libraries and package versions are in `data/environment_records/m2_20261024/`. The M2 ML-DSA-65 verification ratio depends on which liboqs build liboqs-python loads. The Homebrew file is dated 22 Oct 2026, so the build used on 29 Sep 2026 is inferred, not recorded.
- v1.4.0 (3 Oct 2026): adds the ESP32 two-unit data (`data/esp32_two_unit_20261003/`: 12 validated raw serial logs for ML-DSA-65, mbedTLS ECDSA-P256 and micro-ecc ECDSA-P256 on two units, firmware, sketches, recorder and analysis scripts), the second Raspberry Pi 5 run (`data/pi5_unit2_20261003/`), the x86-64 laptop runs (`data/x86_laptop_20261003/`) and the run-time code-path probes (`data/environment_records/runtime_path_probe/`, which the manuscript cites and v1.3.1 lacked). The ESP32 numbers of v1.3.1 and its single-unit ECDSA baseline are superseded.
- v1.4.1 (23 Oct 2026): analysis-only additions (no new measurements): scripts and outputs for the ESP32 repetition-lattice sign-tail mechanism, the PHY/MAC fragment-independence check, the between-run verification-ratio spread and a 15-number recompute audit; plus the Veins 5.3.1 MAC-metrics patch (a reconstruction, not byte-identical to the original) with provenance records in `data/phymac_final_8694_20261001/veins_macmetrics/`.
- v1.3.1 (2 Oct 2026): complete release: final κ = 384 data, Pi 5 repeat, build configurations, final PHY/MAC matrix, ESP32 ECDSA baseline.
- v1.3.0 (DOI 10.5281/zenodo.23085005): archive was created from an earlier commit and is incomplete; superseded by v1.3.1.
- v1.0.0 (DOI 10.5281/zenodo.21805963) and v1.2.0: earlier liboqs 0.15.0 results; superseded.

## License

MIT, see `LICENSE`.
