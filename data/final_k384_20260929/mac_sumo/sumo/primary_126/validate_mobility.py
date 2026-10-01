#!/usr/bin/env python3

import json
import math
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

FCD = Path("studyarea_fcd_final_126.xml")

RSU_X = 80.0
RSU_Y = 36.0
R = 150.0
R2 = R * R

all_vehicles = set()
rsu_vehicles = set()

active_contacts = {}
completed_contacts = []

occupancies = []
entry_events = 0

first_t = None
last_t = None
prev_t = None
steps = []


def percentile(xs, p):
    xs = sorted(xs)

    if not xs:
        return None

    if len(xs) == 1:
        return xs[0]

    k = (len(xs) - 1) * p / 100.0
    lo = math.floor(k)
    hi = math.ceil(k)

    if lo == hi:
        return xs[lo]

    return xs[lo] * (hi - k) + xs[hi] * (k - lo)


for _, elem in ET.iterparse(FCD, events=("end",)):

    if elem.tag != "timestep":
        continue

    t = float(elem.get("time", "0"))

    if first_t is None:
        first_t = t

    if prev_t is not None and t > prev_t:
        steps.append(t - prev_t)

    prev_t = t
    last_t = t

    inside_now = set()

    for veh in elem.findall("vehicle"):

        vid = veh.get("id")
        x = float(veh.get("x", "0"))
        y = float(veh.get("y", "0"))

        all_vehicles.add(vid)

        if (
            (x - RSU_X) ** 2
            + (y - RSU_Y) ** 2
            <= R2
        ):
            inside_now.add(vid)
            rsu_vehicles.add(vid)

            if vid not in active_contacts:
                active_contacts[vid] = [t, t]
                entry_events += 1
            else:
                active_contacts[vid][1] = t

    ended = [
        vid for vid in active_contacts
        if vid not in inside_now
    ]

    for vid in ended:
        start, end = active_contacts.pop(vid)
        completed_contacts.append((start, end))

    occupancies.append(len(inside_now))

    elem.clear()


for vid, (start, end) in active_contacts.items():
    completed_contacts.append((start, end))


step = statistics.median(steps) if steps else 1.0

duration = (
    last_t - first_t + step
    if first_t is not None
    else 0.0
)

contact_seconds = [
    end - start + step
    for start, end in completed_contacts
]

throughput = (
    len(all_vehicles) * 3600.0 / duration
    if duration > 0
    else 0.0
)

result = {
    "fcd": str(FCD),
    "sumo_version": "1.26.0",

    "rsu": {
        "x": RSU_X,
        "y": RSU_Y,
        "radius_m": R
    },

    "simulation": {
        "duration_s": duration,
        "step_s": step
    },

    "traffic": {
        "all_unique_vehicles": len(all_vehicles),
        "throughput_veh_h": throughput
    },

    "coverage": {
        "entry_events": entry_events,
        "unique_vehicles": len(rsu_vehicles),

        "mean_concurrent": (
            statistics.mean(occupancies)
            if occupancies else 0
        ),

        "p95_concurrent": (
            percentile(occupancies, 95)
            if occupancies else 0
        ),

        "contact_count": len(contact_seconds),

        "contact_mean_s": (
            statistics.mean(contact_seconds)
            if contact_seconds else None
        ),

        "contact_p5_s": percentile(contact_seconds, 5),
        "contact_p50_s": percentile(contact_seconds, 50),
        "contact_p95_s": percentile(contact_seconds, 95),

        "contact_min_s": (
            min(contact_seconds)
            if contact_seconds else None
        ),

        "contact_max_s": (
            max(contact_seconds)
            if contact_seconds else None
        )
    }
}


print()
print("=== SUMO 1.26 MOBILITY FINAL ===")

print("FCD                  :", FCD)
print("Simulation duration  :", round(duration, 2), "s")
print("Simulation step      :", round(step, 3), "s")

print("All unique vehicles  :", len(all_vehicles))
print("Traffic throughput   :", round(throughput, 2), "veh/h")

print("RSU entry events     :", entry_events)
print("RSU unique vehicles  :", len(rsu_vehicles))

if occupancies:
    print(
        "Mean concurrent RSU  :",
        round(statistics.mean(occupancies), 2)
    )

    print(
        "p95 concurrent RSU   :",
        round(percentile(occupancies, 95), 2)
    )

if contact_seconds:
    print(
        "Contact mean         :",
        round(statistics.mean(contact_seconds), 2),
        "s"
    )

    print(
        "Contact p5           :",
        round(percentile(contact_seconds, 5), 2),
        "s"
    )

    print(
        "Contact p50          :",
        round(percentile(contact_seconds, 50), 2),
        "s"
    )

    print(
        "Contact p95          :",
        round(percentile(contact_seconds, 95), 2),
        "s"
    )

    print(
        "Contact min/max      :",
        round(min(contact_seconds), 2),
        "/",
        round(max(contact_seconds), 2),
        "s"
    )

print("================================")

out = Path(
    "../rerun/final_k384/sumo/"
    "primary_126/mobility_validation.json"
)

out.write_text(
    json.dumps(result, indent=2)
)

print("Saved:", out)
