#!/usr/bin/env bash
# Run the ORIGINAL P0-7 analysis on the rerun outputs and compare with the archived tables.
set -u
H="$HOME"
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$H/pqcbas_rerun_20261025"
SRC="$H/pqcbas-p0-5-matched120/runs"
ORIG="$H/pq-cbas-dsh-vc-v141/data/phymac_final_8694_20261001/p0-7_final_analysis"
VIEW="$R/raw_view"
OUT="$R/analysis"
rm -rf "$VIEW" "$OUT"; mkdir -p "$VIEW" "$OUT"
miss=0
for d in "$SRC"/*/; do
  t="$(basename "$d")"
  if [ -f "$R/runs/$t/DONE" ] && [ -f "$R/runs/$t/results-explicit/$t.sca" ]; then
    mkdir -p "$VIEW/$t"
    ln -s "$R/runs/$t/run_metadata.json" "$VIEW/$t/run_metadata.json"
    ln -s "$R/runs/$t/results-explicit/$t.sca" "$VIEW/$t/$t.sca"
  else
    miss=$((miss+1))
  fi
done
echo "runs ready: $(ls "$VIEW" | wc -l), missing: $miss"
[ "$miss" -eq 0 ] || { echo "STOP: matrix not complete, rerun the matrix command first"; exit 2; }
python3 -I - "$ORIG/analyze_final_120.py" "$R/analyze_rerun.py" <<'PYEOF'
import sys
src = open(sys.argv[1], encoding="utf-8").read()
a = src.index("RAW = Path(")
b = src.index("OUT.mkdir(")
new = 'import os\nRAW = Path(os.environ["RERUN_RAW"])\nOUT = Path(os.environ["RERUN_OUT"])\n\n'
open(sys.argv[2], "w", encoding="utf-8").write(src[:a] + new + src[b:])
PYEOF
RERUN_RAW="$VIEW" RERUN_OUT="$OUT" python3 -I "$R/analyze_rerun.py" > "$R/analysis_stdout.txt" 2>&1 || { echo "STOP: analysis failed"; tail -8 "$R/analysis_stdout.txt"; exit 3; }
python3 -I "$HERE/compare_csv.py" "$ORIG" "$OUT"
