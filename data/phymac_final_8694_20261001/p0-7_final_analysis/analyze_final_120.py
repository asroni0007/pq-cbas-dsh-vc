from pathlib import Path
from collections import defaultdict
import csv
import json
import math
import re
import statistics
import sys

RAW = Path(
    "/Volumes/Ext_White/pq-cbas-dsh-vc-65B7/"
    "rerun/final_k384/phymac_final_8694/"
    "p0-5_matched120/raw_runs"
)

OUT = Path(
    "/Volumes/Ext_White/pq-cbas-dsh-vc-65B7/"
    "rerun/final_k384/phymac_final_8694/"
    "p0-7_final_analysis"
)

OUT.mkdir(parents=True, exist_ok=True)

scalar_re = re.compile(
    r'^scalar\s+(\S+)\s+(\S+)\s+(.+?)\s*$'
)

counter_names = {
    "generatedLogicalInRsuCoverage",
    "generatedFragmentsInRsuCoverage",
    "receivedFragmentsInCoverage",
    "receivedFragmentsInRsuCoverage",
    "duplicateFragments",
    "malformedFragments",
    "completedLogicalMessages",
    "completedBeforeDeadline",
    "completedAfterDeadline",
    "reassemblyTimeouts",
}

mac_names = {
    "MacQueueDelaySamples",
    "MacQueueDelayMeanMs",
    "MacQueueDelayMaxMs",
    "MacQueueLengthAtEnqueueSamples",
    "MacQueueLengthAtEnqueueMean",
    "MacQueueLengthAtEnqueueMax",
}

expected = {
    "small":  {"payload": 300,  "fragments": 1},
    "digest": {"payload": 3465, "fragments": 3},
    "full":   {"payload": 8694, "fragments": 8},
}

errors = []
rows = []


def rate(a, b):
    if b == 0:
        return float("nan")
    return a / b


def weighted_mean(means, samples):
    mean_map = dict(means)
    sample_map = dict(samples)

    num = 0.0
    den = 0.0

    for module, m in mean_map.items():
        n = sample_map.get(module, 0.0)

        if n > 0:
            num += m * n
            den += n

    return num / den if den else float("nan")


dirs = sorted(
    p for p in RAW.iterdir()
    if p.is_dir()
)

if len(dirs) != 120:
    raise SystemExit(
        f"ERROR: expected 120 runs, found {len(dirs)}"
    )

