#!/usr/bin/env python3
"""
Final-profile PQ-CBAS-DSH compute-path experiment.

Measures:
    RSU arrival
      -> certificate pre-check / digest-cache resolution
      -> canonical aggregation
      -> AggCheck / per-signer signature verification
      -> final framework verdict

Wireless transport before RSU arrival and RSU-to-CS backhaul are excluded.

Final profile:
    KAPPA = 384 bit / 48 B
    full wire = 8694 B
    digest wire = 3465 B
"""

import argparse
import json
import platform
import secrets
import statistics
import time

import numpy as np
import oqs

import bench_pqcbas as core
from ci_stats import mean_ci95


ALG = core.ALG
KAPPA = core.KAPPA
H_CERT = core.H_CERT
H_SIGN = core.H_SIGN
H_AGG = core.H_AGG

DEADLINE = 100.0

assert KAPPA == 48, f"Final-profile requires KAPPA=48, got {KAPPA}"


ap = argparse.ArgumentParser()

ap.add_argument(
    "--window",
    type=float,
    default=90.0,
    help="collection window W in ms",
)

ap.add_argument(
    "--seeds",
    type=int,
    default=20,
    help="number of independent arrival seeds",
)

ap.add_argument(
    "--digest",
    action="store_true",
    help="certificate-digest steady-state mode",
)

ARGS = ap.parse_args()
W = ARGS.window


def cert_bytes(cert):
    return cert[0] + cert[1] + cert[2]


class Vehicle:
    def __init__(self, ca):
        self.signer = oqs.Signature(ALG)
        self.pk = self.signer.generate_keypair()
        self.ID = secrets.token_bytes(16)

        mu_cert = core.xof(
            H_CERT,
            self.ID + self.pk + b"ctx_cert"
        )

        self.cert = (
            self.ID,
            self.pk,
            ca.sign(mu_cert),
        )

        self.cert_id = core.xof(
            H_CERT,
            cert_bytes(self.cert),
        )

    def _valid_message(self):
        m = secrets.token_bytes(100)
        fresh = secrets.token_bytes(8)

        mu_sign = core.xof(
            H_SIGN,
            self.ID
            + m
            + self.pk
            + self.cert[0]
            + self.cert[1]
            + self.cert[2]
            + fresh,
        )

        sig = self.signer.sign(mu_sign)

        return m, fresh, sig

    def make_full_tuple(self, attack=False):
        m, fresh, sig = self._valid_message()

        cert = self.cert

        if attack:
            cert = (
                self.ID,
                self.pk,
                secrets.token_bytes(len(self.cert[2])),
            )
            sig = secrets.token_bytes(3309)

        return (
            self.ID,
            m,
            self.pk,
            cert,
            sig,
            fresh,
        )

    def make_attach_record(self, attack=False):
        ID, m, pk, cert, sig, fresh = self.make_full_tuple(
            attack=attack
        )

        cid = core.xof(
            H_CERT,
            cert_bytes(cert),
        )

        return {
            "kind": "attach",
            "m": m,
            "cert": cert,
            "cid": cid,
            "sig": sig,
            "fresh": fresh,
        }

    def make_digest_record(self):
        m, fresh, sig = self._valid_message()

        # Final wire format deliberately carries no outer ID / public key.
        return {
            "kind": "digest",
            "m": m,
            "cid": self.cert_id,
            "sig": sig,
            "fresh": fresh,
        }


CERT_CACHE = {}


def cert_validate_with(verifier, pk_CA, cert):
    ID, pk, gamma = cert

    mu_cert = core.xof(
        H_CERT,
        ID + pk + b"ctx_cert",
    )

    return verifier.verify(
        mu_cert,
        gamma,
        pk_CA,
    )


