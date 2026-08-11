# PQ-CBAS-DSH — Research Artifact

Reproducible source code and measurement artifact for:

> **What Post-Quantum Authentication Costs in a VANET: Measuring ML-DSA-65 Across Device Classes in a Certificate-Based Batched-Verification Framework**

Repository: `https://github.com/asroni0007/pq-cbas-dsh-vc`

Archived artifact DOI: `https://doi.org/10.5281/zenodo.21805963`

## Source-alignment status

This snapshot aligns the implementation with the revised manuscript assumptions and release evidence. The release gate is:

```bash
python3 scripts/check_source_alignment.py
```

A passing release prints `SOURCE_ALIGNMENT_OK`.

The alignment changes are scientifically relevant: canonical aggregate encoding/order, certificate-digest wire semantics, SUMO crypto-identity handling, and release script paths have been corrected. Therefore the JSON files already present in `results/` must be treated as **historical reported outputs** until the affected experiments are rerun with this source-aligned snapshot. See `RESULTS_NEED_RERUN_AFTER_ALIGNMENT.md`.

## Contents

```text
src/        measurement code (Python)
esp32/      microcontroller-class OBU benchmark (Arduino IDE)
sumo/       StudyArea network, demand, and SUMO configuration
scripts/    run wrappers and release checks
results/    historical/reported JSON outputs
experiments/legacy_unvalidated/
            quarantined compact-extension exploratory code; not paper evidence
docs/       platform guides and revision notes
```

The manuscript source is not required to run the artifact.

## Requirements

| Component | Version / requirement |
|---|---|
| Python | 3.11+ |
| liboqs | **0.15.0**, pinned for manuscript reproduction |
| Python packages | `liboqs-python`, `numpy`, `cryptography` |
| SUMO | 1.26 headless traces / 1.27 visualization used in the study |
| ESP32 (optional) | Arduino IDE 2.x + ESP32 core 3.3.x |

The release scripts pin liboqs 0.15.0 because later liboqs releases may change the default ML-DSA implementation and therefore absolute timing. `cryptography` is required for the ECDSA-P256 E1 baseline.

## Quick start

```bash
# Source-only release checks (no liboqs required)
python3 scripts/check_source_alignment.py
bash scripts/cek_artefak.sh

# Build/pin dependencies and run operation benchmarks
bash scripts/run_bench.sh
source venv/bin/activate

# Operation/aggregation/security experiments
OQS_INSTALL_PATH="$HOME/oqs-0.15.0" python3 src/bench_pqcbas.py | tee results/bench.log

# Transport-excluded authentication-pipeline workflow, 20 seeds, W=90 ms
bash scripts/run_seeds.sh 20 90

# SUMO-FCD workflow, full-certificate mode
OQS_INSTALL_PATH="$HOME/oqs-0.15.0" python3 src/sumo_pqcbas_bridge.py \
  --window 90 --seeds 20 \
  --cfg sumo/studyarea_test.sumocfg \
  --net sumo/StudyAreNetwork.net.xml \
  --fcd studyarea_fcd.xml

# SUMO-FCD steady-state certificate-digest mode.
# --digest-cache-model warm means the first valid full-certificate attach is
# prevalidated outside the timed window; the timed record carries CertID only.
OQS_INSTALL_PATH="$HOME/oqs-0.15.0" python3 src/sumo_pqcbas_bridge.py \
  --window 90 --seeds 20 --no-sumo --digest \
  --digest-cache-model warm --n-obus 0 \
  --fcd studyarea_fcd.xml

# Analytic transport budget; this does not establish transport-inclusive feasibility
python3 src/transport_budget.py --latex
```

## Manuscript-to-code traceability

| Manuscript evidence | Source | Scope |
|---|---|---|
| E1 operation timing + ECDSA-P256 baseline | `src/bench_pqcbas.py` | desktop cryptographic timing |
| E2 domain-hash overhead | `src/bench_pqcbas.py`, ESP32 sketch | protocol-overhead timing |
| Aggregate construction / AggCheck | `src/bench_pqcbas.py` | canonical full-tuple transcript; per-signer verification remains |
| E3 synthetic workflow | `src/e2e_workflow.py`, `src/ci_stats.py` | transport-excluded verifier batch path |
| E3 SUMO-FCD workflow | `src/sumo_pqcbas_bridge.py`, `src/ci_stats.py` | arrival/mobility scheduling; transport delay set to zero |
| Analytic transmission budget | `src/transport_budget.py` | sensitivity/boundary analysis, not PHY/MAC proof |
| E4 microcontroller tail latency | `esp32/PQCBAS_ESP32_Bench/PQCBAS_ESP32_Bench.ino` | `N_SIGN=500` release default |
| Compact response-sum extension | manuscript analysis only | **not a validated implementation** |

