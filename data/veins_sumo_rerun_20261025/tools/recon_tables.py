import csv, math, os, sys
from itertools import product
H = os.path.expanduser("~")
R = sys.argv[1] if len(sys.argv) > 1 else H + "/pqcbas_rerun_20261025/analysis"
A = sys.argv[2] if len(sys.argv) > 2 else H + "/pq-cbas-dsh-vc-v141/data/phymac_final_8694_20261001/p0-7_final_analysis"
OUT = sys.argv[3] if len(sys.argv) > 3 else H + "/pqcbas_rerun_20261025/analysis_recon"
os.makedirs(OUT, exist_ok=True)

def rd(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))

def nk(v):
    try:
        return str(int(float(v)))
    except ValueError:
        return v

runs = rd(R + "/P0-7_FINAL_120_RUNS.csv")
summ = rd(R + "/P0-7_FINAL_12_CELL_SUMMARY.csv")
VAL = {(r["variant"], int(float(r["target"])), int(float(r["seed"]))): r for r in runs}
SEEDS = sorted({k[2] for k in VAL})
PAIRS = [("digest", "small"), ("full", "small"), ("full", "digest")]
TARGETS = [10, 25, 50, 100]
PM = ["logical_completion_rate", "on_time_completion_rate", "fragment_reception_rate",
      "mac_queue_delay_mean_ms", "mac_queue_length_mean"]
SM = ["logical_completion_rate", "fragment_reception_rate", "mac_queue_delay_mean_ms", "mac_queue_length_mean"]

def diffs(a, b, t, m):
    return [float(VAL[(a, t, s)][m]) - float(VAL[(b, t, s)][m]) for s in SEEDS]

def sd(x, ddof):
    mu = sum(x) / len(x)
    return math.sqrt(sum((v - mu) ** 2 for v in x) / (len(x) - ddof))

def sign_p(pos, neg):
    n, k = pos + neg, min(pos, neg)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)

def build_pd(ddof):
    rows = []
    for (a, b), t, m in product(PAIRS, TARGETS, PM):
        d = diffs(a, b, t, m)
        rows.append(dict(variant_a=a, variant_b=b, target=t, metric=m, n_pairs=len(d),
                         mean_difference=sum(d) / len(d), sd_difference=sd(d, ddof),
                         min_difference=min(d), max_difference=max(d)))
    return rows

def build_sign():
    rows = []
    for (a, b), t, m in product(PAIRS, TARGETS, SM):
        d = diffs(a, b, t, m)
        p, n = sum(v > 0 for v in d), sum(v < 0 for v in d)
        rows.append(dict(variant_a=a, variant_b=b, target=t, metric=m, n_pairs=len(d), positive=p,
                         negative=n, zero=len(d) - p - n, exact_two_sided_sign_p=sign_p(p, n),
                         all_same_direction=(p == 0 or n == 0)))
    return rows

def build_pt():
    rows = []
    for s in summ:
        f = lambda c: float(s[c])
        rows.append(dict(variant=s["variant"], target=s["target"], payload_bytes=s["payload_bytes"],
                         fragments=s["fragments"], completion_pct=100 * f("logical_completion_rate_mean"),
                         on_time_pct=100 * f("on_time_completion_rate_mean"),
                         fragment_reception_pct=100 * f("fragment_reception_rate_mean"),
                         reassembly_timeout_per_generated_pct=100 * f("reassembly_timeout_per_generated_mean"),
                         mac_queue_delay_mean_ms=f("mac_queue_delay_mean_ms_mean"),
                         mac_queue_delay_sd_ms=f("mac_queue_delay_mean_ms_sd"),
                         mac_queue_length_mean=f("mac_queue_length_mean_mean")))
    return rows

def cmp(rows, fn, keys):
    arch = rd(A + "/" + fn)
    idx = {tuple(nk(str(r[k])) for k in keys): r for r in rows}
    ex = cl = bad = miss = 0
    for r in arch:
        n = idx.get(tuple(nk(r[c]) for c in keys))
        if n is None:
            miss += 1
            continue
        ok = exact = True
        for c, v in r.items():
            w = str(n[c])
            if w == v:
                continue
            exact = False
            try:
                ok = ok and math.isclose(float(w), float(v), rel_tol=1e-9, abs_tol=1e-12)
            except ValueError:
                ok = False
        ex += exact
        cl += ok and not exact
        bad += not ok
    print("%-34s arch %3d: exact %3d, within 1e-9 %3d, differ %3d, missing %3d, recon %d"
          % (fn, len(arch), ex, cl, bad, miss, len(rows)))
    return bad + miss == 0 and len(rows) == len(arch)

def wr(fn, rows):
    with open(OUT + "/" + fn, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

res = []
for dd in (1, 0):
    print("sd ddof =", dd)
    pd_rows = build_pd(dd)
    ok = cmp(pd_rows, "P0-7_PAIRED_SEED_DIFFERENCES.csv", ["variant_a", "variant_b", "target", "metric"])
    if ok:
        break
res.append(ok)
wr("P0-7_PAIRED_SEED_DIFFERENCES.csv", pd_rows)
sg = build_sign()
res.append(cmp(sg, "P0-7_PAIRED_SIGN_TEST.csv", ["variant_a", "variant_b", "target", "metric"]))
wr("P0-7_PAIRED_SIGN_TEST.csv", sg)
pt = build_pt()
res.append(cmp(pt, "P0-7_FINAL_PHYMAC_PAPER_TABLE.csv", ["variant", "target"]))
wr("P0-7_FINAL_PHYMAC_PAPER_TABLE.csv", pt)
print("VERDICT:", "ALL 3 RECONSTRUCTED TABLES MATCH THE ARCHIVE" if all(res) else "DIFFERENCES FOUND %s" % res)
