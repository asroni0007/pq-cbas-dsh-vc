# ESP32 — bisa atau tidak?

**Jawaban singkat: bisa, tapi bukan untuk keperluan Anda sekarang.**

ESP32 dapat menjalankan ML-DSA-65 sebagai **OBU** (penandatangan), tetapi
tidak dapat menjalankan harness evaluasi Anda, tidak dapat berperan sebagai
RSU, dan **tidak menguji klaim E1 sama sekali**. Untuk menembus skor ~8,3,
Raspberry Pi tetap jalur yang benar.

---

## Kenapa ESP32 tidak menjawab pertanyaan Anda

### 1. Bukan ARM — jadi tidak menguji E1

Klaim E1 Anda adalah: *aritmetika NTT mengungguli perkalian skalar
kurva-eliptik pada pipeline SIMD ARM*. ESP32 memakai **Xtensa LX6**
(ESP32-C3/C6 memakai **RISC-V**). Keduanya bukan ARM dan tidak punya NEON.

Hasil ESP32 tidak bisa mendukung maupun membantah E1 — ia menjawab pertanyaan
yang berbeda.

### 2. Harness Anda tidak bisa jalan di sana

`e2e_workflow.py` dan `sumo_pqcbas_bridge.py` adalah Python 3 + numpy +
liboqs-python. ESP32 hanya punya MicroPython (tanpa numpy, tanpa liboqs
binding). Seluruh alur CA–OBU–RSU–CS, jendela koleksi, dan akuntansi
deadline harus ditulis ulang dari nol dalam C.

### 3. Terlalu lambat untuk peran RSU

Ekstrapolasi dari siklus pqm4 Dilithium3 pada 240 MHz:

| operasi | ESP32 (perkiraan) | Apple M2 (terukur) |
|---|---|---|
| verify | ~10 ms | 0,054 ms |
| sign | ~33 ms | 0,117 ms |

Dampaknya ke verifikasi batch di sisi RSU:

| batch | m × verify | W + T_proc | vs deadline 100 ms |
|---|---|---|---|
| t = 18 | 180 ms | 270 ms | **MISS** |
| t = 25 | 250 ms | 340 ms | **MISS** |
| t = 64 | 640 ms | 730 ms | **MISS** |

ESP32 tidak layak sebagai RSU pada beban skenario Anda, dengan selisih besar.

### 4. Memori sangat ketat begitu radio aktif

| | |
|---|---|
| stack `sign` ML-DSA-65 | ~84 KB |
| stack `verify` | ~54 KB |
| objek (pk+sk+sig) | ~9 KB |
| heap ESP32 tanpa WiFi | ~320 KB → **muat** |
| heap ESP32 **dengan** WiFi | ~160 KB → **sangat ketat** |

VANET jelas butuh radio. Menjalankan `sign` bersama stack WiFi/BLE membuat
margin heap sangat tipis; ESP32-S3 dengan PSRAM lebih longgar, tetapi PSRAM
jauh lebih lambat dari SRAM internal sehingga timing memburuk.

---

## Kapan ESP32 justru berguna

Ada satu pertanyaan yang **hanya** bisa dijawab perangkat kelas ini:

> Apakah OBU kelas mikrokontroler mampu menandatangani pesan BSM ML-DSA-65
> dalam anggaran waktunya?

Dengan `sign` ~33 ms dan laju BSM 10 msg/s (anggaran 100 ms per pesan), OBU
ESP32 memakai ~33% anggaran hanya untuk tanda tangan. Itu **layak namun ketat**
— dan ini temuan yang menarik untuk naskah, karena melengkapi sisi OBU yang
selama ini hanya diukur di M2.

Kalau Anda mau menambahkannya, cakupannya:

- **hanya** benchmark `keygen` / `sign` / `verify` ML-DSA-65 di ESP32
- dilaporkan sebagai *"OBU-class feasibility note"*, bukan pengganti Tabel V
- tidak menyentuh Tabel VIII–X, tidak menyentuh E1

Jalurnya: ESP-IDF + liboqs dikompilasi sebagai komponen. liboqs adalah C
portabel dan **tidak** secara resmi mendukung ESP-IDF, jadi anggap ini
pekerjaan eksperimental beberapa hari, bukan beberapa jam. Alternatif yang
lebih mulus: implementasi Dilithium referensi PQClean langsung sebagai
komponen ESP-IDF.

---

## Rekomendasi

| Prioritas | Perangkat | Menjawab | Usaha |
|---|---|---|---|
| **1** | **Raspberry Pi 4/5** | **E1 lintas kelas ARM + E2E kelas RSU** | akhir pekan |
| 2 | ESP32-S3 | kelayakan sign sisi OBU | beberapa hari |
| — | Cortex-M4 / pqm4 | referensi embedded murni | berbulan-bulan |

Kerjakan RPi dulu. ESP32 hanya kalau Anda ingin menambah catatan sisi-OBU
setelah RPi selesai — dan itu bersifat pelengkap, bukan pengganti.

Semua angka ESP32 di atas adalah **ekstrapolasi dari siklus Cortex-M4**, bukan
pengukuran. Kalau Anda memutuskan menempuh jalur ini, angka sebenarnya harus
diukur sebelum masuk naskah.
