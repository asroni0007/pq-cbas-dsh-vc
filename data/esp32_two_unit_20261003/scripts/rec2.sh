#!/bin/bash
cd ~/Desktop/esp32_unit2 || exit 1
MODE=$1
case "$MODE" in
  final) END=ESP32_FINAL_BENCHMARK_OK ;;
  ecdsa) END=ESP32_ECDSA_BASELINE_OK ;;
  *) echo "pakai: ./rec2.sh final atau ./rec2.sh ecdsa"; exit 1 ;;
esac
PYBIN=${PYBIN:-$HOME/.venvs/pqcbas-final-py313/bin/python}
T=${T:-$(ls -d ~/Library/Arduino15/packages/esp32/tools/esptool_py/*/ | tail -1)}
GLOB=${GLOB:-/dev/cu.usbserial*}
ports=($GLOB)
if [ ${#ports[@]} -ne 1 ] || [ ! -e "${ports[0]}" ]; then
  echo "HARUS tepat satu papan tersambung. Terdeteksi: ${ports[*]}"
  exit 1
fi
P=${ports[0]}
readmac() { "${T}esptool" --port "$P" flash_id 2>&1 | grep -E "^MAC:" | awk '{print $2}'; }
MAC=$(readmac)
case "$MAC" in
  e0:8c:fe:5e:17:e8) U=A ;;
  00:70:07:25:3f:24) U=B ;;
  *) echo "MAC tidak dikenal: [$MAC]"; exit 1 ;;
esac
n=1
while [ -e "${MODE}_unit${U}_run${n}.log" ]; do n=$((n+1)); done
F="${MODE}_unit${U}_run${n}.log"
echo "Papan: Unit $U ($MAC) di $P -> $F"
"$PYBIN" cap5.py "$P" "$F" "$END" || { echo "PEREKAMAN GAGAL"; exit 1; }
MAC2=$(readmac)
echo "$MAC $MAC2" > "${F%.log}.mac"
if [ "$MAC" = "$MAC2" ]; then echo "MAC sebelum dan sesudah sama: OK"; else echo "MAC BERUBAH: log tidak valid"; fi
PL=$(grep -c 'PLATFORM\] ESP32' "$F"); OK=$(grep -c "$END" "$F"); FL=$(grep -c _FAIL "$F")
NUM='[0-9]+,[0-9]+\.[0-9]{6}[[:space:]]*$'
if [ "$MODE" = ecdsa ]; then
  KG=$(grep -c -E "^KG,$NUM" "$F"); S=$(grep -c -E "^S,$NUM" "$F"); FS=$(grep -c -E "^F,$NUM" "$F"); V=$(grep -c -E "^V,$NUM" "$F"); H=$(grep -c -E "^H,$NUM" "$F")
  NG=$(grep -c 'NEGATIVE_CONTROL.*REJECTED_OK' "$F")
  echo "$F baris=$(wc -l < "$F") KG=$KG S=$S F=$FS V=$V H=$H PLAT=$PL NEG=$NG OK=$OK FAIL=$FL"
  if [ "$KG" = 20 ] && [ "$S" = 500 ] && [ "$FS" = 500 ] && [ "$V" = 500 ] && [ "$H" = 200 ] && [ "$PL" = 1 ] && [ "$NG" = 1 ] && [ "$OK" = 1 ] && [ "$FL" = 0 ] && [ "$MAC" = "$MAC2" ]; then
    echo "HASIL: VALID (Unit $U)"
  else
    echo "HASIL: TIDAK VALID, pindahkan ke excluded"
  fi
  grep -E "^(KEYGEN|SIGN_DIGEST|FRAME_SIGN|VERIFY) " "$F" | cut -c1-100
else
  RS=$(grep -c -E "^RAW_SIGN,$NUM" "$F"); RF=$(grep -c -E "^RAW_FRAME_SIGN,$NUM" "$F"); RV=$(grep -c -E "^RAW_VERIFY,$NUM" "$F")
  ST=$(grep -c -E '^\[[1-6]/6\]' "$F"); SM=$(grep -c -E '^(keypair|DSH-48|sign-core|framework-sign|verify) ' "$F"); SQ=$(grep -c -E '^m=(1|2|5|10) n=' "$F")
  JS=$(grep -c -E '^\{"platform".*"heap_min":[0-9]+\}[[:space:]]*$' "$F")
  echo "$F baris=$(wc -l < "$F") RAW_SIGN=$RS RAW_FRAME=$RF RAW_VERIFY=$RV STAGE=$ST SUMMARY=$SM SEQ=$SQ JSON=$JS PLAT=$PL OK=$OK FAIL=$FL"
  if [ "$RS" = 500 ] && [ "$RF" = 500 ] && [ "$RV" = 500 ] && [ "$ST" = 6 ] && [ "$SM" = 5 ] && [ "$SQ" = 4 ] && [ "$JS" = 1 ] && [ "$PL" = 1 ] && [ "$OK" = 1 ] && [ "$FL" = 0 ] && [ "$MAC" = "$MAC2" ]; then
    echo "HASIL: VALID (Unit $U)"
  else
    echo "HASIL: TIDAK VALID, pindahkan ke excluded"
  fi
  grep -E "^(sign-core|framework-sign|verify) " "$F" | cut -c1-100
fi
