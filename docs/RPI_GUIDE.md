# Panduan Compile & Uji — Raspberry Pi

Target: menguji apakah temuan **E1** (CertValidate ML-DSA-65 lebih cepat
daripada verify ECDSA-P256) bertahan di ARM tanpa SIMD selebar Apple M2.

---

## 0. Perangkat

| | RPi 4B | RPi 5 | catatan |
|---|---|---|---|
| Core | Cortex-A72 | Cortex-A76 | keduanya ARMv8-A + NEON |
| Clock | 1,5 GHz | 2,4 GHz | |
| RAM | ≥2 GB | ≥4 GB | 4 GB disarankan untuk build |
| OS | Raspberry Pi OS **64-bit** | idem | 32-bit akan gagal/lambat |

RPi 5 lebih dekat ke kelas RSU. RPi 4 sudah cukup.

Cek arsitektur — harus `aarch64`:

```bash
uname -m
```

Kalau keluar `armv7l`, itu OS 32-bit. Pasang ulang dengan Raspberry Pi OS 64-bit.

---

## 1. Dependensi

```bash
sudo apt update
sudo apt install -y cmake ninja-build git python3-venv python3-dev build-essential

# untuk vcgencmd (monitor termal)
sudo apt install -y libraspberrypi-bin
```

---

## 2. Salin artifact ke RPi

Dari MacBook:

```bash
ART="/Users/asroni/Documents/S3_DTETI_UGM/SH 2/P5/PQ-CBAS-DSH_artifact-3"

rsync -av --exclude venv --exclude liboqs --exclude '*.pyc' \
  "$ART/" pi@raspberrypi.local:~/PQ-CBAS-DSH/

# kit tambahan
rsync -av run_rpi.sh          pi@raspberrypi.local:~/PQ-CBAS-DSH/
rsync -av src/ci_stats.py     pi@raspberrypi.local:~/PQ-CBAS-DSH/src/
```

Ganti `raspberrypi.local` dengan IP RPi kalau mDNS tidak jalan (`hostname -I` di RPi).

**Penting:** `venv` dan `liboqs` sengaja dikecualikan — biner macOS tidak jalan
di ARM Linux dan harus dibangun ulang.

---

## 3. Compile liboqs

```bash
cd ~/PQ-CBAS-DSH

git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git
cmake -S liboqs -B liboqs/build -GNinja \
  -DOQS_MINIMAL_BUILD="SIG_ml_dsa_44;SIG_ml_dsa_65;SIG_ml_dsa_87" \
  -DBUILD_SHARED_LIBS=ON \
  -DOQS_USE_OPENSSL=OFF \
  -DCMAKE_BUILD_TYPE=Release
ninja -C liboqs/build
cmake --install liboqs/build --prefix ~/oqs
```

Durasi: ~10–20 menit di RPi 4, ~6–10 menit di RPi 5.

**Jangan** tambahkan `-DOQS_OPT_TARGET=native` untuk run resmi — biarkan liboqs
memakai profil generik ARMv8, supaya perbandingan dengan M2 sama-sama memakai
implementasi C referensi. Kalau ingin data tambahan, jalankan varian `native`
sebagai baris terpisah, jangan menggantikan.

Verifikasi:

```bash
ls ~/oqs/lib/liboqs.so*
```

---

## 4. Python environment

```bash
cd ~/PQ-CBAS-DSH
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install liboqs-python numpy
```

Kalau `numpy` gagal build dari source (biasa di RPi):

```bash
sudo apt install -y python3-numpy
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install liboqs-python
```

Uji impor:

```bash
OQS_INSTALL_PATH=~/oqs python3 -c "import oqs, numpy; print('oqs + numpy OK')"
```

---

## 5. Patch CI (kalau belum ikut tersalin)

```bash
grep -n "mean_ci95" src/e2e_workflow.py
```

Kalau kosong, jalankan patch dari RUNBOOK bagian 1.

---

## 6. Higienis pengukuran — jangan dilewati

```bash
# kunci clock
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# harus 0x0
vcgencmd get_throttled

# idealnya < 60 C sebelum mulai
vcgencmd measure_temp
```

Arti `get_throttled`: bit 0 = under-voltage sekarang, bit 1 = capping frekuensi,
bit 2 = throttling. Selain `0x0` berarti hasil tidak layak dilaporkan — pasang
heatsink/fan dan pakai PSU resmi.

Kurangi noise:

```bash
sudo systemctl stop bluetooth
sudo systemctl isolate multi-user.target    # matikan desktop GUI
```

---

## 7. Jalankan

```bash
cd ~/PQ-CBAS-DSH
source venv/bin/activate
bash run_rpi.sh 20 90
```

Skrip merekam identitas platform, benchmark operasi + baseline ECDSA, E2E 20
seed kedua mode, lalu meringkas E1. Semua masuk ke `results_rpi_<timestamp>/`.

Ambil hasilnya:

```bash
# dari MacBook
rsync -av pi@raspberrypi.local:~/PQ-CBAS-DSH/results_rpi_*/ ./hasil_rpi/
```

---

## 8. Perkiraan hasil

Ekstrapolasi kasar dari siklus pqm4 Dilithium3 (Cortex-M4, implementasi C
referensi) — ini **batas atas pesimistis**, karena A72/A76 superscalar
out-of-order dengan NEON jadi realitanya akan jauh lebih cepat:

| Platform | verify | sign |
|---|---|---|
| Apple M2 (terukur) | 0,05 ms | 0,12 ms |
| RPi 5 (perkiraan) | 0,3–1,0 ms | 1,0–3,3 ms |
| RPi 4 (perkiraan) | 0,5–1,6 ms | 1,6–5,3 ms |

Kalau `verify` RPi keluar di kisaran 0,3–1,5 ms, itu wajar. Yang menentukan
bukan angka absolutnya, melainkan **rasio terhadap ECDSA-P256 di mesin yang
sama**.

Dampak ke klaim deadline — dengan `verify` 1 ms dan batch t=25, biaya batch
menjadi ~25 ms, sehingga `W + T_proc` ≈ 115 ms dan **melampaui deadline 100 ms**.
Kalau ini terjadi, itu temuan penting: `W` harus diturunkan pada hardware kelas
RSU. Laporkan apa adanya — justru memperkuat E4.

---

## Troubleshooting

**`ImportError: libhoqs.so not found`**
```bash
export LD_LIBRARY_PATH=~/oqs/lib:$LD_LIBRARY_PATH
```

**`ninja: command not found`** → `sudo apt install ninja-build`

**Build OOM di RPi 4 2 GB** → tambah swap:
```bash
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup && sudo dphys-swapfile swapon
```

**Hasil berayun > 10%** → cek `vcgencmd get_throttled` lagi; kemungkinan termal.
Beri jeda antar-run dan pastikan pendinginan aktif.

**`vcgencmd: command not found`** → `sudo apt install libraspberrypi-bin`
(atau abaikan; skrip tetap jalan, hanya tanpa monitor termal).
