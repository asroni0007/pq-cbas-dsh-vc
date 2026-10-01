#!/usr/bin/env python3
"""
sumo_pqcbas_bridge.py — SUMO FCD adapter for PQ-CBAS-DSH

Workflow:
  1. Run SUMO headless (subprocess) → studyarea_fcd.xml
  2. Parse FCD → per-vehicle RSU entry/exit times (real mobility trace)
  3. Feed the mobility-derived arrival schedule to the PQ-CBAS-DSH verifier
     (liboqs ML-DSA-65; certificate-digest cache model optional).
  4. Report transport-excluded authentication-pipeline latency, deadline-miss
     rate, and verifier processing cost.

Usage:
  OQS_INSTALL_PATH=~/oqs python3 sumo_pqcbas_bridge.py \
      --cfg studyarea_test.sumocfg \
      --net StudyAreNetwork.net.xml \
      --rsu-x 80 --rsu-y 36 --R 150 \
      [--digest] [--window 90] [--seeds 3] [--no-sumo] [--fcd existing_fcd.xml]

Dependencies: oqs (liboqs-python), numpy, sumo (in PATH or SUMO_HOME set)
"""
import argparse, hashlib, json, math, os, secrets, statistics, subprocess
from ci_stats import mean_ci95
import sys, tempfile, time, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import oqs

# ------------------------------------------------------------------ constants
ALG = "ML-DSA-65"
H_CERT = b"PQ-CBAS-DSH/CERT"
H_SIGN = b"PQ-CBAS-DSH/SIGN"
H_AGG  = b"PQ-CBAS-DSH/AGG"
DEADLINE_MS = 100.0
KAPPA = 48

def xof(domain, data, n=KAPPA):
    return hashlib.shake_256(domain + data).digest(n)

