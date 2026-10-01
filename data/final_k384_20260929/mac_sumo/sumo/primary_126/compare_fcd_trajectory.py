#!/usr/bin/env python3

import hashlib
import sys
import xml.etree.ElementTree as ET

def trajectory_digest(path):
    h = hashlib.sha256()

    steps = 0
    observations = 0
    unique = set()

    for event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "timestep":
            continue

        t = elem.get("time", "")
        h.update(f"T|{t}\n".encode())

        vehicles = []

        for veh in elem.findall("vehicle"):
            vid = veh.get("id", "")
            unique.add(vid)

            # Semua atribut kendaraan dimasukkan,
            # tetapi urutan atribut dibuat canonical.
            attrs = tuple(sorted(veh.attrib.items()))
            vehicles.append((vid, attrs))

        # Jangan bergantung pada urutan vehicle dalam XML.
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


files = [
    "studyarea_fcd_final_126.xml",
    "studyarea_fcd_repro_126.xml",
]

results = []

for f in files:
    r = trajectory_digest(f)
    results.append(r)

    print()
    print(f)
    print("  trajectory SHA256 :", r["sha256"])
    print("  timesteps         :", r["steps"])
    print("  observations      :", r["observations"])
    print("  unique vehicles   :", r["unique_vehicles"])

print()

if results[0] == results[1]:
    print("SUMO_TRAJECTORY_REPRODUCIBLE_OK")
else:
    print("SUMO_TRAJECTORY_DIFFERENT")
    sys.exit(1)