for d in dirs:

    tag = d.name
    meta_file = d / "run_metadata.json"
    sca_file = d / f"{tag}.sca"

    if not meta_file.exists():
        errors.append(f"{tag}: metadata missing")
        continue

    if not sca_file.exists():
        errors.append(f"{tag}: SCA missing")
        continue

    meta = json.loads(meta_file.read_text())

    variant = meta["variant"]
    target = int(meta["target"])
    seed = int(meta["seed"])

    vals = defaultdict(list)

    with sca_file.open(
        "r",
        errors="replace"
    ) as f:

        for line in f:
            m = scalar_re.match(line)

            if not m:
                continue

            module, name, raw = m.groups()

            if name not in counter_names and name not in mac_names:
                continue

            try:
                value = float(raw)
            except ValueError:
                continue

            vals[name].append(
                (module, value)
            )

    sums = {
        name: sum(
            value for _, value
            in vals.get(name, [])
        )
        for name in counter_names
    }

    generated_logical = sums[
        "generatedLogicalInRsuCoverage"
    ]

    generated_fragments = sums[
        "generatedFragmentsInRsuCoverage"
    ]

    completed = sums[
        "completedLogicalMessages"
    ]

    before = sums[
        "completedBeforeDeadline"
    ]

    after = sums[
        "completedAfterDeadline"
    ]

    timeouts = sums[
        "reassemblyTimeouts"
    ]

    duplicates = sums[
        "duplicateFragments"
    ]

    malformed = sums[
        "malformedFragments"
    ]

    if vals.get(
        "receivedFragmentsInRsuCoverage"
    ):
        received_fragments = sums[
            "receivedFragmentsInRsuCoverage"
        ]
        received_metric = (
            "receivedFragmentsInRsuCoverage"
        )
    else:
        received_fragments = sums[
            "receivedFragmentsInCoverage"
        ]
        received_metric = (
            "receivedFragmentsInCoverage"
        )

    if generated_logical <= 0:
        errors.append(
            f"{tag}: generated logical <= 0"
        )
        frag_ratio = float("nan")
    else:
        frag_ratio = (
            generated_fragments /
            generated_logical
        )

    exp_frag = expected[
        variant
    ]["fragments"]

    if not math.isnan(frag_ratio):
        if abs(
            frag_ratio - exp_frag
        ) > 1e-12:
            errors.append(
                f"{tag}: fragment ratio "
                f"{frag_ratio:.9f} != "
                f"{exp_frag}"
            )

    if abs(
        completed - (before + after)
    ) > 1e-12:
        errors.append(
            f"{tag}: completed != before + after"
        )

    qdelay_samples = sum(
        value for _, value
        in vals.get(
            "MacQueueDelaySamples", []
        )
    )

    qdelay_mean = weighted_mean(
        vals.get(
            "MacQueueDelayMeanMs", []
        ),
        vals.get(
            "MacQueueDelaySamples", []
        ),
    )

    qdelay_max_values = [
        value for _, value
        in vals.get(
            "MacQueueDelayMaxMs", []
        )
    ]

    qdelay_max = (
        max(qdelay_max_values)
        if qdelay_max_values
        else float("nan")
    )

    qlen_samples = sum(
        value for _, value
        in vals.get(
            "MacQueueLengthAtEnqueueSamples",
            []
        )
    )

    qlen_mean = weighted_mean(
        vals.get(
            "MacQueueLengthAtEnqueueMean",
            []
        ),
        vals.get(
            "MacQueueLengthAtEnqueueSamples",
            []
        ),
    )

    qlen_max_values = [
        value for _, value
        in vals.get(
            "MacQueueLengthAtEnqueueMax", []
        )
    ]

    qlen_max = (
        max(qlen_max_values)
        if qlen_max_values
        else float("nan")
    )

    rows.append({
        "tag": tag,
        "variant": variant,
        "target": target,
        "seed": seed,

        "payload_bytes":
            meta["logical_payload_bytes"],

        "expected_fragments":
            meta["expected_fragments"],

        "observed_fragment_ratio":
            frag_ratio,

        "generated_logical":
            generated_logical,

        "generated_fragments":
            generated_fragments,

        "received_fragments":
            received_fragments,

        "received_fragment_metric":
            received_metric,

        "completed_logical":
            completed,

        "completed_before_deadline":
            before,

        "completed_after_deadline":
            after,

        "reassembly_timeouts":
            timeouts,

        "duplicate_fragments":
            duplicates,

        "malformed_fragments":
            malformed,

        "logical_completion_rate":
            rate(
                completed,
                generated_logical
            ),

        "on_time_completion_rate":
            rate(
                before,
                generated_logical
            ),

        "late_completion_rate":
            rate(
                after,
                generated_logical
            ),

        "reassembly_timeout_per_generated":
            rate(
                timeouts,
                generated_logical
            ),

        "fragment_reception_rate":
            rate(
                received_fragments,
                generated_fragments
            ),

        "mac_queue_delay_samples":
            qdelay_samples,

        "mac_queue_delay_mean_ms":
            qdelay_mean,

        "mac_queue_delay_max_ms":
            qdelay_max,

        "mac_queue_length_samples":
            qlen_samples,

        "mac_queue_length_mean":
            qlen_mean,

        "mac_queue_length_max":
            qlen_max,
    })


if errors:
    print(
        f"❌ EXTRACTION FAILED: "
        f"{len(errors)} issue(s)"
    )

    for e in errors[:100]:
        print(" -", e)

    sys.exit(1)


order = {
    "small": 0,
    "digest": 1,
    "full": 2,
}

rows.sort(
    key=lambda r: (
        order[r["variant"]],
        r["target"],
        r["seed"],
    )
)


# -------------------------------------------------
# PER-RUN CSV
# -------------------------------------------------

run_csv = OUT / "P0-7_FINAL_120_RUNS.csv"

