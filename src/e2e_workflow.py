#!/usr/bin/env python3
"""Transport-excluded authentication-pipeline workflow for PQ-CBAS-DSH.

Model
-----
- Messages arrive uniformly in time at ``rate`` msg/s per vehicle.
- The RSU closes a collection window every W ms; tuples in the window are
  processed as one verification batch.
- Per-message pipeline latency = virtual window waiting time + measured
  verifier processing time. Wireless transport, contention, queueing, packet
  loss, and fragmentation are deliberately excluded.
- Full-certificate mode validates the CA certificate on every message.
- Certificate-digest mode models the manuscript protocol explicitly: the first
  valid message for a vehicle is an attach record carrying the full certificate;
  subsequent messages carry only CertID = H_cert(Cert). The verifier resolves
  CertID through a cache populated only after successful CertValidate.
- Attack records carry a forged certificate and are rejected at CertValidate.

Usage:
  OQS_INSTALL_PATH=~/oqs python3 src/e2e_workflow.py --window 90 --seeds 20
  OQS_INSTALL_PATH=~/oqs python3 src/e2e_workflow.py --window 90 --seeds 20 --digest
"""

import argparse
import hashlib
import json
import secrets
import statistics
import time

import numpy as np
import oqs

from ci_stats import mean_ci95

ALG = "ML-DSA-65"
H_CERT = b"PQ-CBAS-DSH/CERT"
H_SIGN = b"PQ-CBAS-DSH/SIGN"
DEADLINE = 100.0
KAPPA = 48

ap = argparse.ArgumentParser()
ap.add_argument("--window", type=float, default=100.0, help="collection window W (ms)")
ap.add_argument("--seeds", type=int, default=1, help="number of independent seeds")
ap.add_argument(
    "--digest",
    action="store_true",
    help=(
        "certificate-digest mode: first valid message carries the full certificate; "
        "subsequent messages carry CertID and resolve a validated certificate cache"
    ),
)
ARGS = ap.parse_args()
W = ARGS.window


def xof(domain: bytes, data: bytes, n: int = KAPPA) -> bytes:
    return hashlib.shake_256(domain + data).digest(n)


def cert_bytes(cert) -> bytes:
    return cert[0] + cert[1] + cert[2]


class Vehicle:
    def __init__(self, ca):
        self.s = oqs.Signature(ALG)
        self.pk = self.s.generate_keypair()
        self.ID = secrets.token_bytes(16)
        mu = xof(H_CERT, self.ID + self.pk + b"ctx_cert")
        self.cert = (self.ID, self.pk, ca.sign(mu))
        self.cert_id = xof(H_CERT, cert_bytes(self.cert))

    def _valid_message(self):
        m = secrets.token_bytes(100)
        fr = secrets.token_bytes(8)
        mu = xof(
            H_SIGN,
            self.ID + m + self.pk + self.cert[0] + self.cert[1] + self.cert[2] + fr,
        )
        sig = self.s.sign(mu)
        return m, fr, sig

    def make_full_tuple(self, attack=False):
        m, fr, sig = self._valid_message()
        cert = self.cert
        if attack:
            cert = (self.ID, self.pk, secrets.token_bytes(len(self.cert[2])))
            sig = secrets.token_bytes(3309)
        return self.ID, m, self.pk, cert, sig, fr

    def make_attach_record(self, attack=False):
        """Full-certificate first attach used to populate the digest cache."""
        ID, m, pk, cert, sig, fr = self.make_full_tuple(attack=attack)
        cid = xof(H_CERT, cert_bytes(cert))
        return {
            "kind": "attach",
            "ID": ID,
            "m": m,
            "pk": pk,
            "cert": cert,
            "cid": cid,
            "sig": sig,
            "fresh": fr,
        }

    def make_digest_record(self):
        """Steady-state record: no public key or certificate is transmitted."""
        m, fr, sig = self._valid_message()
        return {
            "kind": "digest",
            "ID": self.ID,
            "m": m,
            "cid": self.cert_id,
            "sig": sig,
            "fresh": fr,
        }


CERT_CACHE = {}  # CertID -> (pk, cert)


def process_window_digest(records, pk_CA, verifier):
    """Validate first attach once, then resolve steady-state CertID records."""
    t0 = time.perf_counter_ns()
    acc = rej = 0

    for rec in records:
        kind = rec["kind"]
        ID = rec["ID"]
        m = rec["m"]
        sig = rec["sig"]
        fr = rec["fresh"]

        if kind == "attach":
            pk = rec["pk"]
            cert = rec["cert"]
            cid = rec["cid"]

            # Tuple consistency and digest binding before cache insertion.
            if cert[0] != ID or cert[1] != pk or xof(H_CERT, cert_bytes(cert)) != cid:
                rej += 1
                continue

            mu_c = xof(H_CERT, cert[0] + cert[1] + b"ctx_cert")
            if not verifier.verify(mu_c, cert[2], pk_CA):
                rej += 1
                continue
            CERT_CACHE[cid] = (pk, cert)

        elif kind == "digest":
            cid = rec["cid"]
            cached = CERT_CACHE.get(cid)
            if cached is None:
                # A digest record is not accepted before a validated attach.
                rej += 1
                continue
            pk, cert = cached
            if cert[0] != ID:
                rej += 1
                continue
        else:
            rej += 1
            continue

        mu_s = xof(H_SIGN, ID + m + pk + cert[0] + cert[1] + cert[2] + fr)
        if verifier.verify(mu_s, sig, pk):
            acc += 1
        else:
            rej += 1

    return (time.perf_counter_ns() - t0) / 1e6, acc, rej


