#!/usr/bin/env python3

"""
Final SUMO-FCD -> PQ-CBAS-DSH full-framework bridge.

Final profile:
  - ML-DSA-65
  - kappa = 384 bit / 48 B
  - full wire = 8694 B
  - digest wire = 3465 B
  - one measured authentication event per RSU entry
  - 90-ms collection windows
  - transport excluded
  - timed verifier path:
      certificate precheck/cache resolution
      -> canonical Sort
      -> Agg
      -> AggVerify
      -> verdict

The 20 seeds vary only the +/-10 ms scheduling jitter over one
fixed SUMO FCD mobility trace. They are NOT independent mobility seeds.
"""

import argparse
import inspect
import json
import math
import platform
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np
import oqs


# ------------------------------------------------------------
# Import final E3 implementation while shielding its argparse
# ------------------------------------------------------------

_saved_argv = list(sys.argv)

try:
    sys.argv = [sys.argv[0]]
    import e2e_workflow_full as fw
finally:
    sys.argv = _saved_argv


DEADLINE_DEFAULT_MS = 100.0


# ------------------------------------------------------------
# Mobility
# ------------------------------------------------------------

def parse_fcd_entries(fcd_path, rsu_x, rsu_y, radius):
    """
    Extract every transition from outside -> inside RSU coverage.

    Returns:
        arrivals: [(entry_time_ms, vehicle_id), ...]
    """

    r2 = radius * radius

    inside_previous = set()
    arrivals = []

    timesteps = 0
    all_vehicles = set()

    for _, elem in ET.iterparse(
        fcd_path,
        events=("end",)
    ):
        if elem.tag != "timestep":
            continue

        timesteps += 1

        t_s = float(elem.get("time", "0"))
        t_ms = t_s * 1000.0

        inside_now = set()

        for veh in elem.findall("vehicle"):
            vid = veh.get("id")

            x = float(veh.get("x", "0"))
            y = float(veh.get("y", "0"))

            all_vehicles.add(vid)

            d2 = (
                (x - rsu_x) ** 2
                + (y - rsu_y) ** 2
            )

            if d2 <= r2:
                inside_now.add(vid)

                if vid not in inside_previous:
                    arrivals.append(
                        (t_ms, vid)
                    )

        inside_previous = inside_now
        elem.clear()

    arrivals.sort(
        key=lambda x: (x[0], x[1])
    )

    return arrivals, {
        "timesteps": timesteps,
        "all_unique_vehicles": len(all_vehicles),
        "entry_events": len(arrivals),
        "unique_rsu_vehicles": len(
            {vid for _, vid in arrivals}
        ),
    }


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

def percentile(values, p):
    if not values:
        return 0.0

    return float(
        np.percentile(
            np.asarray(values, dtype=float),
            p
        )
    )


def mean(values):
    if not values:
        return 0.0

    return float(
        statistics.mean(values)
    )


def ci95_t(seed_means):
    """
    Student-t 95% CI half-width.

    Final experiment uses n=20 -> df=19:
    t_0.975,19 = 2.093024054.
    """

    n = len(seed_means)

    if n <= 1:
        return 0.0

    df = n - 1

    t_table = {
        1: 12.706205,
        2: 4.302653,
        3: 3.182446,
        4: 2.776445,
        5: 2.570582,
        6: 2.446912,
        7: 2.364624,
        8: 2.306004,
        9: 2.262157,
        10: 2.228139,
        11: 2.200985,
        12: 2.178813,
        13: 2.160369,
        14: 2.144787,
        15: 2.131450,
        16: 2.119905,
        17: 2.109816,
        18: 2.100922,
        19: 2.093024054,
        20: 2.085963,
        21: 2.079614,
        22: 2.073873,
        23: 2.068658,
        24: 2.063899,
        25: 2.059539,
        26: 2.055529,
        27: 2.051831,
        28: 2.048407,
        29: 2.045230,
        30: 2.042272,
    }

    tcrit = t_table.get(
        df,
        1.959964
    )

    sd = statistics.stdev(
        seed_means
    )

    return (
        tcrit
        * sd
        / math.sqrt(n)
    )


