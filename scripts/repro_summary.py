#!/usr/bin/env python3
"""Summarise repeated runs of the paper's original bench_pqcbas.py.

Usage: python3 repro_summary.py DIR
DIR holds sub-folders r1, r2, ... each with the bench_results.json of one run.
Prints, per run, the ML-DSA-65 CertValidate and ECDSA-P256 verify means and their
ratio (above 1 means ML-DSA is faster), then the cross-run mean of the ratio.
"""
import glob
import json
import os
import statistics
import sys

d = sys.argv[1] if len(sys.argv) > 1 else "."
rows = []
for f in sorted(glob.glob(os.path.join(d, "r*", "bench_results.json"))):
    j = json.load(open(f))
    cv, ev = j["CertValidate"], j["ecdsa_p256"]["verify_ms"]
    sg, es = j["Sign"], j["ecdsa_p256"]["sign_ms"]
    rows.append((os.path.basename(os.path.dirname(f)), cv[0], cv[1], ev[0], ev[1], sg[0], es[0]))
if not rows:
    sys.exit("no bench_results.json found under " + d)
print("%-4s %12s %8s %12s %8s %9s %12s %12s" % (
    "run", "CertVal ms", "sd", "ECDSA ver ms", "sd", "ratio", "Sign ms", "ECDSA sgn ms"))
for r in rows:
    print("%-4s %12.4f %8.4f %12.4f %8.4f %9.3f %12.4f %12.4f" % (
        r[0], r[1], r[2], r[3], r[4], r[3] / r[1], r[5], r[6]))
rs = [r[3] / r[1] for r in rows]
print("ratio ECDSA/ML-DSA over %d runs: mean %.3f  min %.3f  max %.3f" % (
    len(rs), statistics.mean(rs), min(rs), max(rs)))
print("paper (29 Sep): CertValidate 0.0527 ms, ECDSA verify 0.0588 ms, ratio 1.116")
