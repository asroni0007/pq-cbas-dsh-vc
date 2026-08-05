#!/usr/bin/env python3
"""e2e_workflow.py — Direct end-to-end workflow measurement for PQ-CBAS-DSH
on the liboqs ML-DSA-65 backend, replacing the inherited prototype trace.

Model (stated explicitly, reported in output):
- Messages arrive uniformly in time at `rate` msg/s per vehicle.
- The RSU closes a collection window every W ms (default 100); all tuples in
  the window are aggregated and verified as one batch at window close.
- Per-message E2E = (window_close - arrival)  [virtual waiting time]
                  + measured batch processing time  [real crypto, wall clock].
- Attack tuples carry a corrupted certificate, so they are rejected at
  CertValidate, before signature verification (early rejection).
- Transport delay is modeled as 0 and must be added for deployment estimates.

Scenarios follow Table VII of the manuscript (vehicles, t avg, totals).
Usage:  OQS_INSTALL_PATH=~/oqs python3 e2e_workflow.py [W_ms]
"""
import sys, time, json, secrets, hashlib, statistics, argparse
from ci_stats import mean_ci95
import numpy as np
import oqs

ALG = "ML-DSA-65"
ap = argparse.ArgumentParser()
ap.add_argument("--window", type=float, default=100.0, help="collection window W (ms)")
ap.add_argument("--seeds", type=int, default=1, help="number of independent seeds")
ap.add_argument("--digest", action="store_true",
                help="certificate-digest mode: tuples carry CertID=H_cert(Cert) (32 B); "
                     "verifier caches and validates each certificate once at first attach")
ARGS = ap.parse_args()
W = ARGS.window
DEADLINE = 100.0

def xof(domain, data, n=32):
    return hashlib.shake_256(domain + data).digest(n)

H_CERT, H_SIGN = b"PQ-CBAS-DSH/CERT", b"PQ-CBAS-DSH/SIGN"

class Vehicle:
    def __init__(self, ca):
        self.s = oqs.Signature(ALG)
        self.pk = self.s.generate_keypair()
        self.ID = secrets.token_bytes(16)
        mu = xof(H_CERT, self.ID + self.pk + b"ctx_cert")
        self.cert = (self.ID, self.pk, ca.sign(mu))
    def make_tuple(self, attack=False):
        m, fr = secrets.token_bytes(100), secrets.token_bytes(8)
        cert = self.cert
        if attack:  # forged certificate -> rejected at CertValidate
            cert = (self.ID, self.pk, secrets.token_bytes(len(self.cert[2])))
            sig = secrets.token_bytes(3309)
        else:
            mu = xof(H_SIGN, self.ID + m + self.pk + cert[0] + cert[1] + cert[2] + fr)
            sig = self.s.sign(mu)
        return (self.ID, m, self.pk, cert, sig, fr)

CERT_CACHE = {}
def process_window_digest(tuples, pk_CA, verifier):
    """Digest mode: CertValidate once per certificate (first attach), then cache by CertID."""
    t0 = time.perf_counter_ns()
    acc = rej = 0
    for (ID, m, pk, cert, sig, fr) in tuples:
        cid = xof(H_CERT, cert[0] + cert[1] + cert[2])  # CertID = H_cert(Cert)
        cached = CERT_CACHE.get(cid)
        if cached is None:
            mu_c = xof(H_CERT, cert[0] + cert[1] + b"ctx_cert")
            if not verifier.verify(mu_c, cert[2], pk_CA):
                rej += 1
                continue
            CERT_CACHE[cid] = cert
        mu_s = xof(H_SIGN, ID + m + pk + cert[0] + cert[1] + cert[2] + fr)
        if verifier.verify(mu_s, sig, pk):
            acc += 1
        else:
            rej += 1
    return (time.perf_counter_ns() - t0) / 1e6, acc, rej

def process_window(tuples, pk_CA, verifier):
    """Real crypto, wall-clock timed. Returns (elapsed_ms, accepted, rejected)."""
    t0 = time.perf_counter_ns()
    acc = rej = 0
    for (ID, m, pk, cert, sig, fr) in tuples:
        mu_c = xof(H_CERT, cert[0] + cert[1] + b"ctx_cert")
        if not verifier.verify(mu_c, cert[2], pk_CA):
            rej += 1
            continue  # early rejection: signature verification skipped
        mu_s = xof(H_SIGN, ID + m + pk + cert[0] + cert[1] + cert[2] + fr)
        if verifier.verify(mu_s, sig, pk):
            acc += 1
        else:
            rej += 1
    return (time.perf_counter_ns() - t0) / 1e6, acc, rej

