# ESP32 two-unit measurements (3 October 2026)

Raw serial logs, firmware, sketches, recorder scripts and analysis for Table `tab:esp32` and Figure `fig:esp32budget`.
These supersede the single-unit ESP32 data of earlier folders (`final_k384_20260929/esp32/`, `esp32_ecdsa_baseline/`), which are kept unmodified.

## What was measured
Two classic ESP32 development boards (Xtensa LX6 dual-core, 240 MHz, 4 MB flash; module marking and silicon revision not recorded),
unit A and unit B, identified by the MAC address read with `esptool flash_id` before and after each run (`logs/*.mac`, two addresses per file).
Three firmwares, each flashed to both units and run twice per unit (12 logs):

| Prefix | Firmware | Sketch | Binary |
|---|---|---|---|
| `final_` | ML-DSA-65 (PQClean 0586a824, kappa = 384, 48 B hashes) | `sketches/src_final.ino` | `firmware/fw_final.bin` |
| `ecdsa_` | ECDSA-P256, mbedTLS precompiled in the Arduino-ESP32 core | `sketches/src_ecdsa.ino` | `firmware/fw_ecdsa.bin` |
| `uecc_`  | ECDSA-P256, micro-ecc secp256r1 (`uECC_WORD_SIZE=4`, `-DNO_BLINK`), SHA-256 from the core | `sketches/src_uecc.ino` | `firmware/fw_uecc.bin` |

Protocol: 240 MHz, task priority 5, esp_timer in ms, `vTaskDelay` between iterations, 7,353 B transcript, serial 57,600 baud.
Samples per run: ML-DSA 500 core sign, 500 framework sign, 500 verify (key generation n = 20 and SHAKE256 n = 200 from the on-device summary);
ECDSA 20 key generations, 500 digest signs, 500 framework signs, 500 verifies, 200 hashes, plus a negative control (tampered digest rejected).

## Validity rule
A log is kept only if all sample counts are complete with consecutive indices, exactly one boot banner is present, there is no `_FAIL` line,
the MAC address is unchanged before and after the run and belongs to the stated unit, the end marker is present
(`ESP32_FINAL_BENCHMARK_OK`, `ESP32_ECDSA_BASELINE_OK`, `ESP32_UECC_BASELINE_OK`), and for the micro-ecc firmware `reset_reason=1` (power-on).
The ML-DSA and mbedTLS firmwares do not print the reset reason. Logs failing these checks (mostly lost serial lines at 57,600 baud, and three micro-ecc logs
from unit A with `reset_reason=0`; after re-flashing the same image the unit reported 1, so the cause was most likely an older image on that unit, not verified) were discarded and re-recorded; the criterion does not depend on the measured values.
The discarded logs are not part of this archive. `scripts/` holds the recorders (`rec.sh`/`recv.sh` for micro-ecc, `rec2.sh`/`recv2.sh` for the other two).

## Reproduce the statistics
```
python3 analysis/analyze_esp32.py logs analysis/stats_final     # needs numpy, scipy; writes stats_final.json/.txt
python3 analysis/make_fig_budget.py                              # run inside analysis/, writes the figure
```
The analysis re-checks every log (index continuity, MAC, boot count, failure lines) and reports the pooled mean of run means, between-run range,
pooled standard deviation, percentiles, Wilson intervals for budget exceedance, bootstrap intervals (20,000 resamples, seed 20261003) and unit comparisons.
`ESP32_ENVIRONMENT_AND_HASHES_AS_RECORDED_ON_MAC.txt` is the arduino-cli version, core list, date and SHA-256 of every file as recorded on the measurement computer.

## Headline results (mean of four run means, ms; between-run range in brackets)
| | ML-DSA-65 | micro-ecc | mbedTLS ECDSA |
|---|---|---|---|
| Verify | 27.668 [27.667, 27.668] | 108.758 [106.140, 110.559] | 310.126 [309.980, 310.418] |
| Framework sign | 93.218 [91.950, 94.907] | 97.467 [97.461, 97.472] | 157.561 [157.528, 157.607] |
| Share of signatures over 100 ms (n = 2,000) | 31.1% (Wilson 29.1-33.2) | 0% | 100% |

Limitations: two units of one chip type; the 500 samples of a run share one key and message; the ECC and ML-DSA code are portable C
(no assembly or hardware-assisted implementation examined); micro-ecc verification varies between runs although it is nearly constant within a run, cause not isolated.