with run_csv.open(
    "w",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(rows[0].keys())
    )

    writer.writeheader()
    writer.writerows(rows)


# -------------------------------------------------
# 12-CELL SUMMARY
# -------------------------------------------------

groups = defaultdict(list)

for r in rows:
    groups[
        (
            r["variant"],
            r["target"]
        )
    ].append(r)


metrics = [
    "logical_completion_rate",
    "on_time_completion_rate",
    "late_completion_rate",
    "reassembly_timeout_per_generated",
    "fragment_reception_rate",
    "mac_queue_delay_mean_ms",
    "mac_queue_delay_max_ms",
    "mac_queue_length_mean",
    "mac_queue_length_max",
]


def clean(xs):
    return [
        x for x in xs
        if not math.isnan(x)
    ]


summary = []

for variant in (
    "small",
    "digest",
    "full",
):

    for target in (
        10,
        25,
        50,
        100,
    ):

        g = groups[
            (
                variant,
                target
            )
        ]

        if len(g) != 10:
            raise SystemExit(
                f"ERROR: {variant}/"
                f"{target} has {len(g)} runs"
            )

        out = {
            "variant": variant,
            "target": target,
            "n_seeds": 10,
            "payload_bytes":
                expected[variant]["payload"],
            "fragments":
                expected[variant]["fragments"],
        }

        for metric in metrics:

            xs = clean([
                float(r[metric])
                for r in g
            ])

            out[
                f"{metric}_mean"
            ] = statistics.mean(xs)

            out[
                f"{metric}_sd"
            ] = (
                statistics.stdev(xs)
                if len(xs) > 1
                else float("nan")
            )

            out[
                f"{metric}_min"
            ] = min(xs)

            out[
                f"{metric}_max"
            ] = max(xs)

        summary.append(out)


summary_csv = (
    OUT /
    "P0-7_FINAL_12_CELL_SUMMARY.csv"
)

with summary_csv.open(
    "w",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(summary)


# -------------------------------------------------
# COMPACT PAPER TABLE
# -------------------------------------------------

compact_fields = [
    "variant",
    "target",
    "payload_bytes",
    "fragments",

    "logical_completion_rate_mean",
    "logical_completion_rate_sd",

    "on_time_completion_rate_mean",
    "on_time_completion_rate_sd",

    "reassembly_timeout_per_generated_mean",
    "reassembly_timeout_per_generated_sd",

    "fragment_reception_rate_mean",
    "fragment_reception_rate_sd",

    "mac_queue_delay_mean_ms_mean",
    "mac_queue_delay_mean_ms_sd",

    "mac_queue_delay_max_ms_mean",

    "mac_queue_length_mean_mean",
    "mac_queue_length_mean_sd",

    "mac_queue_length_max_mean",
]

compact_csv = (
    OUT /
    "P0-7_PAPER_COMPACT_TABLE.csv"
)

with compact_csv.open(
    "w",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=compact_fields
    )

    writer.writeheader()

    for row in summary:
        writer.writerow({
            k: row[k]
            for k in compact_fields
        })


audit = (
    OUT /
    "P0-7_EXTRACTION_AUDIT.txt"
)

audit.write_text(
    "P0-7 FINAL PHY/MAC EXTRACTION\n"
    "=============================\n"
    f"Runs parsed: {len(rows)}\n"
    f"Cells summarized: {len(summary)}\n"
    "small=300B/1 fragment\n"
    "digest=3465B/3 fragments\n"
    "full=8694B/8 fragments\n\n"
    "Rates use generatedLogicalInRsuCoverage "
    "as denominator unless stated otherwise.\n"
    "MAC queue means are weighted by "
    "per-module sample counts.\n"
    "No causal interpretation is made "
    "at this extraction stage.\n"
)

print(
    "========================================"
)
print(
    "P0-7 EXTRACTION COMPLETE"
)
print(
    "========================================"
)
print("Runs parsed      =", len(rows))
print(
    "Cells summarized =",
    len(summary)
)
print()
print("✅ P0-7 EXTRACTION PASS")
print()
print(run_csv)
print(summary_csv)
print(compact_csv)