# ------------------------------------------------------------------ SUMO runner
def run_sumo(cfg_path: str, fcd_out: str, sumo_binary: str = "sumo") -> bool:
    """Run SUMO headless, write FCD to fcd_out. Return True on success."""
    # find sumo binary
    sumo = sumo_binary
    if not sumo or not Path(sumo).is_file():
        for candidate in [sumo_binary, "sumo", "sumo-gui"]:
            import shutil
            found = shutil.which(candidate)
            if found:
                sumo = found; break
        else:
            print("[WARN] SUMO binary not found — use --no-sumo and provide --fcd",
                  file=sys.stderr)
            return False
    cmd = [sumo, "-c", cfg_path,
           "--fcd-output", fcd_out,
           "--no-warnings", "true",
           "--duration-log.disable", "true",
           "--log", os.devnull]
    print(f"[SUMO] Running: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        if r.returncode != 0:
            print(f"[SUMO] stderr: {r.stderr.decode()[:400]}", file=sys.stderr)
            return False
        print(f"[SUMO] Done → {fcd_out}")
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[SUMO] Error: {e}", file=sys.stderr)
        return False

# ------------------------------------------------------------------ FCD parser
def parse_fcd_arrivals(fcd_path: str, rsu_x: float, rsu_y: float, R: float,
                       step_ms: float = 1000.0):
    """
    Parse SUMO FCD XML and extract per-vehicle RSU contact windows.

    Returns list of (arrival_ms, vehicle_id) sorted by arrival time,
    representing the moment each vehicle enters RSU coverage.
    Also returns dict of vehicle_id -> contact_duration_ms.
    """
    R2 = R * R
    in_coverage = {}   # vid -> first_entry_ms
    contact_dur = {}   # vid -> total ms in coverage
    arrivals = []      # (entry_ms, vid)

    print(f"[FCD] Parsing {fcd_path} (RSU R={R}m at ({rsu_x},{rsu_y}))...")
    step_idx = 0
    for event, elem in ET.iterparse(fcd_path, events=("end",)):
        if elem.tag == "timestep":
            t_s = float(elem.get("time", 0))
            t_ms = t_s * 1000.0
            for veh in elem.findall("vehicle"):
                vid = veh.get("id")
                x   = float(veh.get("x", 0))
                y   = float(veh.get("y", 0))
                inside = (x - rsu_x)**2 + (y - rsu_y)**2 <= R2
                if inside:
                    if vid not in in_coverage:
                        in_coverage[vid] = t_ms
                        arrivals.append((t_ms, vid))
                    contact_dur[vid] = contact_dur.get(vid, 0) + step_ms
                else:
                    in_coverage.pop(vid, None)
            elem.clear()
            step_idx += 1

    arrivals.sort()
    print(f"[FCD] Unique vehicles entering RSU: {len(arrivals)}")
    if contact_dur:
        durs = list(contact_dur.values())
        print(f"[FCD] Contact duration: mean={statistics.mean(durs)/1000:.1f}s "
              f"min={min(durs)/1000:.1f}s max={max(durs)/1000:.1f}s")
    return arrivals, contact_dur

# ------------------------------------------------------------------ crypto harness
class CA:
    def __init__(self):
        self.signer = oqs.Signature(ALG)
        self.pk = self.signer.generate_keypair()

def cert_bytes(cert):
    return cert[0] + cert[1] + cert[2]


class OBU:
    def __init__(self, ca: CA):
        self.signer = oqs.Signature(ALG)
        self.pk = self.signer.generate_keypair()
        self.ID = secrets.token_bytes(16)
        mu = xof(H_CERT, self.ID + self.pk + b"ctx_cert")
        gamma = ca.signer.sign(mu)
        self.cert = (self.ID, self.pk, gamma)
        self.cert_id = xof(H_CERT, cert_bytes(self.cert))

    def _signed_fields(self):
        m = secrets.token_bytes(100)
        fr = secrets.token_bytes(8)
        mu = xof(
            H_SIGN,
            self.ID + m + self.pk + self.cert[0] + self.cert[1] + self.cert[2] + fr,
        )
        return m, fr, self.signer.sign(mu)

    def full_record(self):
        m, fr, sig = self._signed_fields()
        return {
            "kind": "full", "ID": self.ID, "m": m, "pk": self.pk,
            "cert": self.cert, "cid": self.cert_id, "sig": sig, "fresh": fr,
        }

    def digest_record(self):
        m, fr, sig = self._signed_fields()
        return {
            "kind": "digest", "ID": self.ID, "m": m, "cid": self.cert_id,
            "sig": sig, "fresh": fr,
        }


CERT_CACHE = {}  # CertID -> (pk, cert)


def verify_window(records, pk_ca, verifier, digest_mode=False):
    """Timed verifier path. Digest records resolve only from a validated cache."""
    t0 = time.perf_counter_ns()
    acc = rej = 0

    for rec in records:
        ID, m, sig, fr = rec["ID"], rec["m"], rec["sig"], rec["fresh"]

        if digest_mode and rec["kind"] == "digest":
            cached = CERT_CACHE.get(rec["cid"])
            if cached is None:
                rej += 1
                continue
            pk, cert = cached
            if cert[0] != ID:
                rej += 1
                continue
        else:
            pk, cert = rec["pk"], rec["cert"]
            if cert[0] != ID or cert[1] != pk:
                rej += 1
                continue
            cid = xof(H_CERT, cert_bytes(cert))
            if cid != rec["cid"]:
                rej += 1
                continue
            mu_c = xof(H_CERT, cert[0] + cert[1] + b"ctx_cert")
            if not verifier.verify(mu_c, cert[2], pk_ca):
                rej += 1
                continue
            if digest_mode:
                CERT_CACHE[cid] = (pk, cert)

        mu_s = xof(H_SIGN, ID + m + pk + cert[0] + cert[1] + cert[2] + fr)
        if verifier.verify(mu_s, sig, pk):
            acc += 1
        else:
            rej += 1

    return (time.perf_counter_ns() - t0) / 1e6, acc, rej

# ------------------------------------------------------------------ main simulation
def simulate(arrivals, contact_dur, ca, obus, W_ms, digest_mode, seed, digest_cache_model="warm"):
    """
    Simulate RSU collection windows over the SUMO mobility trace.

    Each FCD vehicle entry contributes one measured authenticated message.
    Windows close every W_ms and all records in the window are batch-verified.
    In digest/warm mode this measured message represents steady state after a
    previously validated first attach; digest/cold measures the attach record.
    """
    CERT_CACHE.clear()
    rng = np.random.default_rng(seed)

    # The SUMO workload schedules one measured message per FCD vehicle entry.
    # In digest mode the default "warm" setting models the steady-state message
    # after a previously validated first attach; the attach itself is outside the
    # timed window.  "cold" instead sends a full-certificate attach record.
    if digest_mode and digest_cache_model == "warm":
        for obu in obus:
            CERT_CACHE[obu.cert_id] = (obu.pk, obu.cert)

    # Build message schedule: one measured message per vehicle entry, jitter ±10ms
    schedule = []
    obu_pool = {i: obus[i % len(obus)] for i in range(len(arrivals))}
    for idx, (t_ms, vid) in enumerate(arrivals):
        jitter = rng.uniform(-10, 10)
        schedule.append((max(0, t_ms + jitter), idx))
    schedule.sort()

    if not schedule:
        return None

    pk_ca = ca.pk
    e2e_latencies = []
    deadline_misses = 0
    window_procs = []
    accepted_total = rejected_total = 0

    with oqs.Signature(ALG) as verifier:
        w_end = W_ms
        i = 0
        while i < len(schedule):
            batch, batch_arr = [], []
            while i < len(schedule) and schedule[i][0] <= w_end:
                t_arr, idx = schedule[i]
                obu = obu_pool[idx]
                if digest_mode and digest_cache_model == "warm":
                    batch.append(obu.digest_record())
                else:
                    batch.append(obu.full_record())
                batch_arr.append(t_arr)
                i += 1
            if batch:
                proc_ms, acc, rej = verify_window(
                    batch, pk_ca, verifier, digest_mode)
                accepted_total += acc; rejected_total += rej
                window_procs.append(proc_ms)
                for t_arr in batch_arr:
                    e2e = (w_end - t_arr) + proc_ms
                    e2e_latencies.append(e2e)
                    if e2e > DEADLINE_MS:
                        deadline_misses += 1
            w_end += W_ms

    if not e2e_latencies:
        return None

    sim_dur_s = max(t for t,_ in arrivals) / 1000.0
    return {
        "messages": len(e2e_latencies),
        "accepted": accepted_total,
        "rejected": rejected_total,
        "e2e_mean_ms": round(statistics.mean(e2e_latencies), 1),
        "e2e_p95_ms":  round(float(np.percentile(e2e_latencies, 95)), 1),
        "proc_mean_ms": round(statistics.mean(window_procs), 2) if window_procs else 0,
        "deadline_misses": deadline_misses,
        "miss_rate_pct": round(100 * deadline_misses / len(e2e_latencies), 3),
        "sim_duration_s": round(sim_dur_s, 0),
        "vehicles_in_rsu": len(arrivals),
        "windows": len(window_procs),
        "digest_cache_model": digest_cache_model if digest_mode else None,
    }

# ------------------------------------------------------------------ entry point
def main():
    ap = argparse.ArgumentParser(description="SUMO × PQ-CBAS-DSH bridge")
    ap.add_argument("--cfg",   default="studyarea_test.sumocfg")
    ap.add_argument("--net",   default="StudyAreNetwork.net.xml")
    ap.add_argument("--fcd",   default="studyarea_fcd.xml", help="FCD output file")
    ap.add_argument("--rsu-x", type=float, default=80.0)
    ap.add_argument("--rsu-y", type=float, default=36.0)
    ap.add_argument("--R",     type=float, default=150.0)
    ap.add_argument("--window",type=float, default=90.0,  help="collection window W (ms)")
    ap.add_argument("--seeds", type=int,   default=3,     help="crypto seeds to average")
    ap.add_argument("--digest",action="store_true", help="certificate-digest mode")
    ap.add_argument(
        "--digest-cache-model", choices=("warm", "cold"), default="warm",
        help=("digest-mode cache assumption: warm = steady-state CertID message after "
              "prevalidated attach; cold = measured message carries full certificate"),
    )
    ap.add_argument("--no-sumo",action="store_true", help="skip SUMO run, use existing FCD")
    ap.add_argument("--sumo-binary", default="sumo")
    ap.add_argument(
        "--n-obus", type=int, default=0,
        help="crypto identity pool size; 0 = one unique OBU identity per FCD vehicle (paper default)",
    )
    args = ap.parse_args()

    mode = "digest" if args.digest else "full"
    print(f"\n=== PQ-CBAS-DSH SUMO Bridge ===")
    print(f"RSU: ({args.rsu_x},{args.rsu_y}) R={args.R}m  W={args.window}ms  mode={mode}  seeds={args.seeds}")

    # Step 1: run or load FCD
    if not args.no_sumo:
        ok = run_sumo(args.cfg, args.fcd, args.sumo_binary)
        if not ok:
            print("[INFO] Falling back to existing FCD (if available)")

    if not Path(args.fcd).exists():
        sys.exit(f"[ERROR] FCD file not found: {args.fcd}  (run SUMO first or use --no-sumo)")

    # Step 2: parse mobility trace
    arrivals, contact_dur = parse_fcd_arrivals(
        args.fcd, args.rsu_x, args.rsu_y, args.R)

    if not arrivals:
        sys.exit("[ERROR] No vehicles entered RSU coverage — check geometry/demand")

    # Print contact stats for Table VII annotation
    durs_s = [v/1000 for v in contact_dur.values()]
    print(f"\n[MOBILITY] Vehicles in RSU coverage: {len(arrivals)}")
    print(f"[MOBILITY] Contact time: mean={statistics.mean(durs_s):.1f}s "
          f"p5={np.percentile(durs_s,5):.1f}s p95={np.percentile(durs_s,95):.1f}s")

    # Step 3: set up crypto
    n_obus = args.n_obus if args.n_obus > 0 else len(arrivals)
    print(f"\n[CRYPTO] Setting up CA + {n_obus} OBUs (ML-DSA-65)...")
    t0 = time.perf_counter()
    ca = CA()
    obus = [OBU(ca) for _ in range(n_obus)]
    print(f"[CRYPTO] Setup done in {time.perf_counter()-t0:.1f}s")

    # Step 4: simulate over seeds
    results = []
    for k in range(args.seeds):
        seed = 7 + 97 * k
        print(f"\n[SIM] Seed {k+1}/{args.seeds} ...", end=" ", flush=True)
        r = simulate(
            arrivals, contact_dur, ca, obus, args.window, args.digest, seed,
            digest_cache_model=args.digest_cache_model,
        )
        if r:
            results.append(r)
            print(f"E2E={r['e2e_mean_ms']}ms  miss={r['deadline_misses']}/{r['messages']}")

    if not results:
        sys.exit("[ERROR] No simulation results")

    # Step 5: aggregate
    e2e_means = [r["e2e_mean_ms"] for r in results]
    n_total = sum(r["messages"] for r in results)
    miss_total = sum(r["deadline_misses"] for r in results)
    ci95 = mean_ci95(e2e_means)[1] if len(e2e_means) > 1 else None

    summary = {
        "source": "SUMO FCD trace",
        "fcd_file": args.fcd,
        "rsu": {"x": args.rsu_x, "y": args.rsu_y, "R": args.R},
        "window_ms": args.window,
        "mode": mode,
        "digest_cache_model": args.digest_cache_model if args.digest else None,
        "transport_included": False,
        "crypto_identities": n_obus,
        "seeds": args.seeds,
        "alg": ALG,
        "vehicles_in_rsu": len(arrivals),
        "contact_mean_s": round(statistics.mean(durs_s), 1),
        "messages_total": n_total,
        "e2e_mean_ms": round(statistics.mean(e2e_means), 1),
        "e2e_mean_ci95": round(ci95, 2) if ci95 else None,
        "e2e_p95_ms": round(statistics.mean([r["e2e_p95_ms"] for r in results]), 1),
        "proc_mean_ms": round(statistics.mean([r["proc_mean_ms"] for r in results]), 2),
        "deadline_misses": miss_total,
        "miss_rate_pct": round(100 * miss_total / n_total, 3),
        "per_seed": results,
    }

    out_fn = f"sumo_pqcbas_W{int(args.window)}_{mode}.json"
    json.dump(summary, open(out_fn, "w"), indent=1)

    print(f"\n{'='*55}")
    print(f"SUMO × PQ-CBAS-DSH Result (W={args.window}ms, mode={mode})")
    print(f"{'='*55}")
    print(f"  Vehicles entering RSU :  {len(arrivals)}")
    print(f"  Messages processed    :  {n_total}  ({args.seeds} seeds)")
    print(f"  E2E mean latency      :  {summary['e2e_mean_ms']} ms", end="")
    if ci95: print(f"  ±{ci95:.2f} ms (CI₉₅)")
    else: print()
    print(f"  E2E p95               :  {summary['e2e_p95_ms']} ms")
    print(f"  Batch processing mean :  {summary['proc_mean_ms']} ms")
    print(f"  Deadline misses       :  {miss_total}/{n_total}  ({summary['miss_rate_pct']:.3f}%)")
    print(f"  Saved → {out_fn}")
    return summary

if __name__ == "__main__":
    main()
