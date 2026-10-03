#!/bin/bash
cd ~/Desktop/esp32_unit2 || exit 1
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
while [ -e "uecc_unit${U}_run${n}.log" ]; do n=$((n+1)); done
F="uecc_unit${U}_run${n}.log"
echo "Papan: Unit $U ($MAC) di $P -> $F"
"$PYBIN" cap4.py "$P" "$F" || { echo "PEREKAMAN GAGAL"; exit 1; }
MAC2=$(readmac)
echo "$MAC $MAC2" > "${F%.log}.mac"
if [ "$MAC" = "$MAC2" ]; then echo "MAC sebelum dan sesudah sama: OK"; else echo "MAC BERUBAH: log tidak valid"; fi
KG=$(grep -c '^KG,' "$F"); S=$(grep -c '^S,' "$F"); FS=$(grep -c '^F,' "$F"); V=$(grep -c '^V,' "$F"); H=$(grep -c '^H,' "$F")
PL=$(grep -c 'PLATFORM\] ESP32' "$F"); RR=$(grep -c reset_reason "$F"); NG=$(grep -c NEGATIVE_CONTROL "$F"); OK=$(grep -c UECC_BASELINE_OK "$F"); FL=$(grep -c _FAIL "$F")
echo "$F baris=$(wc -l < "$F") KG=$KG S=$S F=$FS V=$V H=$H PLAT=$PL RR=$RR NEG=$NG OK=$OK FAIL=$FL"
if [ "$KG" = 20 ] && [ "$S" = 500 ] && [ "$FS" = 500 ] && [ "$V" = 500 ] && [ "$H" = 200 ] && [ "$PL" = 1 ] && [ "$RR" = 1 ] && [ "$NG" = 1 ] && [ "$OK" = 1 ] && [ "$FL" = 0 ] && [ "$MAC" = "$MAC2" ]; then
  echo "HASIL: VALID (Unit $U)"
else
  echo "HASIL: TIDAK VALID, pindahkan ke excluded"
fi
grep -E "^(KEYGEN|SIGN_DIGEST|FRAME_SIGN|VERIFY) " "$F" | cut -c1-100
