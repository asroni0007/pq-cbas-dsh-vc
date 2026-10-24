#!/usr/bin/env python3
"""Additional CA/CS measurements for PQ-CBAS-DSH on the Apple M2 host.

Purpose: close four limitations that the manuscript states for the M2 results.
  A. Host state: power source, thermal state, low-power mode before and after.
  B. ECDSA-P256 vs ML-DSA-65 verification, repeated in interleaved sessions with
     four ML-DSA variants that separate Python/binding overhead from the core call.
  C. Real (measured) parallel CertValidate with threads and processes, replacing the
     modelled 2x / 4x columns of the batch table.
  D. Sustained CertGen (CA role) throughput and tail latency, with and without the
     Python garbage collector, to test whether rare outliers come from the runtime.

Run (macOS, on AC power, Low Power Mode off):
    caffeinate -i python3 m2_ca_cs_extra.py --out m2_extra_out
Smoke test (about 1 minute):
    python3 m2_ca_cs_extra.py --quick --out m2_extra_smoke

Reads nothing outside its own output directory; writes results.json, summary.txt.
Uses the same libraries as the paper: liboqs-python and cryptography.
"""
import argparse
import concurrent.futures as cf
import gc
import hashlib
import json
import multiprocessing as mp
import os
import platform
import random
import secrets
import statistics
import subprocess
import sys
import time

import oqs

ALG = "ML-DSA-65"
H_CERT = b"PQ-CBAS-DSH/CERT"
KAPPA = 48

T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
        14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
        20: 2.086, 24: 2.064, 29: 2.045}


def tcrit(df):
    if df in T975:
        return T975[df]
    keys = sorted(T975)
    for k in keys:
        if k >= df:
            return T975[k]
    return 1.96


def mean_ci(xs):
    n = len(xs)
    m = statistics.mean(xs)
    if n < 2:
        return m, 0.0, float("nan"), float("nan")
    sd = statistics.stdev(xs)
    h = tcrit(n - 1) * sd / n ** 0.5
    return m, sd, m - h, m + h


def pct(xs, p):
    ys = sorted(xs)
    k = min(len(ys) - 1, max(0, int(round(p / 100.0 * (len(ys) - 1)))))
    return ys[k]


def xof(domain, data):
    return hashlib.shake_256(domain + data).digest(KAPPA)


