# PQ-CBAS-DSH — Artifact Package

Paket reprodusibilitas untuk naskah *"PQ-CBAS-DSH: A Certificate-Based Post-Quantum
Batched Aggregate Authentication Framework with Domain-Separated Hashing for VANETs"*.
Semua angka pada Tabel 5, 6, 11, dan 12 naskah dihasilkan oleh skrip dalam paket ini
dengan backend ML-DSA-65 asli (liboqs 0.15.0, reference C implementation).

## Struktur folder

```
artifact/
├── README.md                      <- file ini (struktur + perintah + ringkasan hasil)
├── run_bench.sh                   <- satu perintah: build liboqs + venv + benchmark
├── src/
│   └── bench_pqcbas.py            <- implementasi framework per Persamaan (1)-(27)
│                                     + benchmark + 6 eksperimen keamanan (cross-platform)
├── results/
│   ├── results_mac_m2.json        <- hasil resmi naskah: Apple M2, macOS 26.4.1,
│   │                                 Python 3.13.13, liboqs 0.15.0
│   └── results_xeon_sandbox.json  <- hasil pembanding: Intel Xeon 2.80 GHz vCPU,
│                                     Ubuntu 24.04, Python 3.12.3, liboqs 0.15.0
└── paper/
    ├── PQ-CBAS-DSH_final.tex      <- sumber LaTeX naskah (kompilasi: pdflatex 2x)
    ├── PQ-CBAS-DSH_final.pdf      <- naskah terkompilasi (20 halaman)
    └── image1.png ... image5.png  <- gambar yang dirujuk .tex
```

## Perintah

### Cara cepat (macOS / Linux)

```bash
bash run_bench.sh
```

Skrip ini otomatis: (1) meng-clone dan membangun liboqs ke `~/oqs` jika belum ada
(hanya algoritma ML-DSA, OpenSSL dimatikan), (2) membuat virtualenv dan memasang
`liboqs-python` + `numpy`, (3) menjalankan benchmark. Hasil tersimpan sebagai
`bench_results.json`. Durasi total: build ±2-5 menit (sekali saja) + benchmark ±1-3 menit.

### Cara manual

Prasyarat — macOS: `brew install cmake ninja python git` (compiler dari
`xcode-select --install`); Linux: `sudo apt install -y python3 python3-venv git cmake
ninja-build gcc`.

```bash
# 1) build liboqs (sekali)
git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git
cmake -S liboqs -B liboqs/build -GNinja \
  -DOQS_MINIMAL_BUILD="SIG_ml_dsa_44;SIG_ml_dsa_65;SIG_ml_dsa_87" \
  -DBUILD_SHARED_LIBS=ON -DOQS_USE_OPENSSL=OFF -DCMAKE_BUILD_TYPE=Release
ninja -C liboqs/build
cmake --install liboqs/build --prefix ~/oqs

# 2) dependensi python
python3 -m venv venv && source venv/bin/activate
pip install liboqs-python numpy

# 3) jalankan
OQS_INSTALL_PATH=~/oqs python3 src/bench_pqcbas.py
```

Catatan macOS: gunakan `OQS_INSTALL_PATH` (bukan `DYLD_LIBRARY_PATH`, yang dihapus
SIP). Verifikasi versi liboqs: `python3 -c "import oqs; print(oqs.oqs_version())"`.

### Kompilasi naskah

```bash
cd paper && pdflatex PQ-CBAS-DSH_final.tex && pdflatex PQ-CBAS-DSH_final.tex
```

(atau unggah folder `paper/` ke Overleaf).

## Ringkasan hasil (Apple M2 — angka resmi naskah)

Timing operasi (mean +/- std, 200 run) — Tabel 5 naskah:

| Operasi      | Waktu               |
|--------------|---------------------|
| Setup (CA)   | 0.054 +/- 0.002 ms  |
| VehKeyGen    | 0.054 +/- 0.002 ms  |
| CertGen      | 0.113 +/- 0.063 ms  |
| CertValidate | 0.054 +/- 0.002 ms  |
| Sign         | 0.117 +/- 0.061 ms  |

Agregasi (100 run; AggVerify 30 run) — Tabel 6 naskah:

| m  | Ukuran aggregate | Waktu Agg | Waktu AggVerify |
|----|------------------|-----------|-----------------|
| 1  | 5,232 B          | 0.05 ms   | 0.16 ms         |
| 2  | 5,280 B          | 0.07 ms   | 0.30 ms         |
| 5  | 5,424 B          | 0.16 ms   | 0.73 ms         |
| 10 | 5,664 B          | 0.32 ms   | 1.43 ms         |

Ukuran objek (byte-identik dengan FIPS 204 ML-DSA-65): pk 1,952 B; signature 3,309 B;
certificate 5,277 B; tuple T_i 10,662 B.

Eksperimen keamanan (10,000 trial per eksperimen) — Tabel 12 naskah: FRA 0; RSA 0;
AMA mutasi byte 0; AMA substitusi komponen 0; CCSA dengan DSH 0; CCSA tanpa DSH
10,000/10,000 (berhasil sesuai konstruksi, menunjukkan perlunya domain separation).

Replikasi lintas platform: run Xeon (sandbox) dan run Apple M2 menghasilkan ukuran
byte-identik dan hasil keamanan identik; timing M2 ±1.3-1.6x lebih cepat dengan
dispersi lebih ketat — lihat kedua file di `results/` untuk perbandingan penuh.

## Pemetaan hasil ke naskah

- `Setup/VehKeyGen/CertGen/CertValidate/Sign` -> Tabel 5
- `agg.{m}.agg_ms`, `agg.{m}.agg_size` -> Tabel 6; `aggverify_ms` -> narasi §7.3
- `sizes` -> Tabel 11 (baris prototipe) dan narasi §7.3
- `security` -> Tabel 12
- Tabel 7-8 dan Figure 3 = re-derivasi model Persamaan (50)-(52) dengan
  `CertValidate` terukur (0.054 ms) atas trace workflow prototipe; lihat §7.4-7.5.
