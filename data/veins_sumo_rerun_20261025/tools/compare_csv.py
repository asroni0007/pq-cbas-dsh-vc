import csv
import math
import sys
from pathlib import Path

A, B = Path(sys.argv[1]), Path(sys.argv[2])
NAMES = ["P0-7_FINAL_120_RUNS.csv", "P0-7_FINAL_12_CELL_SUMMARY.csv",
         "P0-7_PAIRED_SEED_DIFFERENCES.csv", "P0-7_PAIRED_SIGN_TEST.csv",
         "P0-7_PAPER_COMPACT_TABLE.csv", "P0-7_FINAL_PHYMAC_PAPER_TABLE.csv"]


def num(x):
    try:
        return float(x)
    except ValueError:
        return None


def same(x, y):
    if x == y:
        return True
    a, b = num(x), num(y)
    if a is None or b is None:
        return False
    if math.isnan(a) and math.isnan(b):
        return True
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


bad = 0
done = 0
for n in NAMES:
    pa, pb = A / n, B / n
    if not pa.exists() or not pb.exists():
        print("%-36s skipped (archived %s, rerun %s)" % (n, pa.exists(), pb.exists()))
        continue
    done += 1
    ra, rb = list(csv.reader(open(pa))), list(csv.reader(open(pb)))
    if ra[0] != rb[0] or len(ra) != len(rb):
        print("%-36s STRUCTURE DIFFERS (cols %d/%d, rows %d/%d)" % (n, len(ra[0]), len(rb[0]), len(ra), len(rb)))
        bad += 1
        continue
    diffs = [(i, ra[0][j], x, y) for i, (r1, r2) in enumerate(zip(ra[1:], rb[1:]), 1)
             for j, (x, y) in enumerate(zip(r1, r2)) if not same(x, y)]
    rows_bad = len({d[0] for d in diffs})
    print("%-36s rows %3d: identical %3d, differing %3d (cells differing: %d)" % (
        n, len(ra) - 1, len(ra) - 1 - rows_bad, rows_bad, len(diffs)))
    for i, col, x, y in diffs[:5]:
        print("    row %d col %s: archived %s, rerun %s" % (i, col, x[:40], y[:40]))
    bad += bool(diffs)
ok = bad == 0 and done > 0
print("VERDICT:", ("ALL %d COMPARED TABLES MATCH" % done) if ok else "DIFFERENCES FOUND or nothing compared (%d compared)" % done)
sys.exit(0 if ok else 1)