def aggverify_prevalidated(agg, tuples, verifier):
    """
    Final aggregate verification after certificate pre-check/cache resolution.

    Certificates are not verified a second time.
    Signature validity and all AggCheck consistency conditions are executed.
    """

    try:
        ts, encs = core.canonicalize(tuples)
    except (TypeError, ValueError):
        return False

    tau2 = core.xof(
        H_AGG,
        b"".join(encs),
    )

    if tau2 != agg["tau"]:
        return False

    # AggCheck (i): individual ML-DSA signatures
    for T in ts:
        mu_sign = core.xof(
            H_SIGN,
            T["ID"]
            + T["m"]
            + T["pk"]
            + T["cert"][0]
            + T["cert"][1]
            + T["cert"][2]
            + T["fresh"],
        )

        if not verifier.verify(
            mu_sign,
            T["sigma"],
            T["pk"],
        ):
            return False

    # AggCheck (ii): aggregate response
    bar_z = np.zeros(
        core.L * core.N,
        dtype=np.int64,
    )

    for T in ts:
        bar_z += core.unpack_z(
            T["sigma"]
        )

    if not np.array_equal(
        bar_z,
        agg["bar_z"],
    ):
        return False

    # AggCheck (iii): challenge list
    C2 = b"".join(
        core.c_part(T["sigma"])
        for T in ts
    )

    if C2 != agg["C"]:
        return False

    # AggCheck (iv): hint-anchor
    eta2 = core.xof(
        H_AGG,
        b"".join(
            core.hint_part(T["sigma"])
            for T in ts
        )
        + agg["tau"],
    )

    return eta2 == agg["eta"]


def finish_valid_batch(valid_tuples, verifier):
    if not valid_tuples:
        return 0.0, 0.0, True

    t0 = time.perf_counter_ns()

    agg, ordered = core.aggregate(
        valid_tuples
    )

    agg_ms = (
        time.perf_counter_ns() - t0
    ) / 1e6

    t1 = time.perf_counter_ns()

    ok = aggverify_prevalidated(
        agg,
        ordered,
        verifier,
    )

    verify_ms = (
        time.perf_counter_ns() - t1
    ) / 1e6

    return agg_ms, verify_ms, ok


def process_window_full(
    tuples,
    pk_CA,
    verifier,
):
    total_start = time.perf_counter_ns()

    pre_start = time.perf_counter_ns()

    valid = []
    rejected = 0

    for ID, m, pk, cert, sig, fresh in tuples:

        # Tuple consistency.
        if cert[0] != ID or cert[1] != pk:
            rejected += 1
            continue

        # Optional RSU certificate pre-check.
        if not cert_validate_with(
            verifier,
            pk_CA,
            cert,
        ):
            rejected += 1
            continue

        valid.append(
            core.make_tuple(
                ID,
                m,
                pk,
                cert,
                sig,
                fresh,
            )
        )

    pre_ms = (
        time.perf_counter_ns() - pre_start
    ) / 1e6

    agg_ms, aggverify_ms, ok = finish_valid_batch(
        valid,
        verifier,
    )

    if ok:
        accepted = len(valid)
    else:
        accepted = 0
        rejected += len(valid)

    total_ms = (
        time.perf_counter_ns() - total_start
    ) / 1e6

    return {
        "total_ms": total_ms,
        "precheck_ms": pre_ms,
        "aggregate_ms": agg_ms,
        "aggverify_ms": aggverify_ms,
        "accepted": accepted,
        "rejected": rejected,
    }


def process_window_digest(
    records,
    pk_CA,
    verifier,
):
    total_start = time.perf_counter_ns()

    pre_start = time.perf_counter_ns()

    valid = []
    rejected = 0

    for rec in records:

        kind = rec["kind"]
        m = rec["m"]
        sig = rec["sig"]
        fresh = rec["fresh"]

        if kind == "attach":

            cert = rec["cert"]
            cid = rec["cid"]

            ID = cert[0]
            pk = cert[1]

            if core.xof(
                H_CERT,
                cert_bytes(cert),
            ) != cid:
                rejected += 1
                continue

            if not cert_validate_with(
                verifier,
                pk_CA,
                cert,
            ):
                rejected += 1
                continue

            CERT_CACHE[cid] = (
                pk,
                cert,
            )

        elif kind == "digest":

            cid = rec["cid"]

            cached = CERT_CACHE.get(cid)

            if cached is None:
                rejected += 1
                continue

            pk, cert = cached
            ID = cert[0]

        else:
            rejected += 1
            continue

        valid.append(
            core.make_tuple(
                ID,
                m,
                pk,
                cert,
                sig,
                fresh,
            )
        )

    pre_ms = (
        time.perf_counter_ns() - pre_start
    ) / 1e6

    agg_ms, aggverify_ms, ok = finish_valid_batch(
        valid,
        verifier,
    )

    if ok:
        accepted = len(valid)
    else:
        accepted = 0
        rejected += len(valid)

    total_ms = (
        time.perf_counter_ns() - total_start
    ) / 1e6

    return {
        "total_ms": total_ms,
        "precheck_ms": pre_ms,
        "aggregate_ms": agg_ms,
        "aggverify_ms": aggverify_ms,
        "accepted": accepted,
        "rejected": rejected,
    }


