#!/usr/bin/env bash
# cek_artefak.sh — audit artefak PQ-CBAS-DSH sebelum diunggah/di-submit.
#
#   bash cek_artefak.sh                    # audit folder saat ini
#   bash cek_artefak.sh /path/ke/artefak   # audit folder tertentu
#
# Memeriksa: struktur, sintaks kode, patch CI, JSON hasil, kecocokan angka
# dengan naskah, dan sisa berkas sampah. Tidak mengubah apa pun.

set -uo pipefail
A="${1:-.}"
cd "$A" || { echo "folder tidak ditemukan: $A"; exit 1; }

OK=0; WARN=0; FAIL=0
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; OK=$((OK+1)); }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; WARN=$((WARN+1)); }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; FAIL=$((FAIL+1)); }
hdr()  { printf "\n\033[1m%s\033[0m\n"  "$1"; }

echo "════════════════════════════════════════════════════════"
echo " AUDIT ARTEFAK PQ-CBAS-DSH"
echo " folder: $(pwd)"
echo "════════════════════════════════════════════════════════"

# ---------- 1. STRUKTUR ----------
hdr "1. Struktur folder"
for d in paper src esp32 sumo results scripts docs; do
  if [ -d "$d" ]; then ok "$d/ ($(find "$d" -type f | wc -l | tr -d ' ') berkas)"
  else bad "$d/ TIDAK ADA"; fi
done
[ -f README.md ] && ok "README.md" || bad "README.md TIDAK ADA"

# ---------- 2. KODE SUMBER ----------
hdr "2. Kode sumber"
for f in bench_pqcbas.py e2e_workflow.py sumo_pqcbas_bridge.py ci_stats.py transport_budget.py; do
  if [ -f "src/$f" ]; then
    if python3 -m py_compile "src/$f" 2>/dev/null; then ok "src/$f"
    else bad "src/$f — SINTAKS ERROR"; fi
  else bad "src/$f TIDAK ADA"; fi
done
rm -rf src/__pycache__ 2>/dev/null

# ---------- 3. PATCH CI (Student-t) ----------
hdr "3. Patch confidence interval"
for f in src/e2e_workflow.py src/sumo_pqcbas_bridge.py; do
  if [ ! -f "$f" ]; then bad "$f tidak ada"; continue; fi
  if grep -q "mean_ci95" "$f"; then ok "$(basename "$f") memakai Student-t"
  else bad "$(basename "$f") MASIH pakai z=1.96 — angka tidak akan cocok naskah"; fi
  grep -q "1.96" "$f" && warn "$(basename "$f") masih memuat '1.96' — periksa manual"
done

