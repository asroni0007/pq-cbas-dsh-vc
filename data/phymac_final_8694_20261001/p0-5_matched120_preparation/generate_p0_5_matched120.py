from pathlib import Path
from zipfile import ZipFile
import csv
import hashlib
import json
import math
import re
import shutil

# Local paths: set these to where the legacy raw archive and a scratch directory live.
RAW = Path("final_archive_20260929/PQCBAS_PHYMAC_RAW_120RUN_LEGACY_20260813.zip")

WORK = Path.home() / "pqcbas-p0-5-matched120"
RUNS = WORK / "runs"

PREFIX = "generated_runs_macmetrics_core/"

PAYLOADS = {
    "small": 300,
    "full": 8694,
    "digest": 3465,
}

EXPECTED_FRAGMENTS = {
    "small": 1,
    "full": 8,
    "digest": 3,
}

TARGET_SCALE = {
    10: 0.4,
    25: 1.0,
    50: 2.0,
    100: 4.0,
}

RESULT_EXTENSIONS = {
    ".sca",
    ".vec",
    ".vci",
}

if RUNS.exists():
    shutil.rmtree(RUNS)
RUNS.mkdir(parents=True)

with ZipFile(RAW) as z:
    names = z.namelist()

    ini_entries = sorted(
        n for n in names
        if n.startswith(PREFIX)
        and n.endswith("/omnetpp.ini")
    )

    if len(ini_entries) != 120:
        raise SystemExit(
            f"ERROR: expected 120 historical configs, found {len(ini_entries)}"
        )

    rows = []

    for ordinal, ini_entry in enumerate(ini_entries, start=1):

        old_dir = ini_entry.rsplit("/", 1)[0]
        old_tag = old_dir.split("/")[-1]

        m = re.match(
            r"q(\d+)_([^_]+)_(small|full|digest)_6M_t"
            r"(10|25|50|100)_10Hz_s(10|[1-9])$",
            old_tag,
        )

        if not m:
            raise SystemExit(f"ERROR: unexpected historical tag: {old_tag}")

        qnum = int(m.group(1))
        historical_id = m.group(2)
        variant = m.group(3)
        target = int(m.group(4))
        seed = int(m.group(5))

        if qnum != ordinal:
            raise SystemExit(
                f"ERROR: q ordering mismatch {old_tag}: "
                f"q={qnum}, ordinal={ordinal}"
            )

        new_tag = old_tag
        dst = RUNS / new_tag
        dst.mkdir(parents=True)

        # Copy only input/source-side files from this historical run.
        # Never inherit old .sca/.vec/.vci or completion markers.
        prefix = old_dir + "/"

        for member in names:
            if not member.startswith(prefix):
                continue

            rel = member[len(prefix):]

            if not rel or member.endswith("/"):
                continue

            rp = Path(rel)

            if rp.suffix.lower() in RESULT_EXTENSIONS:
                continue

            if "results" in rp.parts:
                continue

            if rp.name.startswith(".run_"):
                continue

            if rp.suffix.lower() in {".log"}:
                continue

            out = dst / rp
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(member))

        ini = dst / "omnetpp.ini"

        if not ini.exists():
            raise SystemExit(f"ERROR: missing extracted ini: {ini}")

        text = ini.read_text()

        old_payload_match = re.search(
            r"^\*\.node\[\*\]\.appl\.logicalPayloadBytes\s*=\s*(\d+)\s*$",
            text,
            re.M,
        )

        if not old_payload_match:
            raise SystemExit(f"ERROR: payload line missing: {new_tag}")

        old_payload = int(old_payload_match.group(1))

        expected_old = {
            "small": 300,
            "full": 10662,
            "digest": 3465,
        }[variant]

        if old_payload != expected_old:
            raise SystemExit(
                f"ERROR: historical payload mismatch {new_tag}: "
                f"{old_payload} != {expected_old}"
            )

        new_payload = PAYLOADS[variant]

        text = re.sub(
            r"^(\*\.node\[\*\]\.appl\.logicalPayloadBytes\s*=\s*)\d+\s*$",
            rf"\g<1>{new_payload}",
            text,
            flags=re.M,
        )

        # Explicit output paths: required by recovered OMNeT++ runtime.
        text = re.sub(
            r"^result-dir\s*=.*$\n?",
            "",
            text,
            flags=re.M,
        )

        text = re.sub(
            r"^output-scalar-file\s*=.*$\n?",
            "",
            text,
            flags=re.M,
        )

        text = re.sub(
            r"^output-vector-file\s*=.*$\n?",
            "",
            text,
            flags=re.M,
        )

        text = text.rstrip() + f"""

# P0-5 recovered runtime explicit outputs
output-scalar-file = results-explicit/{new_tag}.sca
output-vector-file = results-explicit/{new_tag}.vec
"""

        ini.write_text(text)

        result_dir = dst / "results-explicit"
        result_dir.mkdir()

        metadata = {
            "matrix": "P0-5 matched 120-run final K384",
            "ordinal": ordinal,
            "tag": new_tag,
            "source_historical_tag": old_tag,
            "historical_id": historical_id,
            "variant": variant,
            "logical_payload_bytes": new_payload,
            "fragment_payload_bytes": 1200,
            "fragment_header_bytes": 48,
            "expected_fragments": EXPECTED_FRAGMENTS[variant],
            "phy_mbps": 6,
            "logical_rate_hz": 10,
            "logical_message_interval_s": 0.1,
            "logical_deadline_s": 0.1,
            "reassembly_timeout_s": 0.5,
            "target": target,
            "demand_scale": TARGET_SCALE[target],
            "seed": seed,
            "simulation_time_s": 120,
        }

        (dst / "run_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n"
        )

        rows.append(metadata)

matrix_csv = WORK / "matrix.csv"

fields = [
    "ordinal",
    "tag",
    "variant",
    "logical_payload_bytes",
    "expected_fragments",
    "target",
    "demand_scale",
    "seed",
    "phy_mbps",
    "logical_rate_hz",
    "simulation_time_s",
]

with matrix_csv.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for row in rows:
        writer.writerow({k: row[k] for k in fields})

print(f"Generated {len(rows)} runs")
print(f"Run root: {RUNS}")
print(f"Matrix: {matrix_csv}")
