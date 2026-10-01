#!/usr/bin/env python3

import hashlib
import sys
import xml.etree.ElementTree as ET


def digest(path):
    h = hashlib.sha256()
    steps = 0
    observations = 0
    unique = set()

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "timestep":
            continue

        t = elem.get("time", "")
        h.update(f"T|{t}\n".encode())

        vehicles = []

        for veh in elem.findall("vehicle"):
            vid = veh.get("id", "")
            unique.add(vid)

            attrs = tuple(sorted(veh.attrib.items()))
            vehicles.append((vid, attrs))

        vehicles.sort(key=lambda x: (x[0], x[1]))

        for vid, attrs in vehicles:
            line = "V|" + vid + "|" + "|".join(
                f"{k}={v}" for k, v in attrs
            ) + "\n"

            h.update(line.encode())
            observations += 1

        steps += 1
        elem.clear()

    return {
        "sha256": h.hexdigest(),
        "steps": steps,
        "observations": observations,
        "unique_vehicles": len(unique),
    }


if len(sys.argv) != 3:
    print("Usage: compare_two_fcd.py FILE_A FILE_B")
    raise SystemExit(2)

a = digest(sys.argv[1])
b = digest(sys.argv[2])

for f, r in [(sys.argv[1], a), (sys.argv[2], b)]:
    print()
    print(f)
    print("  trajectory SHA256 :", r["sha256"])
    print("  timesteps         :", r["steps"])
    print("  observations      :", r["observations"])
    print("  unique vehicles   :", r["unique_vehicles"])

print()

if a == b:
    print("SEED42_TRAJECTORY_REPRODUCIBLE_OK")
else:
    print("SEED42_TRAJECTORY_DIFFERENT")
    raise SystemExit(1)
