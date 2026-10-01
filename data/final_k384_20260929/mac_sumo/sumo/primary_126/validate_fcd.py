#!/usr/bin/env python3

import json
import math
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

FCD = Path("studyarea_fcd_final_126.xml")

RSU_X = 80.0
RSU_Y = 36.0
RADIUS = 150.0
R2 = RADIUS ** 2

all_vehicles = set()
rsu_vehicles = set()

active_contacts = {}
contact_intervals = []

occupancy_sum = 0
entry_events = 0

first_t = None
last_t = None
previous_t = None
steps = []


def percentile(values, p):
    xs = sorted(values)

    if not xs:
        return None

    if len(xs) == 1:
        return xs[0]

    pos = (len(xs) - 1) * p / 100.0
    lo = math.floor(pos)
    hi = math.ceil(pos)

    if lo == hi:
        return xs[lo]

    return (
        xs[lo] * (hi - pos)
        + xs[hi] * (pos - lo)
    )


for _, elem in ET.iterparse(FCD, events=("end",)):

    if elem.tag != "timestep":
        continue

    t = float(elem.get("time", "0"))

    if first_t is None:
        first_t = t

    if previous_t is not None:
        dt = t - previous_t
        if dt > 0:
            steps.append(dt)

    previous_t = t
    last_t = t

    inside_now = set()

    for veh in elem.findall("vehicle"):

        vid = veh.get("id")
        x = float(veh.get("x", "0"))
        y = float(veh.get("y", "0"))

        all_vehicles.add(vid)

        inside = (
            (x - RSU_X) ** 2
            + (y - RSU_Y) ** 2
            <= R2
        )

        if not inside:
            continue

        inside_now.add(vid)
        rsu_vehicles.add(vid)

        if vid not in active_contacts:
            active_contacts[vid] = [t, t]
            entry_events += 1
        else:
            active_contacts[vid][1] = t

    occupancy_sum += len(inside_now)

    ended = [
        vid
        for vid in active_contacts
        if vid not in inside_now
    ]

    for vid in ended:
        start, end = active_contacts.pop(vid)
        contact_intervals.append((start, end))

    elem.clear()


for vid, (start, end) in active_contacts.items():
    contact_intervals.append((start, end))


step = statistics.median(steps) if steps else 1.0

duration = (
    (last_t - first_t + step)
    if first_t is not None
    else 0
)

contacts = [
    (end - start + step)
    for start, end in contact_intervals
]

mean_concurrent = (
    occupancy_sum * step / duration
    if duration > 0
    else 0
)

traffic_throughput = (
    len(all_vehicles) * 3600.0 / duration
    if duration > 0
    else 0
)

result = {
    "fcd": str(FCD),
    "rsu": {
        "x": RSU_X,
        "y": RSU_Y,
        "radius_m": RADIUS,
    },
    "simulation": {
        "first_s": first_t,
        "last_s": last_t,
        "duration_s": duration,
        "step_s": step,
    },
    "traffic": {
        "all_unique_vehicles": len(all_vehicles),
        "throughput_veh_h": traffic_throughput,
    },
    "coverage": {
        "entry_events": entry_events,
        "unique_vehicles": len(rsu_vehicles),
        "mean_concurrent": mean_concurrent,
        "contact_count": len(contacts),
        "contact_mean_s": statistics.mean(contacts) if contacts else None,
        "contact_p5_s": percentile(contacts, 5),
        "contact_p50_s": percentile(contacts, 50),
        "contact_p95_s": percentile(contacts, 95),
        "contact_min_s": min(contacts) if contacts else None,
        "contact_max_s": max(contacts) if contacts else None,
    },
}

print()
print("=== SUMO 1.26 PRIMARY MOBILITY ===")
print(f'FCD                  : {FCD}')
print(f'RSU                  : ({RSU_X}, {RSU_Y})')
print(f'Radius               : {RADIUS:.0f} m')
print(f'Simulation duration  : {duration:.1f} s')
print(f'Simulation step      : {step:.1f} s')
print(f'All unique vehicles  : {len(all_vehicles)}')
print(f'Traffic throughput   : {traffic_throughput:.1f} veh/h')
print(f'RSU entry events     : {entry_events}')
print(f'RSU unique vehicles  : {len(rsu_vehicles)}')
print(f'Mean concurrent RSU  : {mean_concurrent:.2f}')

if contacts:
    print(f'Contact mean         : {statistics.mean(contacts):.2f} s')
    print(f'Contact p5           : {percentile(contacts, 5):.2f} s')
    print(f'Contact p50          : {percentile(contacts, 50):.2f} s')
    print(f'Contact p95          : {percentile(contacts, 95):.2f} s')
    print(f'Contact min          : {min(contacts):.2f} s')
    print(f'Contact max          : {max(contacts):.2f} s')

print("===================================")

out = Path(
    "../rerun/final_k384/sumo/"
    "primary_126/mobility_validation.json"
)

out.write_text(
    json.dumps(result, indent=2)
)

print()
print("Saved:", out)