# ------------------------------------------------------------
# Result adapter
# ------------------------------------------------------------

def normalize_window_result(
    result,
    batch_size
):
    if not isinstance(result, dict):
        raise RuntimeError(
            "process_window_* did not return dict: "
            + repr(result)
        )

    pre = float(
        result.get(
            "precheck_ms",
            result.get(
                "cert_ms",
                0.0
            )
        )
    )

    agg = float(
        result.get(
            "aggregate_ms",
            result.get(
                "agg_ms",
                0.0
            )
        )
    )

    av = float(
        result.get(
            "aggverify_ms",
            result.get(
                "verify_ms",
                0.0
            )
        )
    )

    total = float(
        result.get(
            "total_ms",
            result.get(
                "elapsed_ms",
                pre + agg + av
            )
        )
    )

    accepted = result.get("accepted")
    rejected = result.get("rejected")

    if accepted is None:
        accepted = result.get("acc")

    if rejected is None:
        rejected = result.get("rej")

    if (
        accepted is None
        or rejected is None
    ):
        verdict = None

        for key in (
            "ok",
            "verdict",
            "agg_ok"
        ):
            if key in result:
                verdict = bool(
                    result[key]
                )
                break

        if verdict is None:
            raise RuntimeError(
                "Cannot determine accepted/rejected "
                "from process_window result. Keys: "
                + repr(sorted(result.keys()))
            )

        accepted = (
            batch_size
            if verdict
            else 0
        )

        rejected = (
            0
            if verdict
            else batch_size
        )

    return {
        "total_ms": total,
        "precheck_ms": pre,
        "aggregate_ms": agg,
        "aggverify_ms": av,
        "accepted": int(accepted),
        "rejected": int(rejected),
        "raw_keys": sorted(
            result.keys()
        ),
    }


# ------------------------------------------------------------
# One scheduling-jitter seed
# ------------------------------------------------------------

