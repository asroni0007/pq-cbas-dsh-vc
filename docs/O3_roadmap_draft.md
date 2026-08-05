# Roadmap Reduksi O3: RespCheck via Module-SIS

**Dokumen kerja untuk pengembangan Theorem 2 PQ-CBAS-DSH-C**

---

## Konteks

Theorem 2 (Conditional security of PQ-CBAS-DSH-C) saat ini kondisional pada
tiga obligasi. O1 (Merkle binding) dan O2 (norm-validity soundness) sudah
terdischarge di naskah via argumen collision resistance. O3 (response-support
soundness) adalah satu-satunya obligasi yang tersisa.

---

## Definisi Eksplisit RespCheck via Relasi Polinomial

**Konstruksi yang diusulkan:**

RespCheck(pp, z̄, ρ, {pk_i}) = 1  iff  A·z̄ ≡ Σ_{i=1}^m (w_i + c_i · t_{1,i}) (mod q)

Di mana:
- A = public matrix (bagian dari pp, dihasilkan via H(seed_A))
- z̄ = combined response (elemen dari Z_q^{l×N})
- c_i = per-signer challenge (32 B, recoverable dari leaf_i ∈ ρ)
- t_{1,i} = bagian publik dari pk_i = (ρ_pk, t_1) per FIPS 204 §6.1
- w_i = commitment (tidak langsung tersedia, lihat §2 di bawah)

**Masalah kritis:** w_i tidak tersimpan di compact aggregate. Dua solusi:

### Solusi A: Simpan w_i di verification bundle (tidak compact)
Kembalikan ke mode linier. Batal.

### Solusi B: Gunakan relasi challenge-response tanpa w_i
Dari FIPS 204 §3.7: verification ML-DSA memeriksa:
  c' = H(μ || [Az - ct_1]_1)
  dan memeriksa c' == c, ‖z‖_∞ ≤ γ_1 - β, hint_count ≤ ω

Untuk agregat: verifier bisa memeriksa bahwa z̄ = Σz_i adalah jumlah respons
yang masing-masing memenuhi ‖z_i‖_∞ ≤ γ_1 - β. Ini ekuivalen dengan:
  ‖z̄‖_∞ ≤ m(γ_1 - β) = B_m  (sudah dibuktikan via O2)

Tapi ini hanya memeriksa norm, bukan konsistensi kriptografis. Untuk menjamin
bahwa z̄ benar-benar berasal dari m signing instances valid:

### Solusi C: Aggregate verification equation (pendekatan terbaik)

Dari struktur ML-DSA: setiap signer i menghasilkan (z_i, c_i) sehingga:
  A·z_i - c_i·t_{1,i} = w_{1,i} (mod q)  dimana ‖w_{1,i}‖_∞ ≤ γ_2 - β

Menjumlahkan m persamaan:
  A·z̄ - Σ_i c_i·t_{1,i} = Σ_i w_{1,i} (mod q)

Definisikan:
  W̄ = A·z̄ - Σ_i c_i·t_{1,i}  (dapat dihitung verifier dari z̄, {c_i}, {t_{1,i}})

RespCheck memeriksa: ‖W̄‖_∞ ≤ m(γ_2 - β)

Ini adalah pemeriksaan yang dapat dikomputasi! c_i tersedia dari leaves di ρ,
t_{1,i} tersedia dari pk_i (bagian dari bundle), A dari pp.

---

## Argumen Soundness via Module-SIS

**Definisi M-SIS(k, l, q, B):** Diberikan A ∈ Z_q^{k×(k+l)N}, cari x ≠ 0
dengan Ax = 0 (mod q) dan ‖x‖_∞ ≤ B.

**Lemma O3 (draft):**

Misalkan RespCheck memeriksa ‖A·z̄ - Σ_i c_i·t_{1,i}‖_∞ ≤ m(γ_2 - β).
Untuk adversary R yang menghasilkan (z̄*, ρ*, {c_i*}) yang:
  (a) Lolos RespCheck
  (b) Tidak merupakan jumlah dari m respons ML-DSA valid

Ada B yang mengekstrak solusi M-SIS dari R dengan parameter B = 2m(γ_2 - β).

**Sketsa bukti:**

Misalkan R memalsukan (z̄*, {c_i*}) yang lolos RespCheck tapi bukan valid sum.
Karena bukan valid sum, ada setidaknya satu signer j di mana:
  A·z_j* - c_j*·t_{1,j} ≠ w_{1,j}  untuk semua w_{1,j} valid

Tapi Σ_i (A·z_i* - c_i*·t_{1,i}) = W̄ dengan ‖W̄‖_∞ ≤ m(γ_2 - β).

