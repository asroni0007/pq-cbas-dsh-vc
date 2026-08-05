#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 BPU-CBAS-DSH  ·  SUMO/TraCI evaluation driver
================================================================================
Runs the SUMO scenario, measures each vehicle's REAL contact time with the RSU
coverage, and derives the pseudonym-refresh delivery ratio:

    a vehicle obtains its entry iff >= 1 of  r = floor(T_contact / T_tx)
    broadcast passes succeeds, each pass with prob (1 - p)
        => per-vehicle success = 1 - p^r
    T_tx = 8 * CO_bpu(n) / BW          (one full batch broadcast)
    CO_bpu(n) = 168 + 205 n  bytes     (paper's message model)

This replaces the closed-form / Monte-Carlo contact-time assumption with the
empirical contact-time distribution produced by SUMO mobility, and reproduces
the delivery-vs-n curve (paper Fig. 3) from a real microscopic traffic model.

USAGE
  1) build the network:        bash build_net.sh
  2) run with SUMO:            python run_bpu_sumo.py --bw 12 --p 0.1
     (GUI:)                    python run_bpu_sumo.py --gui
  3) no SUMO yet? sanity test: python run_bpu_sumo.py --dry-run

OUTPUT
  contact_times.csv      per-vehicle contact time (s)
  delivery_vs_n.csv      delivery ratio vs refresh size n (for --bw)
  fig_delivery_sumo.png  delivery-vs-n plot (matches paper Fig. 3 style)