def run_scenario(
    name,
    n_veh,
    total_msgs,
    attacks,
    rate,
    seed=7,
):

    CERT_CACHE.clear()

    ca = oqs.Signature(ALG)
    pk_CA = ca.generate_keypair()

    vehicles = [
        Vehicle(ca)
        for _ in range(n_veh)
    ]

    duration = (
        total_msgs
        / (n_veh * rate)
        * 1000.0
    )

    arr = sorted(
        np.random.default_rng(seed).uniform(
            0,
            duration,
            total_msgs,
        )
    )

    if attacks:
        atk_idx = set(
            np.random.default_rng(
                seed + 1000
            ).choice(
                total_msgs,
                attacks,
                replace=False,
            )
        )
    else:
        atk_idx = set()

    latencies = []
    waits = []
    proc_total = []
    proc_pre = []
    proc_agg = []
    proc_verify = []
    batch_counts = []

    accepted = 0
    rejected = 0

    attached = set()

    with oqs.Signature(ALG) as verifier:

        i = 0
        w_end = W

        while i < len(arr):

            batch = []
            batch_arr = []

            while (
                i < len(arr)
                and arr[i] <= w_end
            ):

                v = vehicles[
                    i % n_veh
                ]

                attack = (
                    i in atk_idx
                )

                if ARGS.digest:

                    if attack:
                        rec = v.make_attach_record(
                            attack=True
                        )

                    elif v.ID not in attached:
                        rec = v.make_attach_record(
                            attack=False
                        )
                        attached.add(v.ID)

                    else:
                        rec = v.make_digest_record()

                    batch.append(rec)

                else:
                    batch.append(
                        v.make_full_tuple(
                            attack=attack
                        )
                    )

                batch_arr.append(
                    arr[i]
                )

                i += 1

            if batch:

                if ARGS.digest:
                    res = process_window_digest(
                        batch,
                        pk_CA,
                        verifier,
                    )
                else:
                    res = process_window_full(
                        batch,
                        pk_CA,
                        verifier,
                    )

                accepted += res["accepted"]
                rejected += res["rejected"]

                batch_counts.append(
                    len(batch)
                )

                proc_total.append(
                    res["total_ms"]
                )

                proc_pre.append(
                    res["precheck_ms"]
                )

                proc_agg.append(
                    res["aggregate_ms"]
                )

                proc_verify.append(
                    res["aggverify_ms"]
                )

                for arrival_ms in batch_arr:

                    wait = (
                        w_end
                        - arrival_ms
                    )

                    waits.append(wait)

                    latencies.append(
                        wait
                        + res["total_ms"]
                    )

            w_end += W

    return {
        "scenario": name,
        "vehicles": n_veh,
        "messages": total_msgs,
        "attacks": attacks,

        "t_avg": round(
            statistics.mean(
                batch_counts
            ),
            1,
        ),

        "wait_mean_ms": round(
            statistics.mean(
                waits
            ),
            3,
        ),

        "proc_total_mean_ms": round(
            statistics.mean(
                proc_total
            ),
            4,
        ),

        "proc_total_p95_ms": round(
            float(np.percentile(proc_total, 95)),
            4,
        ),

        "proc_total_max_ms": round(
            float(max(proc_total)),
            4,
        ),

        "proc_precheck_mean_ms": round(
            statistics.mean(
                proc_pre
            ),
            4,
        ),

        "proc_aggregate_mean_ms": round(
            statistics.mean(
                proc_agg
            ),
            4,
        ),

        "proc_aggverify_mean_ms": round(
            statistics.mean(
                proc_verify
            ),
            4,
        ),

        "latency_mean_ms": round(
            statistics.mean(
                latencies
            ),
            3,
        ),

        "latency_p95_ms": round(
            float(
                np.percentile(
                    latencies,
                    95,
                )
            ),
            3,
        ),

        "latency_p99_ms": round(
            float(
                np.percentile(
                    latencies,
                    99,
                )
            ),
            3,
        ),

        "latency_max_ms": round(
            float(max(latencies)),
            3,
        ),

        "deadline_misses": int(sum(
            x > DEADLINE
            for x in latencies
        )),

        "accepted": accepted,
        "rejected": rejected,
    }


