# Validasi SUMO untuk PQ-CBAS-DSH
## StudyArea Network — R=150 m — Apple M2 MacBook Air

Dokumen ini menjelaskan cara menjalankan validasi SUMO lengkap yang
menggantikan model uniform-arrival dengan trace mobilitas nyata.

---

## Struktur file

```
PQ-CBAS-DSH_artifact/
├── src/
│   ├── bench_pqcbas.py          # benchmark operasi + ECDSA baseline
│   ├── e2e_workflow.py          # harness E2E (uniform arrival, multi-seed)
│   └── sumo_pqcbas_bridge.py   # ← BARU: bridge SUMO FCD → PQ-CBAS-DSH
├── sumo/
│   ├── StudyAreNetwork.net.xml  # peta jaringan 666m×138m
│   ├── Demand.rou.xml           # demand 6590 veh/jam campuran
│   ├── PublicTransport.xml      # halte bus
│   ├── bpu_studyarea.add.xml    # RSU POI + coverage polygon R=150m
│   ├── studyarea_test.sumocfg   # konfigurasi simulasi
│   ├── run_bpu_sumo.py          # runner BPU asli
│   └── cross_validate_studyarea.py  # cross-validasi asli
└── results/
    ├── results_mac_m2.json      # benchmark timing
    ├── e2e_results_W90_full_mac_m2.json
    ├── e2e_results_W90_digest_mac_m2.json
    └── sumo_pqcbas_W90_*.json  # (dihasilkan oleh bridge)
```

---

## Prasyarat

### 1) SUMO (wajib untuk mode SUMO penuh)
```bash
conda create -n sumo-env python=3.11
conda activate sumo-env
conda install -c conda-forge sumo
export SUMO_HOME=$CONDA_PREFIX
```
Atau via Homebrew:
```bash
brew install sumo
```
Verifikasi: `sumo --version`

### 2) Python dependencies (di venv PQ-CBAS-DSH yang sudah ada)
```bash
cd "/Users/asroni/Documents/S3_DTETI_UGM/SH 1/P5/Sc_P5"
source venv/bin/activate
pip install numpy  # sudah ada
```

---

## Cara menjalankan

### Mode A — SUMO menghasilkan FCD, lalu bridge memrosesnya (DIREKOMENDASIKAN)

```bash
cd sumo/

# 1) Jalankan SUMO headless untuk menghasilkan FCD
sumo -c studyarea_test.sumocfg

# 2) Jalankan bridge (full-cert mode, 3 seed)
OQS_INSTALL_PATH=~/oqs python3 ../src/sumo_pqcbas_bridge.py \
    --no-sumo --fcd studyarea_fcd.xml \
    --rsu-x 80 --rsu-y 36 --R 150 \
    --window 90 --seeds 3

# 3) Digest mode
OQS_INSTALL_PATH=~/oqs python3 ../src/sumo_pqcbas_bridge.py \
    --no-sumo --fcd studyarea_fcd.xml \
    --rsu-x 80 --rsu-y 36 --R 150 \
    --window 90 --seeds 3 --digest
```

### Mode B — Bridge langsung menjalankan SUMO (satu perintah)

```bash
cd sumo/
OQS_INSTALL_PATH=~/oqs python3 ../src/sumo_pqcbas_bridge.py \
    --cfg studyarea_test.sumocfg \
    --rsu-x 80 --rsu-y 36 --R 150 \
    --window 90 --seeds 3
```

### Mode C — Tanpa SUMO (pakai FCD yang sudah ada)

```bash
# Jika sudah punya studyarea_fcd.xml dari run sebelumnya:
OQS_INSTALL_PATH=~/oqs python3 src/sumo_pqcbas_bridge.py \
    --no-sumo --fcd sumo/studyarea_fcd.xml \
    --rsu-x 80 --rsu-y 36 --R 150 \
    --window 90 --seeds 5 --digest
```

---

## Output yang dihasilkan

```
sumo_pqcbas_W90_full.json    # full-cert mode
sumo_pqcbas_W90_digest.json  # digest mode
```

Setiap file berisi:
- `vehicles_in_rsu`: jumlah kendaraan yang masuk coverage RSU
- `contact_mean_s`: rata-rata waktu kontak kendaraan dengan RSU (detik)
- `e2e_mean_ms` + `e2e_mean_ci95`: latensi E2E rata-rata ± CI₉₅
- `proc_mean_ms`: waktu pemrosesan batch rata-rata per window
- `deadline_misses` + `miss_rate_pct`: jumlah dan persentase pesan melewati 100 ms
- `per_seed`: breakdown per seed untuk verifikasi stabilitas

---

## Pemetaan hasil ke naskah

| Field output bridge | Kolom Tabel VII naskah |
|---|---|
| `vehicles_in_rsu` | Vehicles dalam RSU |
| `e2e_mean_ms ± ci95` | E2E mean ± CI₉₅ |
| `proc_mean_ms` | Proc. (ms) |
| `deadline_misses` / `messages_total` | Deadline misses |

Hasil bridge menggantikan narasi "uniform-arrival model" di §VII-D dengan
"SUMO mobility trace (StudyArea, R=150 m)".

---

## Spesifikasi jaringan (untuk §VII-A naskah)

| Parameter | Nilai |
|---|---|
| Panjang koridor | 666 m |
| Lebar | 138 m |
| Edges total | 48 (non-internal) |
| Junctions | 53 |
| Lanes | 275 |
| RSU posisi | (80, 36) |
| RSU radius | 150 m |
| Edges dalam coverage | 17 dari 48 |
| Coverage % bounding box | 77% |
| Demand | ~6.590 kendaraan/jam (bus, motor, taxi, truk) |
| Kendaraan konkuren dalam RSU (Little's Law) | ~25 |
| Durasi simulasi | 3.600 s (1 jam) |