def sh(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return "unavailable: %s" % type(e).__name__


def host_state(tag):
    st = {"tag": tag, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    if platform.system() == "Darwin":
        st["pmset_batt"] = sh(["pmset", "-g", "batt"])
        st["pmset_therm"] = sh(["pmset", "-g", "therm"])
        st["pmset_lowpower"] = [ln.strip() for ln in sh(["pmset", "-g"]).splitlines()
                                if "lowpowermode" in ln.lower()]
    else:
        st["note"] = "not macOS; pmset not available"
    return st


def env_info():
    e = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "liboqs": oqs.oqs_version(),
        "liboqs_python": oqs.oqs_python_version(),
        "cpu_count": os.cpu_count(),
    }
    try:
        import cryptography
        e["cryptography"] = cryptography.__version__
    except Exception:  # noqa: BLE001
        e["cryptography"] = None
    if platform.system() == "Darwin":
        for key in ("machdep.cpu.brand_string", "hw.ncpu", "hw.perflevel0.physicalcpu",
                    "hw.perflevel1.physicalcpu", "hw.memsize"):
            e[key] = sh(["sysctl", "-n", key])
        e["macos"] = sh(["sw_vers", "-productVersion"])
    return e


# ---------------------------------------------------------------- Section B
def make_fixture():
    ca = oqs.Signature(ALG)
    pk_ca = ca.generate_keypair()
    veh = oqs.Signature(ALG)
    pk = veh.generate_keypair()
    ID = b"VEH-0001"
    mu = xof(H_CERT, ID + pk + b"ctx_cert")
    gamma = ca.sign(mu)
    return ca, pk_ca, ID, pk, gamma


def run_section_b(sessions, reps, rng):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    ca, pk_ca, ID, pk, gamma = make_fixture()
    reuse = oqs.Signature(ALG)
    mu = xof(H_CERT, ID + pk + b"ctx_cert")
    esk = ec.generate_private_key(ec.SECP256R1())
    epk = esk.public_key()
    emsg = b"x" * 100
    esig = esk.sign(emsg, ec.ECDSA(hashes.SHA256()))

    def v_asbench():
        m = xof(H_CERT, ID + pk + b"ctx_cert")
        with oqs.Signature(ALG) as v:
            return v.verify(m, gamma, pk_ca)

    def v_reuse_hash():
        m = xof(H_CERT, ID + pk + b"ctx_cert")
        return reuse.verify(m, gamma, pk_ca)

    def v_reuse_nohash():
        return reuse.verify(mu, gamma, pk_ca)

    def v_hash_only():
        return xof(H_CERT, ID + pk + b"ctx_cert")

    def v_ecdsa():
        return epk.verify(esig, emsg, ec.ECDSA(hashes.SHA256()))

    def v_noop():
        return None

    variants = {
        "mldsa_certvalidate_as_in_paper": v_asbench,
        "mldsa_verify_reused_verifier_with_hash": v_reuse_hash,
        "mldsa_verify_reused_verifier_core_only": v_reuse_nohash,
        "shake256_hash_only": v_hash_only,
        "ecdsa_p256_verify_as_in_paper": v_ecdsa,
        "empty_python_call": v_noop,
    }
    names = list(variants)
    for f in variants.values():  # warm-up
        for _ in range(200):
            f()
    per = {n: [] for n in names}      # per-session mean (ms)
    allx = {n: [] for n in names}     # all samples (ms)
    for _ in range(sessions):
        order = names[:]
        rng.shuffle(order)
        for n in order:
            f = variants[n]
            xs = []
            for _ in range(reps):
                t0 = time.perf_counter_ns()
                f()
                xs.append((time.perf_counter_ns() - t0) / 1e6)
            per[n].append(statistics.mean(xs))
            allx[n].extend(xs)
    out = {"sessions": sessions, "reps_per_session": reps, "variants": {}}
    for n in names:
        m, sd, lo, hi = mean_ci(per[n])
        xs = allx[n]
        out["variants"][n] = {
            "session_mean_ms": m, "between_session_sd_ms": sd,
            "ci95_lo_ms": lo, "ci95_hi_ms": hi,
            "pooled_sd_ms": statistics.stdev(xs),
            "pooled_cv_pct": 100 * statistics.stdev(xs) / statistics.mean(xs),
            "median_ms": statistics.median(xs), "p99_ms": pct(xs, 99),
            "session_means_ms": per[n],
        }
    ratios = {}
    base = "ecdsa_p256_verify_as_in_paper"
    for n in ("mldsa_certvalidate_as_in_paper", "mldsa_verify_reused_verifier_with_hash",
              "mldsa_verify_reused_verifier_core_only"):
        rs = [e / a for e, a in zip(per[base], per[n])]   # >1: ML-DSA faster
        m, sd, lo, hi = mean_ci(rs)
        med = statistics.median(allx[base]) / statistics.median(allx[n])
        ratios[n] = {"ecdsa_over_mldsa_mean_of_session_ratios": m,
                     "ci95_lo": lo, "ci95_hi": hi,
                     "ratio_of_medians": med,
                     "faster_in_sessions": sum(1 for r in rs if r > 1),
                     "sessions": len(rs)}
    out["ratio_ecdsa_over_mldsa"] = ratios
    return out


# ---------------------------------------------------------------- Section C
_W = {}


def _init_worker(pk_ca, certs):
    _W["v"] = oqs.Signature(ALG)
    _W["pk_ca"] = pk_ca
    _W["certs"] = certs


def _validate_list(pk_ca, cert_list):
    v = _W.get("v") or oqs.Signature(ALG)
    ok = True
    for ID, pk, gamma in cert_list:
        mu = xof(H_CERT, ID + pk + b"ctx_cert")
        ok = v.verify(mu, gamma, pk_ca) and ok
    return ok


def _validate_range(lo, hi):
    return _validate_list(_W["pk_ca"], _W["certs"][lo:hi])


def build_certs(ca, n):
    certs = []
    for i in range(n):
        s = oqs.Signature(ALG)
        pk = s.generate_keypair()
        ID = b"VEH-%04d" % i
        mu = xof(H_CERT, ID + pk + b"ctx_cert")
        certs.append((ID, pk, ca.sign(mu)))
    return certs


def chunks(seq, s):
    k, r = divmod(len(seq), s)
    out, i = [], 0
    for j in range(s):
        n = k + (1 if j < r else 0)
        out.append(seq[i:i + n])
        i += n
    return [c for c in out if c]


def run_section_c(tlist, slist, windows, warm):
    ca = oqs.Signature(ALG)
    pk_ca = ca.generate_keypair()
    res = {"windows": windows, "warmup_windows": warm, "cases": []}
    ctx = mp.get_context("spawn")
    for t in tlist:
        certs = build_certs(ca, t)
        seqv = oqs.Signature(ALG)

        def timeit(fn):
            xs = []
            for w in range(windows + warm):
                t0 = time.perf_counter_ns()
                ok = fn()
                dt = (time.perf_counter_ns() - t0) / 1e6
                assert ok
                if w >= warm:
                    xs.append(dt)
            return xs

        base = timeit(lambda: _validate_list_local(seqv, pk_ca, certs))
        bm = statistics.mean(base)
        res["cases"].append({"tuples": t, "mode": "sequential", "s": 1,
                             "mean_ms": bm, "p50_ms": statistics.median(base),
                             "p99_ms": pct(base, 99), "speedup_vs_seq": 1.0,
                             "model_mean_ms": bm})
        for s in slist:
            if s == 1:
                continue
            model = bm / s
            # threads
            with cf.ThreadPoolExecutor(max_workers=s) as ex:
                locals_ = [oqs.Signature(ALG) for _ in range(s)]

                def thr():
                    parts = chunks(certs, s)
                    futs = [ex.submit(_validate_list_local, locals_[i], pk_ca, p)
                            for i, p in enumerate(parts)]
                    return all(f.result() for f in futs)

                xs = timeit(thr)
            res["cases"].append(case_row(t, "threads", s, xs, bm, model))
            # processes, certificates sent with each window
            with ctx.Pool(s, initializer=_init_worker, initargs=(pk_ca, None)) as pool:
                def prc():
                    parts = chunks(certs, s)
                    rs = pool.starmap(_validate_list, [(pk_ca, p) for p in parts])
                    return all(rs)

                xs = timeit(prc)
            res["cases"].append(case_row(t, "processes_send_certs", s, xs, bm, model))
            # processes holding the certificates already (index ranges only)
            with ctx.Pool(s, initializer=_init_worker, initargs=(pk_ca, certs)) as pool:
                bounds, i = [], 0
                for p in chunks(certs, s):
                    bounds.append((i, i + len(p)))
                    i += len(p)

                def prr():
                    return all(pool.starmap(_validate_range, bounds))

                xs = timeit(prr)
            res["cases"].append(case_row(t, "processes_resident_certs", s, xs, bm, model))
    return res


def _validate_list_local(v, pk_ca, cert_list):
    ok = True
    for ID, pk, gamma in cert_list:
        mu = xof(H_CERT, ID + pk + b"ctx_cert")
        ok = v.verify(mu, gamma, pk_ca) and ok
    return ok


def case_row(t, mode, s, xs, bm, model):
    m = statistics.mean(xs)
    return {"tuples": t, "mode": mode, "s": s, "mean_ms": m,
            "p50_ms": statistics.median(xs), "p99_ms": pct(xs, 99),
            "speedup_vs_seq": bm / m, "model_mean_ms": model}


# ---------------------------------------------------------------- Section D
def run_section_d(seconds):
    out = {"seconds_per_pass": seconds, "passes": []}
    ca = oqs.Signature(ALG)
    ca.generate_keypair()
    veh = oqs.Signature(ALG)
    pk = veh.generate_keypair()
    for label, gc_on in (("gc_enabled", True), ("gc_disabled", False)):
        gc.collect()
        if gc_on:
            gc.enable()
        else:
            gc.disable()
        xs, stamps = [], []
        i = 0
        t_end = time.perf_counter() + seconds
        t_start = time.perf_counter()
        while time.perf_counter() < t_end:
            ID = b"VEH-%08d" % i
            t0 = time.perf_counter_ns()
            mu = xof(H_CERT, ID + pk + b"ctx_cert")
            ca.sign(mu)
            dt = (time.perf_counter_ns() - t0) / 1e6
            xs.append(dt)
            stamps.append(round(time.perf_counter() - t_start, 3))
            i += 1
        gc.enable()
        med = statistics.median(xs)
        big = sorted(range(len(xs)), key=lambda k: -xs[k])[:5]
        out["passes"].append({
            "pass": label, "certs_issued": len(xs),
            "throughput_per_s": len(xs) / seconds,
            "mean_ms": statistics.mean(xs), "median_ms": med,
            "p99_ms": pct(xs, 99), "p999_ms": pct(xs, 99.9), "max_ms": max(xs),
            "ops_over_10x_median": sum(1 for x in xs if x > 10 * med),
            "top5_ms": [round(xs[k], 3) for k in big],
            "top5_at_s": [stamps[k] for k in big],
        })
    return out


# ---------------------------------------------------------------- summary
def write_summary(path, r):
    L = []
    L.append("M2 CA/CS EXTRA MEASUREMENTS")
    L.append("=" * 60)
    e = r["env"]
    L.append("host: %s | %s | python %s | liboqs %s | liboqs-python %s | cryptography %s" % (
        e.get("machdep.cpu.brand_string", e["machine"]), e["platform"], e["python"],
        e["liboqs"], e["liboqs_python"], e.get("cryptography")))
    for s in r["host_state"]:
        L.append("[%s] %s" % (s["tag"], s["time"]))
        for k in ("pmset_batt", "pmset_therm", "pmset_lowpower", "note"):
            if k in s:
                L.append("   %s: %s" % (k, s[k]))
    b = r["B"]
    L.append("")
    L.append("B. Verification, %d sessions x %d reps (ms)" % (b["sessions"], b["reps_per_session"]))
    L.append("%-44s %9s %9s %9s %8s" % ("variant", "mean", "ci95_lo", "ci95_hi", "pooledCV%"))
    for n, v in b["variants"].items():
        L.append("%-44s %9.4f %9.4f %9.4f %8.1f" % (
            n, v["session_mean_ms"], v["ci95_lo_ms"], v["ci95_hi_ms"], v["pooled_cv_pct"]))
    L.append("ratio ECDSA/ML-DSA (>1 = ML-DSA faster):")
    for n, v in b["ratio_ecdsa_over_mldsa"].items():
        L.append("  %-42s %.3f  CI95 [%.3f, %.3f]  ratio of medians %.3f  faster in %d/%d sessions" % (
            n, v["ecdsa_over_mldsa_mean_of_session_ratios"], v["ci95_lo"], v["ci95_hi"],
            v["ratio_of_medians"], v["faster_in_sessions"], v["sessions"]))
    c = r["C"]
    L.append("")
    L.append("C. Parallel CertValidate per window, %d windows (ms)" % c["windows"])
    L.append("%6s %-26s %3s %9s %9s %9s %9s" % ("tuples", "mode", "s", "mean", "p99", "speedup", "model"))
    for x in c["cases"]:
        L.append("%6d %-26s %3d %9.4f %9.4f %9.2f %9.4f" % (
            x["tuples"], x["mode"], x["s"], x["mean_ms"], x["p99_ms"],
            x["speedup_vs_seq"], x["model_mean_ms"]))
    d = r["D"]
    L.append("")
    L.append("D. CertGen sustained, %.0f s per pass" % d["seconds_per_pass"])
    for p in d["passes"]:
        L.append("  %-12s n=%d  %.0f/s  mean %.4f  median %.4f  p99 %.4f  p99.9 %.4f  max %.3f ms  >10x median: %d" % (
            p["pass"], p["certs_issued"], p["throughput_per_s"], p["mean_ms"], p["median_ms"],
            p["p99_ms"], p["p999_ms"], p["max_ms"], p["ops_over_10x_median"]))
        L.append("      top5 ms %s at s %s" % (p["top5_ms"], p["top5_at_s"]))
    open(path, "w").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="m2_extra_out")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--sessions", type=int, default=20)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--windows", type=int, default=300)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--procs", default="1,2,4,8")
    ap.add_argument("--tuples", default="16,22")
    a = ap.parse_args()
    if a.quick:
        a.sessions, a.reps, a.windows, a.seconds = 3, 200, 40, 1.0
        a.procs = "1,2"
    os.makedirs(a.out, exist_ok=True)
    rng = random.Random(20261024)
    res = {"env": env_info(), "host_state": [host_state("before")]}
    res["script_sha256"] = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
    t0 = time.time()
    print("B: verification sessions ...", flush=True)
    res["B"] = run_section_b(a.sessions, a.reps, rng)
    res["host_state"].append(host_state("after_B"))
    print("C: parallel CertValidate ...", flush=True)
    res["C"] = run_section_c([int(x) for x in a.tuples.split(",")],
                             [int(x) for x in a.procs.split(",")], a.windows, 20 if not a.quick else 5)
    res["host_state"].append(host_state("after_C"))
    print("D: CertGen throughput ...", flush=True)
    res["D"] = run_section_d(a.seconds)
    res["host_state"].append(host_state("after_D"))
    res["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(a.out, "results.json"), "w"), indent=1)
    write_summary(os.path.join(a.out, "summary.txt"), res)
    print(open(os.path.join(a.out, "summary.txt")).read())
    print("elapsed %.0f s; files in %s" % (res["elapsed_s"], a.out))


if __name__ == "__main__":
    main()