def aggregate_seeds(rows):

    lat = [
        r["latency_mean_ms"]
        for r in rows
    ]

    total_messages = int(sum(
        r["messages"]
        for r in rows
    ))

    total_attacks = int(sum(
        r["attacks"]
        for r in rows
    ))

    accepted = int(sum(
        r["accepted"]
        for r in rows
    ))

    rejected = int(sum(
        r["rejected"]
        for r in rows
    ))

    misses = int(sum(
        r["deadline_misses"]
        for r in rows
    ))

    def avg(field):
        return round(
            statistics.mean(
                r[field]
                for r in rows
            ),
            4,
        )

    return {
        "scenario": rows[0]["scenario"],
        "seeds": len(rows),
        "messages_total": total_messages,
        "attacks_total": total_attacks,
        "accepted": accepted,
        "rejected": rejected,
        "acceptance_rate_pct": round(
            100.0 * accepted / total_messages,
            4,
        ),

        "latency_mean_ms": round(
            statistics.mean(lat),
            3,
        ),

        "latency_mean_ci95": (
            round(
                mean_ci95(lat)[1],
                3,
            )
            if len(rows) > 1
            else None
        ),

        "t_avg": round(
            statistics.mean(
                r["t_avg"] for r in rows
            ),
            1,
        ),

        "latency_p95_seed_mean_ms":
            avg("latency_p95_ms"),

        "latency_p99_seed_mean_ms":
            avg("latency_p99_ms"),

        "latency_max_ms": round(
            max(
                r["latency_max_ms"]
                for r in rows
            ),
            3,
        ),

        "proc_total_mean_ms":
            avg("proc_total_mean_ms"),

        "proc_total_p95_seed_mean_ms":
            avg("proc_total_p95_ms"),

        "proc_total_max_ms": round(
            max(
                r["proc_total_max_ms"]
                for r in rows
            ),
            4,
        ),

        "proc_precheck_mean_ms":
            avg("proc_precheck_mean_ms"),

        "proc_aggregate_mean_ms":
            avg("proc_aggregate_mean_ms"),

        "proc_aggverify_mean_ms":
            avg("proc_aggverify_mean_ms"),

        "deadline_misses": misses,

        "miss_rate_pct": round(
            100.0
            * misses
            / total_messages,
            4,
        ),
    }


def json_default(obj):
    """Convert NumPy scalar/array objects to JSON-safe Python types."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(
        f"Object of type {obj.__class__.__name__} is not JSON serializable"
    )


def main():

    scenarios = [
        (
            "highway-n20",
            20,
            1586,
            0,
            9.00,
        ),
        (
            "highway-n20-attack",
            20,
            1865,
            200,
            9.00,
        ),
        (
            "urban-n30",
            30,
            2210,
            0,
            7.33,
        ),
        (
            "intersection-n15",
            15,
            1478,
            0,
            16.67,
        ),
    ]

    mode = (
        "digest"
        if ARGS.digest
        else "full"
    )

    out = {
        "profile": "final-k384",
        "hash_bytes": KAPPA,
        "full_wire_bytes": 8694,
        "digest_wire_bytes": 3465,

        "window_ms": W,
        "deadline_ms": DEADLINE,
        "mode": mode,

        "framework_path": (
            "cert-precheck/cache"
            " -> Agg"
            " -> AggCheck/AggVerify"
            " -> verdict"
        ),

        "transport_before_rsu_included": False,
        "rsu_to_cs_backhaul_included": False,

        "seeds": ARGS.seeds,
        "algorithm": ALG,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "liboqs": oqs.oqs_version(),
        "liboqs_python": oqs.oqs_python_version(),

        "per_seed": [],
        "summary": [],
    }

    for scenario in scenarios:

        rows = []

        for k in range(
            ARGS.seeds
        ):

            r = run_scenario(
                *scenario,
                seed=7 + 97 * k,
            )

            rows.append(r)
            out["per_seed"].append(r)

        summary = aggregate_seeds(
            rows
        )

        out["summary"].append(
            summary
        )

        print(
            json.dumps(
                summary,
                indent=1,
                default=json_default,
            )
        )

    filename = (
        f"e2e_fullpath_W"
        f"{int(W)}_{mode}.json"
    )

    with open(
        filename,
        "w",
    ) as fh:
        json.dump(
            out,
            fh,
            indent=1,
            default=json_default,
        )

    print(
        f"\nSaved {filename}"
    )


if __name__ == "__main__":
    main()