def run_seed(
    arrivals,
    identity_by_vid,
    pk_ca,
    window_ms,
    digest_mode,
    digest_cache_model,
    seed,
    deadline_ms,
    jitter_ms,
):
    fw.CERT_CACHE.clear()

    # Warm cache = first valid full-certificate attach happened
    # before the measured steady-state CertID message.
    if (
        digest_mode
        and digest_cache_model == "warm"
    ):
        for v in identity_by_vid.values():
            fw.CERT_CACHE[
                v.cert_id
            ] = (
                v.pk,
                v.cert
            )

    rng = np.random.default_rng(
        seed
    )

    schedule = []

    for event_idx, (
        entry_ms,
        vid
    ) in enumerate(arrivals):

        jitter = float(
            rng.uniform(
                -jitter_ms,
                jitter_ms
            )
        )

        arrival_ms = max(
            0.0,
            entry_ms + jitter
        )

        # Collection windows are anchored at t=0:
        # (0,W], (W,2W], ...
        win_index = max(
            1,
            int(
                math.ceil(
                    arrival_ms
                    / window_ms
                )
            )
        )

        close_ms = (
            win_index
            * window_ms
        )

        schedule.append(
            (
                close_ms,
                arrival_ms,
                event_idx,
                vid,
            )
        )

    groups = defaultdict(list)

    for row in schedule:
        groups[row[0]].append(row)

    latencies = []

    proc_total = []
    proc_pre = []
    proc_agg = []
    proc_av = []

    batch_sizes = []

    accepted_total = 0
    rejected_total = 0
    deadline_misses = 0

    first_result_keys = None

    with oqs.Signature(
        fw.ALG
    ) as verifier:

        for close_ms in sorted(groups):

            events = groups[
                close_ms
            ]

            batch = []
            arrival_times = []

            for (
                _,
                arrival_ms,
                _event_idx,
                vid,
            ) in events:

                v = identity_by_vid[
                    vid
                ]

                if digest_mode:

                    if (
                        digest_cache_model
                        == "warm"
                    ):
                        rec = (
                            v.make_digest_record()
                        )
                    else:
                        rec = (
                            v.make_attach_record(
                                attack=False
                            )
                        )

                    batch.append(rec)

                else:
                    batch.append(
                        v.make_full_tuple(
                            attack=False
                        )
                    )

                arrival_times.append(
                    arrival_ms
                )

            if digest_mode:
                raw = (
                    fw.process_window_digest(
                        batch,
                        pk_ca,
                        verifier,
                    )
                )
            else:
                raw = (
                    fw.process_window_full(
                        batch,
                        pk_ca,
                        verifier,
                    )
                )

            res = normalize_window_result(
                raw,
                len(batch)
            )

            if first_result_keys is None:
                first_result_keys = (
                    res["raw_keys"]
                )

            batch_sizes.append(
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

            proc_av.append(
                res["aggverify_ms"]
            )

            accepted_total += (
                res["accepted"]
            )

            rejected_total += (
                res["rejected"]
            )

            for arrival_ms in arrival_times:

                latency = (
                    close_ms
                    - arrival_ms
                    + res["total_ms"]
                )

                latencies.append(
                    latency
                )

                if latency > deadline_ms:
                    deadline_misses += 1

    return {
        "seed": int(seed),

        "messages": len(latencies),

        "accepted": accepted_total,
        "rejected": rejected_total,

        "windows": len(batch_sizes),

        "batch_mean": round(
            mean(batch_sizes),
            4
        ),

        "batch_p95": round(
            percentile(
                batch_sizes,
                95
            ),
            4
        ),

        "batch_max": (
            max(batch_sizes)
            if batch_sizes
            else 0
        ),

        "latency_mean_ms": round(
            mean(latencies),
            6
        ),

        "latency_p95_ms": round(
            percentile(
                latencies,
                95
            ),
            6
        ),

        "latency_p99_ms": round(
            percentile(
                latencies,
                99
            ),
            6
        ),

        "latency_max_ms": round(
            max(latencies)
            if latencies
            else 0.0,
            6
        ),

        "proc_total_mean_ms": round(
            mean(proc_total),
            6
        ),

        "proc_total_p95_ms": round(
            percentile(
                proc_total,
                95
            ),
            6
        ),

        "proc_total_max_ms": round(
            max(proc_total)
            if proc_total
            else 0.0,
            6
        ),

        "proc_precheck_mean_ms":
            round(
                mean(proc_pre),
                6
            ),

        "proc_aggregate_mean_ms":
            round(
                mean(proc_agg),
                6
            ),

        "proc_aggverify_mean_ms":
            round(
                mean(proc_av),
                6
            ),

        "deadline_misses":
            deadline_misses,

        "first_window_result_keys":
            first_result_keys,
    }


# ------------------------------------------------------------
# Multi-seed summary
# ------------------------------------------------------------

def summarize(rows):
    seed_latency_means = [
        r["latency_mean_ms"]
        for r in rows
    ]

    messages_total = sum(
        r["messages"]
        for r in rows
    )

    misses_total = sum(
        r["deadline_misses"]
        for r in rows
    )

    return {
        "seeds": len(rows),

        "messages_total":
            messages_total,

        "accepted_total": sum(
            r["accepted"]
            for r in rows
        ),

        "rejected_total": sum(
            r["rejected"]
            for r in rows
        ),

        "windows_total": sum(
            r["windows"]
            for r in rows
        ),

        "batch_mean": round(
            mean([
                r["batch_mean"]
                for r in rows
            ]),
            4
        ),

        "batch_p95_seed_mean": round(
            mean([
                r["batch_p95"]
                for r in rows
            ]),
            4
        ),

        "batch_max": max(
            r["batch_max"]
            for r in rows
        ),

        "latency_mean_ms": round(
            mean(
                seed_latency_means
            ),
            6
        ),

        "latency_mean_ci95_ms": round(
            ci95_t(
                seed_latency_means
            ),
            6
        ),

        "latency_p95_seed_mean_ms":
            round(
                mean([
                    r["latency_p95_ms"]
                    for r in rows
                ]),
                6
            ),

        "latency_p99_seed_mean_ms":
            round(
                mean([
                    r["latency_p99_ms"]
                    for r in rows
                ]),
                6
            ),

        "latency_max_ms": round(
            max(
                r["latency_max_ms"]
                for r in rows
            ),
            6
        ),

        "proc_total_mean_ms": round(
            mean([
                r["proc_total_mean_ms"]
                for r in rows
            ]),
            6
        ),

        "proc_total_p95_seed_mean_ms":
            round(
                mean([
                    r["proc_total_p95_ms"]
                    for r in rows
                ]),
                6
            ),

        "proc_total_max_ms": round(
            max(
                r["proc_total_max_ms"]
                for r in rows
            ),
            6
        ),

        "proc_precheck_mean_ms":
            round(
                mean([
                    r["proc_precheck_mean_ms"]
                    for r in rows
                ]),
                6
            ),

        "proc_aggregate_mean_ms":
            round(
                mean([
                    r["proc_aggregate_mean_ms"]
                    for r in rows
                ]),
                6
            ),

        "proc_aggverify_mean_ms":
            round(
                mean([
                    r["proc_aggverify_mean_ms"]
                    for r in rows
                ]),
                6
            ),

        "deadline_misses":
            misses_total,

        "miss_rate_pct": round(
            (
                100.0
                * misses_total
                / messages_total
            )
            if messages_total
            else 0.0,
            8
        ),
    }


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--fcd",
        required=True
    )

    ap.add_argument(
        "--no-sumo",
        action="store_true"
    )

    ap.add_argument(
        "--rsu-x",
        type=float,
        default=80.0
    )

    ap.add_argument(
        "--rsu-y",
        type=float,
        default=36.0
    )

    ap.add_argument(
        "--R",
        type=float,
        default=150.0
    )

    ap.add_argument(
        "--window",
        type=float,
        default=90.0
    )

    ap.add_argument(
        "--seeds",
        type=int,
        default=20
    )

    ap.add_argument(
        "--digest",
        action="store_true"
    )

    ap.add_argument(
        "--digest-cache-model",
        choices=(
            "warm",
            "cold"
        ),
        default="warm"
    )

    ap.add_argument(
        "--deadline",
        type=float,
        default=DEADLINE_DEFAULT_MS
    )

    ap.add_argument(
        "--jitter",
        type=float,
        default=10.0
    )

    ap.add_argument(
        "--max-events",
        type=int,
        default=0,
        help=(
            "sanity-test only; "
            "0 = all FCD entries"
        )
    )

    ap.add_argument(
        "--output",
        default=None
    )

    args = ap.parse_args()

    fcd = Path(
        args.fcd
    )

    if not fcd.exists():
        raise SystemExit(
            f"FCD not found: {fcd}"
        )

    # Final-profile gates.
    core_kappa = getattr(
        fw.core,
        "KAPPA",
        None
    )

    if core_kappa != 48:
        raise SystemExit(
            f"FINAL PROFILE ERROR: "
            f"core.KAPPA={core_kappa}, "
            f"expected 48"
        )

    print(
        "=== FINAL SUMO FULL-PATH BRIDGE ==="
    )

    print(
        "Python             :",
        platform.python_version()
    )

    print(
        "liboqs-python     :",
        oqs.oqs_python_version()
    )

    print(
        "liboqs            :",
        oqs.oqs_version()
    )

    print(
        "Algorithm         :",
        fw.ALG
    )

    print(
        "KAPPA             :",
        core_kappa,
        "bytes"
    )

    print(
        "process_window_full:",
        inspect.signature(
            fw.process_window_full
        )
    )

    print(
        "process_window_digest:",
        inspect.signature(
            fw.process_window_digest
        )
    )

    arrivals, mobility = (
        parse_fcd_entries(
            str(fcd),
            args.rsu_x,
            args.rsu_y,
            args.R
        )
    )

    if args.max_events > 0:
        arrivals = arrivals[
            :args.max_events
        ]

    print(
        "FCD entry events   :",
        len(arrivals)
    )

    print(
        "FCD unique RSU veh :",
        len(
            {vid for _, vid in arrivals}
        )
    )

    if not arrivals:
        raise SystemExit(
            "No RSU entry events"
        )

    unique_vids = sorted(
        {vid for _, vid in arrivals}
    )

    print(
        "Creating crypto identities:",
        len(unique_vids)
    )

    # One crypto identity per FCD vehicle.
    with oqs.Signature(
        fw.ALG
    ) as ca:

        pk_ca = (
            ca.generate_keypair()
        )

        identity_by_vid = {}

        for n, vid in enumerate(
            unique_vids,
            start=1
        ):
            identity_by_vid[
                vid
            ] = fw.Vehicle(ca)

            if (
                n % 500 == 0
                or n == len(unique_vids)
            ):
                print(
                    f"  identities "
                    f"{n}/{len(unique_vids)}"
                )

        rows = []

        for k in range(
            args.seeds
        ):
            seed = (
                7
                + 97 * k
            )

            print(
                f"[seed {k+1:02d}/"
                f"{args.seeds:02d}] "
                f"rng={seed}"
            )

            row = run_seed(
                arrivals=arrivals,
                identity_by_vid=
                    identity_by_vid,
                pk_ca=pk_ca,
                window_ms=args.window,
                digest_mode=args.digest,
                digest_cache_model=
                    args.digest_cache_model,
                seed=seed,
                deadline_ms=
                    args.deadline,
                jitter_ms=args.jitter,
            )

            rows.append(row)

            print(
                "  messages=",
                row["messages"],
                " accepted=",
                row["accepted"],
                " rejected=",
                row["rejected"],
                " proc=",
                row["proc_total_mean_ms"],
                "ms",
                " latency=",
                row["latency_mean_ms"],
                "ms",
                " p99=",
                row["latency_p99_ms"],
                " max=",
                row["latency_max_ms"],
                " miss=",
                row["deadline_misses"],
                sep=""
            )

    summary = summarize(
        rows
    )

    mode = (
        "digest"
        if args.digest
        else "full"
    )

    output = (
        args.output
        if args.output
        else (
            f"sumo_fullpath_"
            f"W{int(args.window)}_"
            f"{mode}.json"
        )
    )

    result = {
        "experiment":
            "SUMO-FCD RSU-arrival-to-verdict",

        "mode": mode,

        "digest_cache_model":
            (
                args.digest_cache_model
                if args.digest
                else None
            ),

        "transport_included":
            False,

        "mobility_seed_model":
            (
                "single fixed FCD; "
                "20 seeds vary only "
                "authentication scheduling "
                "jitter"
            ),

        "fcd_file":
            str(fcd),

        "rsu": {
            "x": args.rsu_x,
            "y": args.rsu_y,
            "radius_m": args.R,
        },

        "window_ms":
            args.window,

        "deadline_ms":
            args.deadline,

        "jitter_ms":
            args.jitter,

        "python":
            platform.python_version(),

        "liboqs_python":
            str(
                oqs.oqs_python_version()
            ),

        "liboqs":
            str(
                oqs.oqs_version()
            ),

        "algorithm":
            fw.ALG,

        "kappa_bytes":
            core_kappa,

        "full_wire_bytes":
            8694,

        "digest_wire_bytes":
            3465,

        "timed_path": (
            "certificate-precheck/cache"
            " -> canonical Sort"
            " -> Agg"
            " -> AggVerify"
            " -> verdict"
        ),

        "mobility": mobility,

        "measured_entry_events":
            len(arrivals),

        "measured_unique_vehicles":
            len(
                {vid for _, vid in arrivals}
            ),

        "per_seed": rows,

        "summary": summary,
    }

    Path(output).write_text(
        json.dumps(
            result,
            indent=2
        )
        + "\n"
    )

    print()
    print(
        "=== SUMMARY ==="
    )

    print(
        json.dumps(
            summary,
            indent=2
        )
    )

    print()
    print(
        "Saved:",
        output
    )


if __name__ == "__main__":
    main()
