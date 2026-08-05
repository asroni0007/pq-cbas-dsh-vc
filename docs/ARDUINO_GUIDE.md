# ESP32 via Arduino IDE — Panduan Menjalankan

Anda sudah berhasil flash Blink ke DOIT ESP32 DEVKIT V1 di
`/dev/cu.usbserial-0001`, jadi driver dan toolchain sudah beres.
Panduan ini memakai jalur Arduino IDE yang sama — **tidak perlu ESP-IDF**.

---

## 1. Ambil sumber PQClean

Buka Terminal:

```bash
cd <folder-eval-kit>/arduino/PQCBAS_ESP32_Bench
bash setup_arduino.sh
```

Skrip ini meng-clone PQClean dan menyalin Dilithium3 (= ML-DSA-65) +
`fips202.c` (SHAKE256) ke `src/`, lalu membuat shim RNG ESP32.

Arduino IDE otomatis mengompilasi semua `.c` di dalam `src/` — tidak perlu
membuat library.

Verifikasi:

```bash
ls src/ | head
```

Harus muncul `sign.c`, `poly.c`, `polyvec.c`, `packing.c`, `ntt.c`,
`fips202.c`, `api.h`, dan lain-lain.

---

## 2. Pindahkan ke folder sketchbook

Arduino IDE mensyaratkan nama folder = nama file `.ino`. Struktur ini sudah
benar, tinggal salin:

```bash
cp -r "$(pwd)" ~/Documents/Arduino/
```

---

## 3. Setelan Arduino IDE

Buka `~/Documents/Arduino/PQCBAS_ESP32_Bench/PQCBAS_ESP32_Bench.ino`, lalu:

| Menu | Nilai |
|---|---|
| Tools → Board | **DOIT ESP32 DEVKIT V1** |
| Tools → **Partition Scheme** | **Huge APP (3MB No OTA/1MB SPIFFS)** |
| Tools → CPU Frequency | **240MHz (WiFi/BT)** |
| Tools → Flash Size | 4MB (32Mb) |
| Tools → Core Debug Level | None |
| Tools → Port | `/dev/cu.usbserial-0001` |

**Partition Scheme wajib diubah.** Default "Default 4MB with spiffs" hanya
memberi 1,2 MB untuk aplikasi; Dilithium + FreeRTOS bisa melampauinya.

---

## 4. Compile & upload

1. Klik **Verify** (✓) dulu — kompilasi pertama ~2–4 menit.
2. Kalau bersih, klik **Upload** (→).
3. Buka **Serial Monitor** (Tools → Serial Monitor), set baud **115200**.
4. Tekan tombol **EN/RST** di papan kalau keluaran tidak muncul.

Benchmark berjalan ~2–3 menit.

---

## 5. Keluaran

```
[PLATFORM] ESP32 | 240 MHz | 2 core | SDK v4.4.x
[PLATFORM] flash 4194304 B | heap awal 29xxxx B

========================================================
 PQ-CBAS-DSH benchmark - ESP32 (kelas OBU)
========================================================
  pk=1952 B  sk=4032 B  sig=3309 B  msg=100 B

[1/5] keypair (n=20)...
[2/5] domain-separated hashing (n=200)...
[3/5] sign (n=50)...
[4/5] verify (n=50)...
[5/5] batch verify m=1,2,5,10...

--- A. Operasi inti ---
  keypair      n= 20  mean=    9.xxx ms  ...
  sign         n= 50  mean=   3x.xxx ms  ...
  verify       n= 50  mean=   1x.xxx ms  ...
  2x DSH       n=200  mean=    x.xxx ms  ...

--- B. Kelayakan OBU (sign vs anggaran BSM) ---
  10 msg/s : anggaran  100.0 ms | sign   3x.xx ms = 3x.x% | LAYAK

--- C. Verifikasi batch sisi-RSU (terukur) ---
--- D. Proyeksi ke beban skenario naskah ---
--- E. Memori ---
--- F. JSON (salin baris di bawah) ---
{"platform":"esp32", ... }
```

**Salin baris JSON di bagian F** dan kirimkan — itu yang saya butuhkan untuk
menyusun tabel naskah.

Perkiraan awal (ekstrapolasi siklus pqm4 @240 MHz, **bukan** pengukuran):
keypair ~9 ms, sign ~33 ms, verify ~10 ms. Bisa meleset 2× ke dua arah;
yang masuk naskah adalah hasil ukur.

---

## 6. Kenapa bagian C dan D penting

Bagian C **mengukur** verifikasi batch, bukan mengekstrapolasi. Ini mengubah
pernyataan "ESP32 tidak layak sebagai RSU" dari dugaan menjadi hasil
pengukuran.

Bersama data Apple M2 pada Tabel V, Anda memperoleh **penjepit rentang ~200×
kelas perangkat**:

| Platform | verify | kelas |
|---|---|---|
| Apple M2 | 0,054 ms | desktop |
| ESP32 | ~10 ms | mikrokontroler |

Itu argumen yang jauh lebih kuat daripada sekadar menambah satu titik data —
ia memetakan di mana batas kelayakan RSU berada.

---

## Troubleshooting

**`fatal error: src/api.h: No such file`**
`setup_arduino.sh` belum dijalankan, atau dijalankan di folder lain. Pastikan
`src/api.h` ada di sebelah file `.ino`.

**`Sketch too big`**
Partition Scheme belum diubah ke **Huge APP**. Lihat langkah 3.

**`Guru Meditation Error: Core 0 panic'ed (Stack canary watchpoint triggered)`**
Naikkan `BENCH_STACK` di `.ino` dari `110 * 1024` ke `128 * 1024`.

**`E (xxx) task_wdt: Task watchdog got triggered`**
Sudah ada `vTaskDelay(1)` di setiap loop. Kalau masih muncul, naikkan delay
menjadi `vTaskDelay(2)`.

**Serial Monitor kosong**
Baud harus 115200. Tekan tombol EN/RST. Kalau tetap kosong, coba
Tools → USB CDC On Boot → Disabled.

**`undefined reference to PQCLEAN_DILITHIUM3_CLEAN_...`**
PQClean memakai prefiks `MLDSA65`. Skrip setup menambahkan alias otomatis; cek
bagian akhir `src/api.h` apakah aliasnya ada.

**Heap tidak cukup / crash saat batch**
Turunkan `MAX_BATCH` dari 10 ke 5 di `.ino` (bagian C tetap bermakna dengan
m = 1, 2, 5).

---

## Peringatan akurasi

Kode ini saya tulis dan validasi logikanya (statistik, pelaporan, kurung
seimbang, jejak memori 166 KB dari ~320 KB DRAM), tetapi **tidak dapat saya
kompilasi-uji** — tidak ada toolchain ESP32 maupun perangkatnya di sini.
Kemungkinan besar perlu satu-dua penyesuaian kecil saat Verify pertama,
terutama pada nama simbol PQClean. Sediakan waktu untuk iterasi.
