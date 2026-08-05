# ARM Cloud — Menguji E1 Tanpa Biaya

Target: menguji apakah temuan **E1** (CertValidate ML-DSA-65 lebih cepat
daripada verify ECDSA-P256) bertahan di ARM non-Apple.

ESP32 tidak bisa menjawab ini — Xtensa bukan ARM. Yang dibutuhkan adalah
`aarch64` Linux, dan itu tersedia gratis.

---

## Pilihan penyedia

| Penyedia | CPU | Gratis? | Catatan |
|---|---|---|---|
| **Oracle Cloud** | Ampere A1 (Neoverse-N1) | **permanen**, 4 core / 24 GB | rekomendasi utama |
| AWS EC2 | Graviton2/3 (Neoverse) | 750 jam `t4g.small` (12 bln) | perlu kartu kredit |
| Hetzner | Ampere | ~€4/bln | murah, tanpa ribet kuota |
| GitHub Actions | Cortex-A / Neoverse | runner ARM gratis | timing berisik, hindari |

Semua Neoverse adalah **server-class** dengan NEON lebar seperti M2. Artinya
hasilnya membuktikan "lintas vendor ARM", belum "lintas kelas ARM". Untuk yang
kedua butuh Cortex-A72/A76 (Raspberry Pi). Tetap berharga: kalau E1 bertahan di
Ampere, klaim Anda tidak lagi khusus Apple.

---

## Oracle Cloud — langkah demi langkah

### 1. Buat instance

1. Daftar di `cloud.oracle.com` (perlu kartu untuk verifikasi, tidak ditagih
   untuk Always Free)
2. Compute → Instances → **Create Instance**
3. **Image and shape** → Change shape → **Ampere** → `VM.Standard.A1.Flex`
4. Set **4 OCPU, 24 GB** (batas Always Free)
5. Image: **Ubuntu 22.04** atau **24.04** (pastikan varian aarch64)
6. Simpan private key SSH yang ditawarkan
7. Create

Kalau muncul "Out of capacity", coba region atau availability domain lain —
kapasitas Ampere gratis sering penuh. Ini hambatan paling umum.

### 2. Masuk

```bash
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<public-ip>

uname -m                          # WAJIB aarch64
lscpu | grep -E "Model name|BogoMIPS|Flags" | head -3
```

Catat keluaran `lscpu` — ini masuk ke naskah sebagai identitas platform.

### 3. Dependensi

```bash
sudo apt update
sudo apt install -y cmake ninja-build git python3-venv python3-dev build-essential
```

### 4. Salin artifact

Dari MacBook:

```bash
ART="/Users/asroni/Documents/S3_DTETI_UGM/SH 2/P5/PQ-CBAS-DSH_artifact-3"

rsync -av -e "ssh -i ~/Downloads/ssh-key-*.key" \
  --exclude venv --exclude liboqs --exclude '*.pyc' --exclude results \
  "$ART/" ubuntu@<public-ip>:~/PQ-CBAS-DSH/

rsync -av -e "ssh -i ~/Downloads/ssh-key-*.key" \
  <eval-kit>/run_rpi.sh <eval-kit>/src/ci_stats.py \
  ubuntu@<public-ip>:~/PQ-CBAS-DSH/
```

`venv` dan `liboqs` dikecualikan — biner macOS/ARM64-Darwin tidak jalan di
Linux/aarch64 dan harus dibangun ulang.

### 5. Build liboqs

```bash
cd ~/PQ-CBAS-DSH

git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git
cmake -S liboqs -B liboqs/build -GNinja \
  -DOQS_MINIMAL_BUILD="SIG_ml_dsa_44;SIG_ml_dsa_65;SIG_ml_dsa_87" \
  -DBUILD_SHARED_LIBS=ON -DOQS_USE_OPENSSL=OFF -DCMAKE_BUILD_TYPE=Release
ninja -C liboqs/build
cmake --install liboqs/build --prefix ~/oqs
```

**Jangan** pakai `-DOQS_OPT_TARGET=native` untuk run resmi — biarkan profil
generik ARMv8 supaya sebanding dengan backend referensi pada Tabel V.

