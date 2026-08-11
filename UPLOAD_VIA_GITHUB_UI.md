# GitHub Web UI Update — v1.1.0 source alignment

Repository: `asroni0007/pq-cbas-dsh-vc`

## Goal
Replace/add the files in this folder without using Terminal/Git CLI.
Do **not** upload the outer `GITHUB_UI_UPDATE_v1.1.0` directory as a nested directory in the repository.
The paths below are paths relative to the repository root.

## Recommended upload order

### A. Replace existing source files
Upload/replace these files in their matching repository folders:

- `src/bench_pqcbas.py`
- `src/e2e_workflow.py`
- `src/sumo_pqcbas_bridge.py`
- `src/transport_budget.py`
- `src/bench_compact.py`
- `src/ci_stats.py`
- `scripts/cek_artefak.sh`
- `scripts/run_bench.sh`
- `scripts/run_rpi.sh`
- `scripts/run_seeds.sh`
- `esp32/PQCBAS_ESP32_Bench/PQCBAS_ESP32_Bench.ino`
- `README.md`

### B. Add new validation/reproducibility files
- `scripts/check_source_alignment.py`
- `experiments/legacy_unvalidated/bench_compact_legacy.py`
- `requirements.txt`
- `CITATION.cff`
- `.zenodo.json`
- `.gitignore`
- `.github/workflows/source-alignment.yml`

## Using GitHub UI
For an existing file:
1. Open the target file in GitHub.
2. Click the pencil icon (Edit this file).
3. Replace all content with the matching file from this bundle.
4. Click **Commit changes...**.

For a new file:
1. In the repository root, choose **Add file > Create new file**.
2. Type the complete path, e.g. `scripts/check_source_alignment.py`.
3. Paste the matching file content.
4. Commit the change.

For groups of non-hidden files you may use **Add file > Upload files** inside the matching folder.
For dotfiles/directories (`.zenodo.json`, `.gitignore`, `.github/...`) use **Create new file** because they can be hidden by Finder.

## Commit message
Use:

`Align source code with manuscript assumptions and reproducibility claims`

Optional description:

`Adds canonical length-delimited Enc_full ordering, duplicate-tuple rejection, explicit digest cache semantics, SUMO one-identity-per-vehicle default, liboqs 0.15.0 pinning, ESP32 n=500, and source-alignment CI checks.`

## After upload
Open GitHub Actions and verify the `Source alignment` workflow passes.
Do not create a new Zenodo version until affected experiments have been rerun and the regenerated result files are committed.
