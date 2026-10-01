PQ-CBAS-DSH PHY/MAC HISTORICAL 120-RUN ARCHIVE
==============================================

Purpose
-------
This archive preserves the processed per-run evidence underlying the
historical SUMO/OMNeT++/Veins PHY/MAC experiment reported in the paper.

Verified design
---------------
Modes:
  small
  digest
  full

Configured density cells:
  10, 25, 50, 100

Matched seeds:
  1 through 10 in every mode-density cell

Total:
  3 modes x 4 cells x 10 seeds = 120 runs

Object representations
----------------------
small:
  payload_bytes = 300
  fragment_count = 1

digest:
  payload_bytes = 3465
  fragment_count = 3

full:
  payload_bytes = 10662
  fragment_count = 9

Important scope boundary
------------------------
The 10,662-byte FULL object is the LEGACY redundant encoding.

The final canonical FULL object used by the current computational
profile is 8,694 bytes and is NOT represented by these historical
PHY/MAC measurements.

Therefore:
  - DIGEST 3,465-byte PHY/MAC measurements apply directly to the
    current final-profile DIGEST representation.
  - FULL 10,662-byte results are retained only as legacy evidence.
  - No final-profile 8,694-byte FULL PDR is claimed from this archive.

Raw simulator-output boundary
-----------------------------
The preserved submission package does not contain the original
OMNeT++ .sca, .vec, or .vci files.

macmetrics_core_results.csv contains the processed per-run dataset
for all 120 runs.

The absence of .sca/.vec means this archive supports verification
and re-analysis of the preserved per-run metrics, but it is not a
complete raw-simulator-output archive.

Future rerun policy
-------------------
Any new final-profile PHY/MAC rerun should preserve:
  - omnetpp.ini and all simulator configuration
  - SUMO/Veins source/configuration
  - .sca/.vec/.vci raw outputs
  - parsed per-run CSV
  - statistical summaries
  - exact software versions
  - SHA-256 manifests

Historical data must not be overwritten by a new rerun.
