# PQ-CBAS-DSH — Research Artifact (v1.3.0, final κ = 384 profile)

Reproducible measurement artifact for:

> **What Post-Quantum Authentication Costs in a VANET: Measuring ML-DSA-65 Across Device Classes in a Certificate-Based Batched-Verification Framework**
> Asroni, Selo Sulistyo, Sigit B. Wibowo — submitted to *Vehicular Communications*.

DOI: add the version DOI that Zenodo issues for release `v1.3.0` (the earlier DOI 10.5281/zenodo.21805963 archives v1.2.0, see "Versions").

## What is where

| Folder | Content |
|---|---|
| `data/` | All data behind the reported numbers (see `data/README_SUPPLEMENTARY.md` for the table-to-source map): final κ = 384 runs on Apple M2, Raspberry Pi 5 and ESP32; Pi 5 repeat with thermal log (1 Oct 2026); liboqs build configurations; final PHY/MAC matrix (120 runs, per-run CSV, cell summaries, sign test); ESP32 ECDSA-P256 baseline logs |
| `src/` | Final benchmark and harness sources (Python). `transport_budget_STALE_unused.py` is kept for history only |
| `esp32/PQCBAS_ESP32_Final/` | ML-DSA-65 firmware (PQClean commit `0586a824`, arduino-cli 1.5.1, esp32 core 3.3.11) |
| `esp32/PQCBAS_ESP32_ECDSA_baseline/` | ECDSA-P256 (mbedTLS as shipped in the core) sketch, two serial logs, parse script |
| `sumo/` | StudyArea network, demand and SUMO configuration |
| `scripts/`, `docs/` | Run wrappers; Raspberry Pi guide |
| `legacy_v1.2.0_liboqs0.15/` | Superseded v1.2.0 results (liboqs 0.15.0). **Not used for any reported value** |

## Environment of the reported data

Apple M2: liboqs 0.16.0, liboqs-python 0.16.0.1, Python 3.13.15. Raspberry Pi 5: Debian 12, kernel 6.6.51, `performance` governor, Python 3.11.2. ESP32: Arduino-ESP32 core 3.3.11 (SDK v5.5.5). Both liboqs builds are generic distribution builds; the Pi build uses OpenSSL and the M2 build does not; which ML-DSA code path ran at run time was not verified (`data/environment_records/`). Pi-to-M2 ratios therefore compare builds as well as hardware.

## Known limitations of this artifact

- One unit per device class.
- Raw OMNeT++/Veins `.sca/.vec` files and the 62 MB SUMO FCD file are not included (checksums are recorded); the per-run PHY/MAC analysis is.
- `scripts/` were updated from liboqs 0.15.0 to 0.16.0 to match the reported data and were not re-run end to end after that change; the reported values come from the archived raw outputs in `data/`.
- ECDSA-P256 on the ESP32 is the unmodified mbedTLS of the core, not an optimized library.

## Integrity

```bash
sha256sum -c SHA256SUMS.txt
```

## Versions

- v1.3.0 (1 Oct 2026): final κ = 384 data, Pi 5 repeat, build configurations, final PHY/MAC matrix, ESP32 ECDSA baseline.
- v1.2.0 (28 Sep 2026, DOI 10.5281/zenodo.21805963): earlier liboqs 0.15.0 results; superseded.

## License

MIT, see `LICENSE`.