================================================================================
"""
import os, sys, math, csv, random, argparse

# ----------------------------------------------------------------------------
# Paper message model (bytes) — keep in sync with the manuscript
# ----------------------------------------------------------------------------
SIZE = dict(Ctx=40, RL=32, Root=32, sigma=64, Entry=205)
def co_bpu(n):            return SIZE["Ctx"]+SIZE["RL"]+SIZE["Root"]+SIZE["sigma"]+n*SIZE["Entry"]
def tx_time(n, bw_bps):   return 8.0*co_bpu(n)/bw_bps          # seconds, one pass
def rounds(t_contact, n, bw_bps): return int(t_contact // tx_time(n, bw_bps))

def delivery_ratio(contact_times, n, bw_bps, p, seed=0):
    """Mean per-vehicle delivery for a given refresh size n and channel rate."""
    rng = random.Random(seed)
    ok = 0
    for tc in contact_times:
        r = rounds(tc, n, bw_bps)
        if r > 0 and rng.random() < (1.0 - p**r):
            ok += 1
    return ok / max(1, len(contact_times))

# ----------------------------------------------------------------------------
# SUMO/TraCI: collect real contact times with the RSU coverage
# ----------------------------------------------------------------------------
def collect_contact_times_sumo(cfg, rsu_x, rsu_y, R, step, gui):
    if "SUMO_HOME" in os.environ:
        sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
    try:
        import traci
    except ImportError:
        sys.exit("ERROR: TraCI not found. Set SUMO_HOME or `pip install traci sumolib`.")
    sumo_bin = "sumo-gui" if gui else "sumo"
    traci.start([sumo_bin, "-c", cfg, "--step-length", str(step),
                 "--no-step-log", "true", "--duration-log.disable", "true"])
    contact = {}
    R2 = R * R
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        for vid in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vid)
            if (x - rsu_x) ** 2 + (y - rsu_y) ** 2 <= R2:
                contact[vid] = contact.get(vid, 0.0) + step
    traci.close()
    return list(contact.values())

# ----------------------------------------------------------------------------
# Dry-run: synthesize contact times analytically (no SUMO needed)
#          T_contact = 2R/v for a vehicle crossing the coverage diameter
# ----------------------------------------------------------------------------
def collect_contact_times_dryrun(R, n_vehicles, speed_kmh_range, seed):
    rng = random.Random(seed)
    lo, hi = speed_kmh_range
    out = []
    for _ in range(n_vehicles):
        v = rng.uniform(lo, hi) / 3.6
        out.append(2.0 * R / v)
    return out

# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="BPU-CBAS-DSH SUMO/TraCI evaluation")
    ap.add_argument("--cfg", default="bpu.sumocfg")
    ap.add_argument("--rsu-x", type=float, default=1000.0)
    ap.add_argument("--rsu-y", type=float, default=0.0)
    ap.add_argument("--R", type=float, default=300.0, help="RSU coverage radius (m)")
    ap.add_argument("--bw", type=float, default=12.0, help="channel rate (Mbps)")
    ap.add_argument("--p", type=float, default=0.10, help="per-pass packet loss")
    ap.add_argument("--step", type=float, default=0.10, help="SUMO step length (s)")
    ap.add_argument("--gui", action="store_true", help="run sumo-gui")
    ap.add_argument("--dry-run", action="store_true",
                    help="skip SUMO; synthesize contact times to test the pipeline")
    ap.add_argument("--dry-vehicles", type=int, default=20000)
    ap.add_argument("--dry-speed", default="119,121", help="dry-run speed range km/h")
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()
    bw = args.bw * 1e6

    if args.dry_run:
        lo, hi = (float(x) for x in args.dry_speed.split(","))
        contacts = collect_contact_times_dryrun(args.R, args.dry_vehicles, (lo, hi), args.seed)
        src = "dry-run (synthetic 2R/v)"
    else:
        if not os.path.exists("bpu.net.xml"):
            sys.exit("ERROR: bpu.net.xml missing — run `bash build_net.sh` first.")
        contacts = collect_contact_times_sumo(args.cfg, args.rsu_x, args.rsu_y,
                                              args.R, args.step, args.gui)
        src = "SUMO mobility"

    if not contacts:
        sys.exit("No vehicles entered the RSU coverage — check geometry/demand.")

    # per-vehicle contact-time stats
    contacts.sort()
    mean_tc = sum(contacts) / len(contacts)
    print(f"[{src}] vehicles in coverage: {len(contacts)}")
    print(f"  contact time  mean={mean_tc:.2f}s  min={contacts[0]:.2f}s  "
          f"median={contacts[len(contacts)//2]:.2f}s")
    with open("contact_times.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["contact_time_s"])
        w.writerows([[round(t, 3)] for t in contacts])

    # delivery ratio vs refresh size n (paper Fig. 3), for this --bw and --p
    ns = [1000, 2000, 5000, 10000, 20000, 40000, 60000, 80000, 100000]
    print(f"\nDelivery ratio vs n  (BW={args.bw} Mbps, p={args.p}, R={args.R} m):")
    rows = []
    cap = None
    for n in ns:
        d = delivery_ratio(contacts, n, bw, args.p, seed=args.seed)
        rows.append([n, round(d * 100, 2), rounds(mean_tc, n, bw)])
        if d >= 0.99:
            cap = n
        print(f"  n={n:7d}: delivery={d*100:6.2f}%   mean rounds={rounds(mean_tc,n,bw)}")
    print(f"  -> single-RSU sustains >=99% refresh up to about n={cap}")
    with open("delivery_vs_n.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["n", "delivery_pct", "mean_rounds"]); w.writerows(rows)

    # optional plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.figure(figsize=(5, 3.2))
        plt.plot([r[0] for r in rows], [r[1] for r in rows], "s-", color="#ff7f0e")
        plt.axhline(99, ls=":", color="grey")
        plt.xscale("log"); plt.xlabel("Number of OBUs in one refresh (n)")
        plt.ylabel("Delivery ratio (%)"); plt.ylim(60, 102)
        plt.grid(True, which="both", ls=":", alpha=0.4)
        plt.title(f"BPU-CBAS-DSH delivery ({src}, {args.bw} Mbps, p={args.p})", fontsize=9)
        plt.tight_layout(); plt.savefig("fig_delivery_sumo.png", dpi=200)
        print("\nwrote fig_delivery_sumo.png")
    except Exception as e:
        print("plot skipped:", e)

    print("\nwrote contact_times.csv, delivery_vs_n.csv")

if __name__ == "__main__":
    main()
