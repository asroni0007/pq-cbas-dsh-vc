# ESP32 ECDSA-P256 baseline (companion to PQCBAS_ESP32_Final)

STATUS: **sketch written but NOT yet compiled or run on hardware.** No ESP32 result from this folder may be quoted
until it has been compiled, flashed and its log archived.

Sketch: `PQCBAS_ESP32_ECDSA/PQCBAS_ESP32_ECDSA.ino` (mbedTLS from the Arduino-ESP32 core; same 240 MHz, task priority,
N = 20/500/500, esp_timer, vTaskDelay between iterations, and 7,353-byte transcript as the ML-DSA sketch).

Build / run (same toolchain as the final ML-DSA run: arduino-cli 1.5.1, esp32 core 3.3.11, board esp32:esp32:esp32doit-devkit-v1, as in FQBN.txt of the final run):

    cd <this folder>
    arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 PQCBAS_ESP32_ECDSA
    arduino-cli upload  --fqbn esp32:esp32:esp32doit-devkit-v1 -p /dev/cu.usbserial-0001 PQCBAS_ESP32_ECDSA
    # capture the serial output at 57600 baud into a log (stop after ESP32_ECDSA_BASELINE_OK)
    python3 - <<'PY'
    import serial,sys,time
    s=serial.Serial('/dev/cu.usbserial-0001',57600,timeout=1)
    out=open('ecdsa_baseline_serial.log','w')
    while True:
        l=s.readline().decode(errors='replace')
        if l: out.write(l); out.flush(); print(l,end='')
        if 'ESP32_ECDSA_BASELINE_OK' in l: break
    PY

Expected log lines: `KG,i,ms` / `S,i,ms` / `F,i,ms` / `V,i,ms` / `H,i,ms` per sample, `NEGATIVE_CONTROL ... REJECTED_OK`,
a `--- SUMMARY ---` block, and `ESP32_ECDSA_BASELINE_OK`.
After the run, archive: the .ino, the log, `arduino-cli version`, `arduino-cli core list`, and sha256 of all.

## Results (1 October 2026, two runs on the same ESP32-WROOM-32)

Device-computed summaries (full n; mean ms): 

| Operation | Run 1 | Run 2 |
|---|---|---|
| KeyGen (n=20) | 144.950 | 144.923 |
| Sign, 32 B digest (n=500) | 156.690 | 156.843 |
| Sign, framework path (SHA-256 over 7,353 B + sign) | 157.522 | 157.494 |
| Verify (n=500) | 309.541 | 310.298 |
| SHA-256 over 7,353 B (n=200) | 0.757 | 0.757 |

Framework signing exceeds 100 ms in 500/500 signatures in both runs. DER signature 71 B. Negative control (tampered digest) rejected (rc -19968) in both runs.

Serial capture at 57,600 baud lost some per-sample lines. Captured samples (parse_logs.py -> captured_sample_summary.json):
run 1: KG 0/20, S 480/500, F 498/500, V 498/500, H 200/200; run 2: KG 20/20, S 497/500, F 500/500, V 498/500, H 200/200.
Means of the captured samples agree with the device summaries within 0.01 ms. The manuscript uses the device summaries.

Caveat: mbedTLS as precompiled in Arduino-ESP32 core 3.3.11 (not an optimized ECC library); hash is SHA-256, not SHAKE256.