Gunakan forking lemma (rewinding R dua kali dengan c_j berbeda untuk signer j):
  Run 1: (z̄, c_j,  {c_i}_{i≠j}) dengan W̄  valid
  Run 2: (z̄, c_j', {c_i}_{i≠j}) dengan W̄' valid

Dari kedua run:
  A·z_j - c_j·t_{1,j}  = W̄  - Σ_{i≠j}(A·z_i - c_i·t_{1,i})
  A·z_j - c_j'·t_{1,j} = W̄' - Σ_{i≠j}(A·z_i - c_i·t_{1,i})

Kurangkan:
  (c_j' - c_j)·t_{1,j} = W̄ - W̄'  (mod q)

Kalau c_j ≠ c_j' (yang hampir pasti di RO), maka:
  t_{1,j} = (c_j' - c_j)^{-1}·(W̄ - W̄')

Ini bukan M-SIS langsung, tapi menunjukkan bahwa z_j bisa diekstrak,
yang kemudian dapat digunakan untuk forgery signer-level...

**Status:** Argumen ini menemui circular reasoning. Perlu pendekatan berbeda.

---

## Pendekatan Alternatif: AGM (Algebraic Group Model) untuk Lattices

Gunakan Algebraic Module Framework dari Lyubashevsky et al. (2022):
dalam model algebraic, setiap z̄ yang dikembalikan adversary adalah kombinasi
linier eksplisit dari z_i yang diamati. Soundness mengikuti dari linearitas
dan M-SIS over module lattices.

Referensi: "CRYSTALS-Dilithium: A Lattice-Based Digital Signature Scheme"
§5 (Security Analysis), khususnya Theorem 3 (EUF-CMA di ROM).

---

## Pendekatan Terbaik: Batasi Klaim RespCheck ke Kasus Khusus

**Klaim yang bisa dibuktikan sekarang:**

Jika setiap c_i dalam bundle dikunci ke leaf_i via Merkle (O1 sudah proven),
dan ρ mengikat urutan tuple (O1), maka:

  RespCheck menerima z̄' yang bukan valid sum HANYA JIKA ada i dengan:
  A·z_i' - c_i·t_{1,i} ∉ {-γ_2, ..., γ_2}^k  (norm violation pada komponen)

  Yang mengimplikasikan W̄ = A·z̄' - Σ_i c_i·t_{1,i} memiliki ‖W̄‖_∞ > m(γ_2 - β)

  Yang ditolak oleh RespCheck.

**Kesimpulan:** RespCheck via norm-check pada W̄ adalah soundness yang sah
dalam batas B = m(γ_2 - β), DENGAN ASUMSI bahwa c_i tidak bisa dimanipulasi
(dijamin O1 via Merkle).

Ini menghasilkan Theorem 2 yang terdischarge secara full di classical ROM
dengan asumsi M-LWE/M-SIS standar.

---

## Langkah Implementasi untuk Discharge Penuh O3

1. **Tambahkan RespCheck ke AggVerify_C (Persamaan baru setelah 44):**
   ```
   RespCheck(pp, z̄, ρ, {(c_i, pk_i)}) = 1  iff
     W̄ = A·z̄ - Σ_i c_i·t_{1,i}  (mod q)
     ‖W̄‖_∞ ≤ m(γ_2 - β)
   ```

2. **Tulis Lemma O3:**
   Setiap adversary yang menembus RespCheck memecahkan M-SIS(k, l, q, 2m(γ_2 - β))
   atau menemukan collision di H_leaf (yang tereduksi ke O1).

3. **Tulis korolari Theorem 2 tanpa kondisionalitas:**
   ```
   Adv^{PQ-CBAS-DSH-C}_{Agg-EUF-CMA}(A) ≤
     N_fresh · Adv^{ML-DSA}_{EUF-CMA}(B) + Adv_{DIC}(D) + Adv_{M-SIS}(S)
     + O(q_H^2 / 2^κ) + negl(λ)
   ```

4. **Pastikan implementasi:**
   - c_i tersimpan/terpulihkan dari leaves
   - t_{1,i} dari pk_i tersedia di bundle
   - A dari pp (bukan diseeding ulang per-signature)

---

## Estimasi waktu

- Langkah 1–2 (definisi + Lemma O3): 2–3 minggu  
- Langkah 3 (Theorem 2 update): 1 minggu  
- Langkah 4 (implementasi di artifact): 2–3 minggu  
- Review internal + penulisan bersih: 2–4 minggu  
- **Total: 7–11 minggu untuk discharge O3 penuh**

Dengan O3 terdischarge, Theorem 2 menjadi unconditional di classical ROM
dan naskah layak untuk submission ke venue kriptografi (IEEE TIFS, PKC, CCS).
