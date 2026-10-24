#!/usr/bin/env bash
# Rerun of the final Veins/SUMO matrix from the deposited inputs. Read-only on your inputs.
# Usage: rerun.sh preflight | smoke | matrix [MAX_RUNS]
set -u
H="$HOME"
HERE="$(cd "$(dirname "$0")" && pwd)"
OPP="${OPP:-$H/pq-opp-core/omnetpp-6.1.0}"
VEINS="${VEINS_HOME:-$H/backup_ext/veins-5.3.1-macmetrics-recovered}"
PROJ="${PROJ:-$H/pqcbas-phymac-app-recovered/veins_project_template}"
SUMO="${SUMO_BIN:-$H/pq-sumo-1.22.0-src/bin/sumo}"
SRC_RUNS="$H/pqcbas-p0-5-matched120/runs"
SMOKE="$H/pqcbas-final-full-8694-smoke-s1"
OUT="${OUT:-$H/pqcbas_rerun_20261025}"
PORT=9999
LPID=""
mkdir -p "$OUT"
export OMNETPP_ROOT="$OPP" OPP_ENV_VERSION="${OPP_ENV_VERSION:-1}"; export PATH="$OPP/bin:$PATH"
command -v opp_run >/dev/null 2>&1 || export PATH="$OPP/bin:$PATH"
export SUMO_HOME="${SUMO_HOME:-$H/pq-sumo-1.22.0-src}"
LIBPQ="$PROJ/libpqcbas.dylib"
LIBV="$VEINS/out/clang-release/src/libveins.dylib"
[ -f "$LIBV" ] || LIBV="$VEINS/src/libveins.dylib"
trap '[ -n "$LPID" ] && kill "$LPID" 2>/dev/null' EXIT

pre() {
  local bad=0 f
  for f in "$LIBPQ" "$LIBV" "$SUMO" "$VEINS/sumo-launchd.py" "$SRC_RUNS" "$SMOKE/omnetpp.ini" "$HERE/compare_sca.py"; do
    if [ -e "$f" ]; then echo "OK   $f"; else echo "MISS $f"; bad=1; fi
  done
  if command -v opp_run >/dev/null 2>&1; then echo "OK   opp_run $(command -v opp_run)"; else echo "MISS opp_run"; bad=1; fi
  echo "sumo: $("$SUMO" --version 2>/dev/null | head -1)"
  echo "libpqcbas sha256 $(shasum -a 256 "$LIBPQ" | cut -c1-16) (expected 609182f550c7a837)"
  if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then echo "BUSY port $PORT"; bad=1; else echo "OK   port $PORT free"; fi
  echo "runs available: $(ls "$SRC_RUNS" 2>/dev/null | wc -l)"
  df -h "$OUT" | tail -1
  ls -la "$SMOKE/results-explicit" 2>/dev/null | head -6
  return $bad
}

start_launchd() {
  python3 "$VEINS/sumo-launchd.py" -vv -c "$SUMO" -p $PORT -L "$OUT/launchd.log" >"$OUT/launchd.stdout" 2>&1 &
  LPID=$!
  sleep 2
  kill -0 "$LPID" 2>/dev/null || { echo "STOP: launchd did not start, see $OUT/launchd.stdout"; exit 3; }
}

run_one() {  # $1 = source run dir, $2 = tag
  local d="$OUT/runs/$2" rc
  [ -f "$d/DONE" ] && { echo "skip $2"; return 0; }
  kill -0 "$LPID" 2>/dev/null || start_launchd
  rm -rf "$d"; mkdir -p "$d"; cp -R "$1/." "$d/"
  rm -rf "$d/results-explicit"; mkdir -p "$d/results-explicit"
  ( cd "$d" && opp_run -u Cmdenv -n "$PROJ:$VEINS/src/veins" -l "$LIBV" -l "$LIBPQ" -f omnetpp.ini --debug-on-errors=false ) >"$d/run.log" 2>&1
  rc=$?
  if [ $rc -eq 0 ] && ls "$d"/results-explicit/*.sca >/dev/null 2>&1; then
    [ "${KEEP_VEC:-0}" = 1 ] || rm -f "$d"/results-explicit/*.vec "$d"/results-explicit/*.vci; date +%FT%T >"$d/DONE"; echo "done $2"
  else
    echo "FAIL $2 rc=$rc, see $d/run.log"; return 1
  fi
}

case "${1:-}" in
  preflight) pre ;;
  smoke)
    pre || { echo "preflight failed"; exit 2; }
    start_launchd
    run_one "$SMOKE" smoke_final_full_8694_s1 || exit 4
    python3 -I "$HERE/compare_sca.py" "$SMOKE"/results-explicit/*.sca "$OUT"/runs/smoke_final_full_8694_s1/results-explicit/*.sca ;;
  matrix)
    pre || { echo "preflight failed"; exit 2; }
    start_launchd
    n=0; fail=0; max="${2:-0}"
    for d in "$SRC_RUNS"/*/; do
      run_one "${d%/}" "$(basename "$d")" || fail=$((fail+1))
      n=$((n+1))
      if [ "$max" -gt 0 ] && [ "$n" -ge "$max" ]; then break; fi
    done
    echo "finished: $n attempted, $fail failed" ;;
  *) echo "usage: $0 preflight | smoke | matrix [MAX_RUNS]"; exit 1 ;;
esac