### Figures

The repository contains the data-generating code and the SUMO network asset. Manuscript figure composition/plotting is not claimed to be performed by `bench_pqcbas.py`; figures should be regenerated from the corresponding result JSON or manuscript plotting workflow.

## A3 canonical transcript implementation

The aggregate transcript uses a shared `enc_full(T)` encoder in both aggregation and verification. Variable-length fields use fixed-width unsigned length prefixes, the ML-DSA-65 signature is fixed at 3309 bytes, freshness is fixed at 8 bytes, tuples are lexicographically ordered by the resulting full encoding, and duplicate canonical tuples are rejected.

`ser_tuple()` remains only for wire-size accounting and must not be used as the aggregate security transcript.

## Certificate-digest semantics

Two distinct cases are explicit in the source:

- **Synthetic workflow:** first valid contact carries the full certificate; subsequent messages carry `CertID` and resolve the cached public key/certificate.
- **SUMO steady-state digest workflow:** `--digest-cache-model warm` models the timed message after a valid first attach has already populated the cache. `--digest-cache-model cold` measures the first full-certificate attach.

Digest records do not carry the full certificate/public key in the corrected implementation. SUMO defaults to `--n-obus 0`, i.e. one unique crypto identity per FCD vehicle; any smaller identity pool must be requested explicitly and reported.

## What “latency” means here

The E3 workflow measures **transport-excluded authentication-pipeline latency conditional on delivery to the verifier**. It does not include PHY/MAC contention, queuing, packet loss, or application-message fragmentation. The packet-level Veins/OMNeT++/SUMO work is a separate confirmatory layer.

The workflow performs timed per-signer certificate/signature checks over collection-window batches. Aggregate construction and AggCheck costs are benchmarked separately; the E3 workflow must not be described as a transport-inclusive or cryptographically compressed batch-verification result.

## Confidence intervals

`src/ci_stats.py` computes across-seed 95% confidence intervals using a Student-*t* multiplier at `df=n-1`.

```bash
python3 src/ci_stats.py
```

## ESP32 benchmark

The microcontroller-class measurement uses the PQClean portable implementation of ML-DSA-65. The source-aligned release default is:

```cpp
#define N_SIGN 500
```

Run instructions are in `docs/ARDUINO_GUIDE.md`. The archived summary is `results/esp32_n500_summary.json`.

## Compact extension boundary

`src/bench_compact.py` is intentionally a non-executable guard/stub. The former exploratory implementation is retained under `experiments/legacy_unvalidated/` for provenance only and is **not evidence for the paper**. The compact extension remains an analytical, scoped/negative result unless a standards-faithful implementation is separately validated.

## Results and reruns

Absolute timings are platform-dependent. More importantly, some source-alignment changes modify the semantics of the transcript or digest workflow. Do not overwrite the historical JSON blindly. Write new outputs to a new release/results directory, compare them, update manuscript tables/figures if needed, and only then tag the GitHub/Zenodo release.

See:

```text
RESULTS_NEED_RERUN_AFTER_ALIGNMENT.md
SOURCE_ALIGNMENT_REPORT.md
```

## Reproducibility notes

- Do not reproduce manuscript timings against an unpinned newest liboqs checkout.
- Do not build with architecture-specific options unless the experiment is explicitly reported as optimized; the manuscript comparison uses a common reference-oriented profile.
- Benchmarks are single-threaded unless a script states otherwise.
- On Linux/Raspberry Pi, verify CPU governor and thermal headroom before interpreting absolute timings.

## License

Code (`src/`, `scripts/`, `esp32/`): MIT License (see `LICENSE`). Result/manuscript data should retain the licensing terms stated in the archived artifact. Third-party components retain their own licenses.

## Continuous source gate

GitHub Actions runs `.github/workflows/source-alignment.yml` on pushes and pull requests. It performs Python syntax checks, shell syntax checks, and the dependency-light manuscript/source alignment gate. Heavy cryptographic timing runs remain manual because benchmark hardware and thermal conditions are part of the experimental control.

Zenodo-compatible metadata is provided in `.zenodo.json`; citation metadata is provided in `CITATION.cff`.
