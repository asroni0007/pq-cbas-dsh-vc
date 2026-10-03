#!/bin/bash
cd ~/Desktop/esp32_unit2 || exit 1
MODE=$1
mkdir -p excluded
for i in 1 2 3; do
  out=$(./rec2.sh "$MODE" | tee /dev/stderr)
  if echo "$out" | grep -q "HASIL: VALID"; then
    echo "SELESAI: satu log valid diperoleh pada percobaan ke-$i"
    exit 0
  fi
  f=$(echo "$out" | grep -o "${MODE}_unit[AB]_run[0-9]*\.log" | head -1)
  if [ -n "$f" ] && [ -e "$f" ]; then
    mv "$f" "excluded/${f%.log}_gagal$(date +%H%M%S).log"
    mv "${f%.log}.mac" excluded/ 2>/dev/null
    echo "log gagal dipindah ke excluded, mengulang..."
  else
    echo "perekaman tidak menghasilkan log, berhenti"
    exit 1
  fi
done
echo "TIGA PERCOBAAN GAGAL: periksa kabel dan papan"
exit 1
