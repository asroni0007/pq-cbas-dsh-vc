import re
import sys

IGN = re.compile(r'^(run |attr (datetime|datetimef|processid|runnumber|resultdir|runid)\b)')
LOC = re.compile(r' at [^"]*/([^/"]+:\d+)"')


def load(p):
    out = []
    for line in open(p, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if IGN.match(line):
            continue
        out.append(LOC.sub(r' at \1"', line))
    return out


a, b = load(sys.argv[1]), load(sys.argv[2])
d = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
n_s = sum(1 for line in a if line.startswith(("scalar ", "statistic ")))
print("lines: archived %d, rerun %d; scalar/statistic lines (archived): %d" % (len(a), len(b), n_s))
print("differing lines: %d" % (len(d) + abs(len(a) - len(b))))
for i, x, y in d[:8]:
    print("  line %d\n   old: %s\n   new: %s" % (i, x[:160], y[:160]))
ok = not d and len(a) == len(b)
print("VERDICT:", "IDENTICAL (apart from run id, timestamps, paths)" if ok else "DIFFERENT")
sys.exit(0 if ok else 1)
