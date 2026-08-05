# RUNBOOK — tiga langkah perbaikan evaluasi PQ-CBAS-DSH

Urutan ini disengaja. Langkah 1 dan 2 tidak butuh run ulang atau hardware baru,
dan **hasilnya bisa mengubah parameter skenario** — jadi kerjakan sebelum
menghabiskan waktu pada langkah 3.

```
kit/
├── RUNBOOK.md              <- file ini
├── run_seeds.sh            <- langkah 2: sweep 20 seed
└── src/
    ├── ci_stats.py         <- langkah 1: perbaikan CI (Student-t)
    └── transport_budget.py <- langkah 1b: anggaran transport + beban kanal
```

Salin `src/*.py` ke folder `src/` artifact Anda, dan `run_seeds.sh` ke akar
artifact (sejajar dengan `run_bench.sh`).

---

## Langkah 1 — perbaiki bug CI (15 menit, tanpa run ulang)

### Bugnya

`src/e2e_workflow.py`, di dalam `aggregate_seeds()`:

```python
"e2e_mean_ci95": round(1.96*statistics.stdev(e2e)/len(e2e)**0.5,2) if len(rows)>1 else None,
```

`1.96` adalah kuantil **normal**. Untuk n=5 dengan sigma diestimasi dari sampel,
yang benar adalah Student-t pada df=4, yaitu **2.776**. CI yang dilaporkan
karena itu terlalu sempit: **1.416×** untuk n=5, **2.195×** untuk n=3.

### Perbaikan kode

Tambahkan di bagian import:

```python
from ci_stats import mean_ci95
```

Ganti baris di atas menjadi:

```python
"e2e_mean_ci95": round(mean_ci95(e2e)[1], 2) if len(rows) > 1 else None,
```

Verifikasi:

```bash
python3 src/ci_stats.py
```

### Koreksi tabel tanpa run ulang

Karena kedua rumus punya faktor `s/sqrt(n)` yang sama, CI lama bisa langsung
diskalakan. Nilai pengganti untuk Tabel VIII–X:

| Tabel | Skenario | dilaporkan | **benar** | batas atas |
|---|---|---|---|---|
| VIII | highway-n20 | 47.1 ± 0.50 | **47.1 ± 0.71** | 47.8 |
| VIII | highway-n20-attack | 47.1 ± 0.68 | **47.1 ± 0.96** | 48.1 |
| VIII | urban-n30 | 47.1 ± 0.35 | **47.1 ± 0.50** | 47.6 |
| VIII | intersection-n15 | 48.1 ± 0.51 | **48.1 ± 0.72** | 48.8 |
| IX | highway-n20 | 46.4 ± 0.53 | **46.4 ± 0.75** | 47.2 |
| IX | highway-n20-attack | 46.4 ± 0.65 | **46.4 ± 0.92** | 47.3 |
| IX | urban-n30 | 46.2 ± 0.32 | **46.2 ± 0.45** | 46.7 |
| IX | intersection-n15 | 47.1 ± 0.51 | **47.1 ± 0.72** | 47.8 |
| X | full-certificate (n=3) | 46.3 ± 0.36 | **46.3 ± 0.79** | 47.1 |
| X | certificate-digest (n=3) | 46.3 ± 0.43 | **46.3 ± 0.94** | 47.2 |

**Kabar baik:** semua batas atas tetap jauh di bawah 100 ms — klaim
*zero deadline misses* tidak goyah.

**Yang harus dihapus:** klaim di Bagian VII-E,

> "The CI95 is 4× tighter than the uniform-arrival result (0.4 vs 1.5 ms)
> because the SUMO arrival distribution is more regular."

Setelah koreksi, SUMO ±0.79–0.94 vs uniform ±0.50–0.96 — **tidak lebih ketat**.
Klaim itu artefak dari memakai z pada n=3. Hapus, atau ganti menjadi pernyataan
bahwa kedua distribusi kedatangan memberi dispersi antar-seed yang sebanding.

---

## Langkah 1b — anggaran transport & kelayakan kanal (30 menit, murni analitik)

```bash
python3 src/transport_budget.py           # tabel
python3 src/transport_budget.py --latex   # + LaTeX siap tempel
```

### Dua temuan yang akan muncul

**(a) Full-cert mode gagal deadline pada DSRC 6 Mbit/s.**