def process_window(tuples, pk_CA, verifier):
    """Full-certificate verifier path. Returns elapsed_ms, accepted, rejected."""
    t0 = time.perf_counter_ns()
    acc = rej = 0
    for ID, m, pk, cert, sig, fr in tuples:
        if cert[0] != ID or cert[1] != pk:
            rej += 1
            continue
        mu_c = xof(H_CERT, cert[0] + cert[1] + b"ctx_cert")
        if not verifier.verify(mu_c, cert[2], pk_CA):
            rej += 1
            continue
        mu_s = xof(H_SIGN, ID + m + pk + cert[0] + cert[1] + cert[2] + fr)
        if verifier.verify(mu_s, sig, pk):
            acc += 1
        else:
            rej += 1
    return (time.perf_counter_ns() - t0) / 1e6, acc, rej


def run_scenario(name, n_veh, total_msgs, attacks, rate, seed=7):
    CERT_CACHE.clear()
    ca = oqs.Signature(ALG)
    pk_CA = ca.generate_keypair()
    vehicles = [Vehicle(ca) for _ in range(n_veh)]

    duration = total_msgs / (n_veh * rate) * 1000.0
    arr = sorted(np.random.default_rng(seed).uniform(0, duration, total_msgs))
    atk_idx = (
        set(np.random.default_rng(seed + 1000).choice(total_msgs, attacks, replace=False))
        if attacks
        else set()
    )

    e2e, waits, procs, t_counts = [], [], [], []
    acc = rej = 0
    attached = set()

    with oqs.Signature(ALG) as verifier:
        i = 0
        w_end = W
        while i < len(arr):
            batch, batch_arr = [], []
            while i < len(arr) and arr[i] <= w_end:
                v = vehicles[i % n_veh]
                attack = i in atk_idx

                if ARGS.digest:
                    if attack:
                        # Preserve the forged-certificate early-rejection experiment.
                        rec = v.make_attach_record(attack=True)
                    elif v.ID not in attached:
                        rec = v.make_attach_record(attack=False)
                        attached.add(v.ID)
                    else:
                        rec = v.make_digest_record()
                    batch.append(rec)
                else:
                    batch.append(v.make_full_tuple(attack=attack))

                batch_arr.append(arr[i])
                i += 1

            if batch:
                pw = process_window_digest if ARGS.digest else process_window
                p_ms, a, r = pw(batch, pk_CA, verifier)
                acc += a
                rej += r
                t_counts.append(len(batch))
                procs.append(p_ms)
                for am in batch_arr:
                    waits.append(w_end - am)
                    e2e.append((w_end - am) + p_ms)
            w_end += W

    return {
        "scenario": name,
        "vehicles": n_veh,
        "messages": total_msgs,
        "attacks": attacks,
        "t_avg": round(statistics.mean(t_counts), 1),
        "wait_mean_ms": round(statistics.mean(waits), 1),
        "proc_mean_ms": round(statistics.mean(procs), 2),
        "e2e_mean_ms": round(statistics.mean(e2e), 1),
        "e2e_p95_ms": round(float(np.percentile(e2e, 95)), 1),
        "deadline_misses": sum(1 for x in e2e if x > DEADLINE),
        "under_100ms_pct": round(100 * sum(1 for x in e2e if x <= DEADLINE) / len(e2e), 2),
        "accepted": acc,
        "rejected": rej,
    }


def aggregate_seeds(rows):
    e2e = [r["e2e_mean_ms"] for r in rows]
    miss = sum(r["deadline_misses"] for r in rows)
    n = sum(r["messages"] for r in rows)
    return {
        "scenario": rows[0]["scenario"],
        "seeds": len(rows),
        "messages_total": n,
        "e2e_mean_ms": round(statistics.mean(e2e), 1),
        "e2e_mean_ci95": round(mean_ci95(e2e)[1], 2) if len(rows) > 1 else None,
        "proc_mean_ms": round(statistics.mean([r["proc_mean_ms"] for r in rows]), 2),
        "deadline_misses": miss,
        "miss_rate_pct": round(100 * miss / n, 3),
    }


def main():
    # Rates calibrated so mean tuples/window match the manuscript scenarios.
    scenarios = [
        ("highway-n20", 20, 1586, 0, 9.00),
        ("highway-n20-attack", 20, 1865, 200, 9.00),
        ("urban-n30", 30, 2210, 0, 7.33),
        ("intersection-n15", 15, 1478, 0, 16.67),
    ]
    mode = "digest" if ARGS.digest else "full"
    out = {
        "window_ms": W,
        "mode": mode,
        "digest_model": "first-attach-full-then-certid" if ARGS.digest else None,
        "transport_included": False,
        "seeds": ARGS.seeds,
        "alg": ALG,
        "per_seed": [],
        "summary": [],
    }

    for sc in scenarios:
        rows = []
        for k in range(ARGS.seeds):
            r = run_scenario(*sc, seed=7 + 97 * k)
            rows.append(r)
            out["per_seed"].append(r)
        summ = aggregate_seeds(rows)
        out["summary"].append(summ)
        print(json.dumps(summ))

    fn = f"e2e_results_W{int(W)}_{mode}.json"
    with open(fn, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nSaved {fn} (W = {W} ms, mode = {mode}, seeds = {ARGS.seeds})")


if __name__ == "__main__":
    main()