# ---------- 4. HASIL ----------
hdr "4. Berkas hasil"
N=$(ls results/*.json 2>/dev/null | wc -l | tr -d ' ')
[ "$N" -gt 0 ] && ok "$N berkas JSON" || bad "results/ kosong"
for f in results/*.json; do
  [ -e "$f" ] || continue
  python3 -c "import json,sys; json.load(open('$f'))" 2>/dev/null \
    || bad "$(basename "$f") — JSON RUSAK"
done

# cek apakah hasil 20-seed sudah ada
if grep -lq '"seeds": *20' results/*.json 2>/dev/null; then
  ok "hasil 20-seed ditemukan"
else
  warn "belum ada hasil 20-seed di results/ — salin dari folder kerja"
fi

# ---------- 5. KECOCOKAN ANGKA DENGAN NASKAH ----------
hdr "5. Angka hasil vs naskah"
python3 - <<'PY'
import json, glob, os
target = {  # (nilai naskah, toleransi)
 "highway-n20":        (46.9, 0.5),
 "highway-n20-attack": (46.9, 0.5),
 "urban-n30":          (47.3, 0.5),
 "intersection-n15":   (47.6, 0.5),
}
f = "results/e2e_results_W90_full.json"
if not os.path.exists(f):
    cand = [x for x in glob.glob("results/e2e*full*.json")]
    f = cand[0] if cand else None
if not f:
    print("  ! tidak ada e2e full-cert JSON untuk dibandingkan"); raise SystemExit
d = json.load(open(f))
rows = d.get("summary", d if isinstance(d, list) else [])
seeds = d.get("seeds", "?")
print(f"  sumber: {os.path.basename(f)} (seeds={seeds})")
for r in rows:
    s = r.get("scenario"); v = r.get("e2e_mean_ms")
    if s in target:
        exp, tol = target[s]
        mark = "✓" if abs(v-exp) <= tol else "✗"
        print(f"    {mark} {s:22s} {v:5.1f} ms   (naskah {exp})")
PY

# ---------- 6. NASKAH ----------
hdr "6. Naskah"
[ -f paper/PQ-CBAS-DSH_VehicularCommunications.tex ] \
  && ok "sumber LaTeX ada" || bad "sumber LaTeX TIDAK ADA"
[ -f paper/elsarticle.cls ] && ok "elsarticle.cls disertakan" || warn "elsarticle.cls tidak ada"
IMG=$(ls paper/image*.png 2>/dev/null | wc -l | tr -d ' ')
[ "$IMG" -eq 6 ] && ok "6 gambar" || warn "gambar: $IMG (harusnya 6)"

if command -v pdflatex >/dev/null 2>&1; then
  (cd paper && pdflatex -interaction=nonstopmode -draftmode \
      PQ-CBAS-DSH_VehicularCommunications.tex >/tmp/_tex.log 2>&1)
  E=$(grep -c '^!' /tmp/_tex.log || true)
  [ "$E" -eq 0 ] && ok "kompilasi LaTeX bersih" || bad "LaTeX $E error — lihat /tmp/_tex.log"
  (cd paper && rm -f *.aux *.log *.out *.spl 2>/dev/null)
else
  warn "pdflatex tidak terpasang — lewati uji kompilasi"
fi

# ---------- 7. PLACEHOLDER YANG BELUM DIISI ----------
hdr "7. Placeholder"
for pat in "\[ISI" "\[Nama Penulis" "\[NAMA ALAT" "\[SPECIFY"; do
  C=$(grep -rl "$pat" paper/*.tex README.md 2>/dev/null | tr '\n' ' ')
  [ -n "$C" ] && warn "'$pat' masih ada di: $C"
done
[ "$WARN" -eq 0 ] && ok "tidak ada placeholder tersisa"

# ---------- 8. BERKAS SAMPAH ----------
hdr "8. Kebersihan"
J=$(find . \( -name '__pycache__' -o -name '.DS_Store' -o -name '*.pyc' \
    -o -name '*.aux' -o -name '*.log' \) 2>/dev/null | wc -l | tr -d ' ')
[ "$J" -eq 0 ] && ok "tidak ada berkas sampah" || warn "$J berkas sampah — jalankan pembersih di bawah"
V=$(find . -maxdepth 2 -name 'venv' -o -maxdepth 2 -name 'liboqs' 2>/dev/null | wc -l | tr -d ' ')
[ "$V" -eq 0 ] && ok "tidak ada venv/liboqs (jangan disertakan)" \
               || bad "$V folder venv/liboqs ikut terpaket — HAPUS, ukurannya besar & tidak portabel"

# ---------- RINGKASAN ----------
echo
echo "════════════════════════════════════════════════════════"
printf " LULUS: %d   PERINGATAN: %d   GAGAL: %d\n" "$OK" "$WARN" "$FAIL"
echo "════════════════════════════════════════════════════════"
if [ "$FAIL" -gt 0 ]; then
  echo " Ada kegagalan — perbaiki sebelum submit."; exit 1
elif [ "$WARN" -gt 0 ]; then
  echo " Siap, tapi periksa peringatan di atas."; exit 0
else
  echo " Artefak bersih dan siap diunggah."; exit 0
fi