```
full-cert  DSRC 6 Mbit/s   T_tx 14.22 ms  total 106.62 ms   MISS
digest     DSRC 6 Mbit/s   T_tx  4.62 ms  total  97.02 ms   OK (margin 2.98 ms)
```

Margin menyusut dari 7.6 ms (klaim sekarang) ke 2.98 ms. Ini **memperkuat**
temuan E4 Anda: pemilihan `W` benar-benar jadi parameter dominan.

**(b) Digest mode melebihi batas bawah DSRC.**

```
digest: 25 kend × 10 msg/s = 6.93 Mbit/s   >  6 Mbit/s
```

Naskah memakai digest sebagai solusi kelayakan kanal (§V-E), tapi pada beban
skenario Anda sendiri ia masih lewat. **Anda harus memilih:** naikkan asumsi MCS
ke ≥12 Mbit/s, atau turunkan message rate ke ≤8.7 msg/s. Keputusan ini
mempengaruhi parameter skenario — karena itu kerjakan **sebelum** langkah 2.

---

## Langkah 2 — sweep 20 seed (beberapa jam, MacBook Anda)

```bash
bash run_bench.sh          # sekali saja, kalau liboqs belum dibangun
bash run_seeds.sh 20 90    # 20 seed, W = 90 ms, kedua mode
```

Kenapa 20, bukan 50:

| n | t(df=n−1) | lebar CI relatif thd n=50 |
|---|---|---|
| 5 | 2.776 | 1.38× |
| **20** | **2.093** | **1.04×** |
| 50 | 2.010 | 1.00× |
| 100 | 1.984 | 0.99× |

n=20 menangkap ~96% manfaatnya. Dari 20 ke 50 nyaris tak ada bedanya —
tidak sepadan dengan waktu runnya.

**Jalankan di MacBook M2 yang sama** dengan run sebelumnya. Jangan campur
platform dalam satu tabel.

---

## Langkah 3 — run kelas RSU/OBU (akhir pekan, Raspberry Pi)

### Perangkat

Raspberry Pi 4 atau 5, 64-bit Raspberry Pi OS. RPi 5 (Cortex-A76) lebih dekat
ke kelas RSU; RPi 4 (Cortex-A72) sudah cukup. Keduanya punya NEON tapi jauh
lebih sempit dari M2 — itulah titik ujinya.

**Jangan** kejar Cortex-M4/pqm4 untuk paper ini: butuh reimplementasi total,
berbulan-bulan, dan tidak sebanding dengan nilai tambahnya. Cukup catat sebagai
future work.

### Setup

```bash
sudo apt update
sudo apt install -y cmake ninja-build git python3-venv python3-dev

git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git
cmake -S liboqs -B liboqs/build -GNinja \
  -DOQS_MINIMAL_BUILD="SIG_ml_dsa_44;SIG_ml_dsa_65;SIG_ml_dsa_87" \
  -DBUILD_SHARED_LIBS=ON -DOQS_USE_OPENSSL=OFF -DCMAKE_BUILD_TYPE=Release
ninja -C liboqs/build
cmake --install liboqs/build --prefix ~/oqs

python3 -m venv venv && source venv/bin/activate
pip install liboqs-python numpy
```

### Higienis pengukuran (penting di RPi)

```bash
# kunci ke governor performance — tanpa ini hasil berayun besar
sudo cpufreq-set -g performance   2>/dev/null || \
  echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# pantau throttling termal; kalau != 0x0 pasang heatsink/fan dan ulangi
vcgencmd get_throttled
```

### Jalankan

```bash
OQS_INSTALL_PATH=~/oqs python3 src/bench_pqcbas.py      # timing operasi + E1
bash run_seeds.sh 20 90                                  # E2E
```

### Yang dicari: apakah E1 bertahan?

Bandingkan `CertValidate` (ML-DSA-65 verify) dengan `ECDSA-P256 verify` pada
mesin yang sama. Di M2: 0.054 vs 0.083 ms — ML-DSA menang.

- **Kalau inversi tetap muncul** → klaim naik dari "berlaku di MacBook saya"
  jadi "berlaku lintas kelas ARM". Jauh lebih kuat.
- **Kalau tidak muncul** → itu sendiri temuan yang layak dilaporkan, dan jauh
  lebih baik Anda yang menemukan daripada reviewer.

Apa pun hasilnya, laporkan sebagai tabel dua-platform. Jangan ganti angka M2 —
tambahkan kolom.

---

## Estimasi dampak