def run_scenario(name, n_veh, total_msgs, attacks, rate, seed=7):
    CERT_CACHE.clear()
    ca = oqs.Signature(ALG); pk_CA = ca.generate_keypair()
    vehicles = [Vehicle(ca) for _ in range(n_veh)]
    duration = total_msgs / (n_veh * rate) * 1000.0
    arr = sorted(np.random.default_rng(seed).uniform(0, duration, total_msgs))
    atk_idx = set(np.random.default_rng(seed + 1000).choice(total_msgs, attacks, replace=False)) if attacks else set()
    e2e, waits, procs, t_counts = [], [], [], []
    acc = rej = 0
    with oqs.Signature(ALG) as verifier:
        i = 0
        w_end = W
        while i < len(arr):
            batch, batch_arr = [], []
            while i < len(arr) and arr[i] <= w_end:
                v = vehicles[i % n_veh]
                batch.append(v.make_tuple(attack=(i in atk_idx)))
                batch_arr.append(arr[i]); i += 1
            if batch:
                pw = process_window_digest if ARGS.digest else process_window
                p_ms, a, r = pw(batch, pk_CA, verifier)
                acc += a; rej += r
                t_counts.append(len(batch)); procs.append(p_ms)
                for am in batch_arr:
                    waits.append(w_end - am)
                    e2e.append((w_end - am) + p_ms)
            w_end += W
    return {"scenario": name, "vehicles": n_veh, "messages": total_msgs,
            "attacks": attacks, "t_avg": round(statistics.mean(t_counts), 1),
            "wait_mean_ms": round(statistics.mean(waits), 1),
            "proc_mean_ms": round(statistics.mean(procs), 2),
            "e2e_mean_ms": round(statistics.mean(e2e), 1),
            "e2e_p95_ms": round(float(np.percentile(e2e, 95)), 1),
            "deadline_misses": sum(1 for x in e2e if x > DEADLINE),
            "under_100ms_pct": round(100 * sum(1 for x in e2e if x <= DEADLINE) / len(e2e), 2),
            "accepted": acc, "rejected": rej}

def aggregate_seeds(rows):
    e2e=[r["e2e_mean_ms"] for r in rows]; miss=sum(r["deadline_misses"] for r in rows)
    n=sum(r["messages"] for r in rows)
    return {"scenario": rows[0]["scenario"], "seeds": len(rows),
            "messages_total": n,
            "e2e_mean_ms": round(statistics.mean(e2e),1),
            "e2e_mean_ci95": round(mean_ci95(e2e)[1],2) if len(rows)>1 else None,
            "proc_mean_ms": round(statistics.mean([r["proc_mean_ms"] for r in rows]),2),
            "deadline_misses": miss,
            "miss_rate_pct": round(100*miss/n,3)}

def main():
    # rate (msg/s/vehicle) dikalibrasi agar t_avg per window cocok dengan Tabel VII
    scenarios = [
        ("highway-n20",        20, 1586,   0,  9.00),   # t ~ 18
        ("highway-n20-attack", 20, 1865, 200,  9.00),   # t ~ 18 (+serangan)
        ("urban-n30",          30, 2210,   0,  7.33),   # t ~ 22
        ("intersection-n15",   15, 1478,   0, 16.67),   # t ~ 25 (dense)
    ]
    mode = "digest" if ARGS.digest else "full"
    out = {"window_ms": W, "mode": mode, "seeds": ARGS.seeds, "alg": ALG,
           "per_seed": [], "summary": []}
    for sc in scenarios:
        rows = []
        for k in range(ARGS.seeds):
            r = run_scenario(*sc, seed=7 + 97 * k)
            rows.append(r); out["per_seed"].append(r)
        summ = aggregate_seeds(rows)
        out["summary"].append(summ)
        print(json.dumps(summ))
    fn = f"e2e_results_W{int(W)}_{mode}.json"
    json.dump(out, open(fn, "w"), indent=1)
    print(f"\nSaved {fn} (W = {W} ms, mode = {mode}, seeds = {ARGS.seeds})")

if __name__ == "__main__":
    main()
