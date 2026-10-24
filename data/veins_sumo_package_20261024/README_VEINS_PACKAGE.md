# Veins/SUMO reproducibility package (PQ-CBAS-DSH, final 8,694 B PHY/MAC matrix)

Prepared 2026-10-24 from the authors' Mac. Nothing here was changed by a script after the runs.

## Contents
- versions/recovered_20260930: application project used for the final-matrix smoke run of
  30 Sep 2026 (fragmenting PQVehicleApp/PQRSUApp, PQFragmentMessage). Source only, no binaries.
- versions/snapshot_20260930_0508: snapshot taken before the rerun. It is the earlier periodic-BSM
  template without fragmentation, so it cannot have produced the final matrix.
- versions/upload_20260813: source of the 13 Aug 2026 upload (legacy 10,662 B era).
- inputs/matched120_final: the 120 rendered omnetpp.ini and SUMO files, run metadata and matrix.csv.
- evidence/smoke_final_full_8694_s1: logs, ini, metadata and the raw .sca of the 30 Sep smoke run.
- records: hashes of the compiled libraries and of the Veins 5.3.1 toolchain tree (hash only).

## Caveats
- The source hashes in this package were computed on 2026-10-24, not at run time; the run-time hashes were not
  recorded. The compiled libraries are not deposited, only their hashes.
- The project is the recovered version (see versions/). The raw outputs of the 120 final runs are not
  part of this package.
- Generated *_m.cc/*_m.h files are included as found; AppleDouble ._* files are excluded.

## Notes added after assembly
- The raw OMNeT++ result file (evidence/.../p0-4_final_full_8694B_s1.sca) is kept byte-for-byte as produced.
  Its 301 lines of the form "... at /Users/<user>/pqcbas-final-full-8694-smoke-s1//config_pq.xml:2" are
  file-location annotations written by OMNeT++; they contain the author's Mac user name and nothing else.
  In the copied text files (logs, ini, sources) the home directory was replaced by "~".
- SUMO: the launchd log records that the run started ~/pq-sumo-1.22.0-src/bin/sumo (a source build; it reports
  version 1.22.0 in records/BUILD_ENV_AND_LIBRARIES.txt). The log records the path, not a version string at run time.
  The sumo found on PATH (1.27.1) was not the one launched.