| Setelah | Skor perkiraan |
|---|---|
| sekarang | 7.2 |
| + langkah 1 (CI) | ~7.4 |
| + langkah 1b (transport) | ~7.6 |
| + langkah 2 (20 seed) | ~7.7 |
| + langkah 3, E1 **replikasi** | **~8.3** |
| + langkah 3, E1 **tidak** replikasi | ~7.9 |

Langkah 1 dan 1b memberi kenaikan terbesar per jam kerja, dan keduanya tidak
butuh hardware apa pun.

---

## Catatan

Saya tidak bisa menjalankan langkah 2 dan 3 untuk Anda: container saya
x86_64 Xeon **1 vCPU** — arsitektur berbeda dari M2, dan vCPU bersama membuat
timing terlalu berisik untuk benchmark. Mencampurkan hasilnya ke Tabel VIII/IX
akan jadi cacat metodologis. Langkah 1 dan 1b sepenuhnya analitik, jadi hasil
di atas sudah final dan bisa langsung dipakai.

---

# STATUS PER 1 AGUSTUS 2026

| Langkah | Status | Hasil |
|---|---|---|
| 1. Bug CI (Student-t) | selesai | dipatch di `e2e_workflow.py` + `sumo_pqcbas_bridge.py` |
| 1b. Anggaran transport | selesai | subbagian + Tabel baru masuk naskah |
| 2. Sweep 20 seed uniform | selesai | 285.560 pesan, 0 miss |
| 2b. Sweep 20 seed SUMO | selesai | 63.860 pesan, 0 miss, CI ±0,10-0,11 |
| **3. Run Raspberry Pi** | **belum** | `bash run_rpi.sh` |

Total sekarang: **349.420 pesan, 20 seed, nol deadline miss.**

---

# Langkah 3 — Raspberry Pi (satu-satunya yang tersisa)

## Persiapan perangkat

RPi 4 (Cortex-A72) atau 5 (Cortex-A76), 64-bit Raspberry Pi OS. RPi 5 lebih
dekat ke kelas RSU. **Jangan** kejar Cortex-M4/pqm4 — butuh reimplementasi
total, berbulan-bulan, tak sebanding nilainya. Catat sebagai future work.

```bash
sudo apt update
sudo apt install -y cmake ninja-build git python3-venv python3-dev

# salin folder artifact ke RPi (scp / rsync / USB), lalu:
cd PQ-CBAS-DSH_artifact-3
bash run_bench.sh          # build liboqs + venv, ~10-20 menit di RPi
```

Salin juga `run_rpi.sh` ke akar artifact, dan `src/ci_stats.py` ke `src/`.
Pastikan patch CI sudah ada di `e2e_workflow.py` (RUNBOOK bagian 1).

## Higienis pengukuran — jangan dilewati

```bash
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
vcgencmd get_throttled    # harus 0x0; kalau tidak, pasang heatsink/fan
vcgencmd measure_temp     # idealnya < 60 C sebelum mulai
```

Tanpa ini hasil berayun besar dan tidak layak dilaporkan. `run_rpi.sh` akan
memperingatkan otomatis kalau kondisi belum terpenuhi.

## Jalankan

```bash
bash run_rpi.sh 20 90
```

Skrip akan: (1) merekam identitas platform lengkap ke `platform.txt` — ini
**wajib** untuk naskah, (2) benchmark operasi + baseline ECDSA, (3) E2E 20 seed
kedua mode, (4) meringkas apakah E1 bertahan.

Semua keluaran masuk ke `results_rpi_<timestamp>/`.

## Membaca hasilnya

Yang diuji: apakah `CertValidate` (ML-DSA-65) tetap lebih cepat dari
`ECDSA-P256 verify`? Di M2: 0,054 vs 0,083 ms.

- **Bertahan** → klaim E1 naik dari "berlaku di MacBook saya" menjadi "berlaku
  lintas kelas ARM". Jauh lebih kuat.
- **Tidak bertahan** → juga temuan sah: inversi bergantung pada lebar SIMD.
  Lebih baik Anda yang menemukan daripada reviewer.

**Apa pun hasilnya, jangan ganti angka M2.** Laporkan sebagai tabel dua-platform
dengan kolom terpisah. Mencampur platform dalam satu kolom adalah cacat
metodologis.

Kirimkan isi `results_rpi_<timestamp>/` dan saya susun tabel dua-platform serta
revisi klaim E1-nya.
