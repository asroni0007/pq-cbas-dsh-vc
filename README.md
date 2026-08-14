# PQ-CBAS-DSH — Research Artifact

Reproducible source code and measurement artifact for:

> **What Post-Quantum Authentication Costs in a VANET: Measuring ML-DSA-65 Across Device Classes in a Certificate-Based Batched-Verification Framework**

- **Repository:** https://github.com/asroni0007/pq-cbas-dsh-vc
- **Archived artifact DOI:** https://doi.org/10.5281/zenodo.21805963

## Contents

```
src/         measurement code (Python)
esp32/       microcontroller-class OBU benchmark (Arduino IDE)
sumo/        StudyArea network, demand, and SUMO configuration
scripts/     run wrappers and release checks
results/     raw JSON outputs underlying Tables 5-19
docs/        platform guides and revision notes
```

The manuscript source (LaTeX) is not required to run the artifact.

## Requirements

| Component | Version / requirement |
|---|---|
| Python | 3.11+ |
| liboqs | 0.15.0 (pinned for manuscript reproduction) |
| numpy | see `requirements.txt` |
| SUMO | 1.26 (mobility trace) / 1.22.0 (OMNeT++/Veins coupling) |
| OMNeT++ | 6.1 |
| Veins | 5.3.1 |
| ESP32 toolchain | ESP-IDF v5.5.5 (PQClean reference ML-DSA-65) |

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Reproducing the results

```bash
# Operation-level benchmarks (Table 5), microcontroller benchmark (Table 6)
python3 scripts/run_operation_benchmarks.py

# Aggregation behavior and overhead (Tables 7-8)
python3 scripts/run_aggregation_benchmarks.py

# End-to-end latency, uniform arrivals and SUMO trace (Tables 9-12)
python3 scripts/run_e2e_latency.py

# Security-oriented experiments: CCSA, FRA, TCSA, AMA (Table 17-18)
python3 scripts/run_security_experiments.py

# Transport-inclusive confirmatory evaluation, 120-run matrix (Table 19)
python3 scripts/run_mac_confirmatory.py
```

All reported values in the manuscript can be regenerated from these scripts.
Confidence intervals use a Student-t multiplier at df = n-1 throughout.

## Verifying integrity

```bash
sha256sum -c SHA256SUMS.txt
```

## Citation

If you use this artifact, please cite the manuscript (see `CITATION.cff`).

## License

See `LICENSE`.
