#!/usr/bin/env python3
"""E1 ratio = ECDSA-P256 verify mean / ML-DSA-65 CertValidate mean, per archived bench_results json.
Reports per-run ratios and between-run spread (no delta-method)."""
import json,os
H=os.path.dirname(os.path.abspath(__file__))
R={"M2 (k384 run)":"final_k384_20260929/mac_sumo/stack_B/bench_results_k384.json",
"Pi5 unit1 (k384)":"final_k384_20260929/pi5/bench_results_k384.json",
"Pi5 unit1 repeat":"pi5_repeat_20261001/raw_repeat_20261001/bench_results_rerun_20261001.json",
"Pi5 unit2":"pi5_unit2_20261003/bench_results.json",
"x86 laptop run1":"x86_laptop_20261003/run1_DEVIATION/bench_results.json",
"x86 laptop run2":"x86_laptop_20261003/run2_DEVIATION/bench_results.json",
"x86 laptop run3":"x86_laptop_20261003/run3_REPORTED/bench_results.json"}
for n,p in R.items():
    d=json.load(open(f"{H}/{p}"));cv=d["CertValidate"][0];e=d["ecdsa_p256"]
    es=e["sign_ms"][0];ev=e["verify_ms"][0];sg=d["Sign"][0]
    print(f"{n:18s} CertValidate {cv:.4f} ms  ECDSA verify {ev:.4f}  ratio {ev/cv:.3f}  | sign ratio ML/ECDSA {sg/es:.2f}")