~5 menit di 4 core Ampere.

### 6. Python environment

```bash
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip
pip install liboqs-python numpy cryptography
```

**`cryptography` wajib** — dari situ baseline ECDSA-P256 diambil, dan tanpa itu
E1 tidak bisa diuji. Kalau gagal build dari source:

```bash
sudo apt install -y python3-cryptography libssl-dev pkg-config
```

### 7. Patch CI (kalau belum ikut tersalin)

```bash
grep -n "mean_ci95" src/e2e_workflow.py
```

Kosong berarti belum — jalankan patch dari RUNBOOK bagian 1.

### 8. Higienis pengukuran

```bash
# matikan layanan yang tidak perlu
sudo systemctl stop snapd unattended-upgrades 2>/dev/null

# pastikan tidak ada beban lain
uptime
```

Instance cloud berjalan di atas hypervisor bersama, jadi timing lebih berisik
daripada bare-metal. Jalankan tiap benchmark dua kali dan bandingkan; kalau
selisihnya di atas 10%, ulangi saat beban host lebih rendah.

### 9. Jalankan

```bash
cd ~/PQ-CBAS-DSH
source venv/bin/activate

# operasi + baseline ECDSA -> ini yang menguji E1
OQS_INSTALL_PATH=~/oqs python3 src/bench_pqcbas.py 2>&1 | tee bench_arm.log

# E2E 20 seed kedua mode
bash run_seeds.sh 20 90
```

### 10. Ambil hasil

```bash
# dari MacBook
rsync -av -e "ssh -i ~/Downloads/ssh-key-*.key" \
  ubuntu@<public-ip>:~/PQ-CBAS-DSH/{bench_arm.log,e2e_results_*.json,bench_results.json} \
  ./hasil_arm/
```

Kirimkan `bench_arm.log` — di situ ada blok `ml_dsa_65` dan `ecdsa_p256` yang
menentukan E1.

---

## Membaca hasilnya

Bandingkan pada mesin yang sama:

| | Apple M2 | Ampere ARM |
|---|---|---|
| CertValidate (ML-DSA-65 verify) | 0,054 ms | ? |
| ECDSA-P256 verify | 0,083 ms | ? |
| Rasio | **0,65×** (ML-DSA menang) | ? |

**E1 bertahan** → klaim naik dari "berlaku di Apple silicon" menjadi "berlaku
lintas vendor ARM". Inilah yang menembus ~8,3.

**E1 tidak bertahan** → temuan sah dan penting: inversi bergantung pada
mikroarsitektur tertentu. Jauh lebih baik Anda yang menemukan daripada
reviewer. Skor ~7,9 dengan klaim yang lebih jujur.

**Apa pun hasilnya, jangan ganti angka M2.** Laporkan sebagai tabel
multi-platform dengan kolom terpisah; mencampur platform dalam satu kolom
adalah cacat metodologis.

---

## Alternatif kalau Oracle penuh

**GitHub Codespaces** tidak menyediakan ARM. **AWS Graviton** `t4g.small` masuk
free tier 12 bulan dan biasanya selalu tersedia:

```bash
# setelah membuat instance Ubuntu arm64 di EC2
ssh -i key.pem ubuntu@<ip>
uname -m    # aarch64
# lanjutkan dari langkah 3
```

Atau **Hetzner CAX11** (~€4/bulan, Ampere, selalu tersedia) — kalau waktu lebih
berharga daripada biaya kecil ini, ini pilihan paling mulus.

---

## Setelah ini

Dengan M2 + ESP32 + ARM cloud, evaluasi Anda mencakup:

| Kelas | Platform | Arsitektur |
|---|---|---|
| Desktop | Apple M2 | ARM (Apple) |
| Server | Ampere/Graviton | ARM (Neoverse) |
| Mikrokontroler | ESP32 | Xtensa |

Tiga kelas perangkat, dua arsitektur, rentang lebih dari 500×. Itu cakupan
evaluasi yang jarang ditemukan pada paper VANET post-quantum, dan menutup
kritik "single platform" sepenuhnya.
