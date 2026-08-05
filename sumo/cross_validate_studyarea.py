import sys
import math
import xml.etree.ElementTree as ET
import numpy as np
from scipy.optimize import linear_sum_assignment

# StudyArea RSU position and valid urban coverage radius
RSU_X = 80.0
RSU_Y = 36.0
R = 150.0
OBS = 5.0

rng = np.random.default_rng(20260603)

def load_fcd(fcd_file):
    times = {}
    for _, elem in ET.iterparse(fcd_file, events=("end",)):
        if elem.tag == "timestep":
            t = round(float(elem.get("time")), 1)
            vehs = {}
            for v in elem.findall("vehicle"):
                try:
                    vehs[v.get("id")] = (
                        float(v.get("x")),
                        float(v.get("y")),
                        float(v.get("speed")),
                        float(v.get("angle")),
                    )
                except Exception:
                    pass
            times[t] = vehs
            elem.clear()
    return times

def in_coverage(x, y):
    return (x - RSU_X) ** 2 + (y - RSU_Y) ** 2 <= R ** 2

def heading(speed, angle_deg):
    r = math.radians(angle_deg)
    return speed * math.sin(r), speed * math.cos(r)

def main(fcd_file):
    T = load_fcd(fcd_file)
    ts = sorted(T.keys())
    steady = [t for t in ts if 60 <= t <= 3300]

    ks = []
    for t in steady:
        k = sum(1 for (x, y, s, a) in T[t].values() if in_coverage(x, y))
        ks.append(k)

    print(f"SUMO FCD: {len(ts)} steps")
    print()
    print("(1) batch size k in RSU coverage")
    print(f"RSU center=({RSU_X:.1f},{RSU_Y:.1f}), R={R:.0f} m")
    print(f"mean={np.mean(ks):.1f} p95={np.percentile(ks,95):.0f}")
    print()

    print("(2) trajectory-aware linking advantage")

    for W in (5, 10, 20, 40, 60):
        accs = []
        klist = []

        for t0 in steady[::20]:
            t1 = round(t0 + W, 1)
            if t1 not in T:
                continue

            old = {
                vid: p
                for vid, p in T[t0].items()
                if in_coverage(p[0], p[1]) and vid in T[t1]
            }

            ids = list(old.keys())
            k = len(ids)

            if k < 2:
                continue

            pred = np.zeros((k, 2))
            next_pos = np.zeros((k, 2))

            for j, vid in enumerate(ids):
                x, y, s, a = old[vid]
                vx, vy = heading(s, a)
                pred[j] = (x + vx * W, y + vy * W)

                nx, ny, _, _ = T[t1][vid]
                next_pos[j] = (
                    nx + rng.normal(0, OBS),
                    ny + rng.normal(0, OBS),
                )

            perm = rng.permutation(k)

            C = np.linalg.norm(
                pred[:, None, :] - next_pos[perm][None, :, :],
                axis=2,
            )

            row, col = linear_sum_assignment(C)
            truth = np.argsort(perm)
            acc = np.sum(col[row] == truth[row]) / k

            accs.append(acc)
            klist.append(k)

        if accs:
            kk = np.mean(klist)
            adv = (np.mean(accs) - 1 / kk) / (1 - 1 / kk)
            print(
                f"W={W:2d}s "
                f"acc={np.mean(accs):.3f} "
                f"adv={adv:.3f} "
                f"avg_k={kk:.1f}"
            )
        else:
            print(f"W={W:2d}s no valid batches")

if __name__ == "__main__":
    fcd = sys.argv[1] if len(sys.argv) > 1 else "fcd.xml"
    main(fcd)
