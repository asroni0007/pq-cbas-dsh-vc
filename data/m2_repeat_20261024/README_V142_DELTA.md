# Release v1.4.2: delta from the Apple M2 host (24 October 2026)

Contents
- data/m2_repeat_20261024/buildA_oqs_home_run1..3: repeat of the M2 verification comparison,
  parallel certificate validation and sustained certificate issuance (script m2_ca_cs_extra.py),
  liboqs 0.16.0 source build without OpenSSL (SHA-256 prefix 3a9a78ce6916094e), forced with
  DYLD_LIBRARY_PATH. These runs support Table 9 (build A rows), the parallel-validation speedups
  (S(2) = 1.78, S(4) = 2.6) and the sustained-issuance statement of the manuscript.
- data/m2_repeat_20261024/buildB_homebrew_run1..2: the same script with the Homebrew liboqs 0.16.0
  package (links OpenSSL 4), which liboqs-python loads by default. Table 9, build B rows.
- data/m2_repeat_20261024/bench_original_repeats/r1..r6: six repeats of the paper's unchanged benchmark
  (src/bench_pqcbas.py). r1-r3 used the Homebrew build, r4-r6 build A.
- data/environment_records/m2_20261024/LIBOQS_AND_ENV_RECORD.txt: path, SHA-256, date and linked
  libraries of both liboqs files, and the package versions of the benchmark environment.
- scripts/: the extra M2 measurement script and the summary script. The benchmark itself is src/bench_pqcbas.py in this repository (unchanged, SHA-256 37c53c1f2808969d).

Caveats (also stated in the manuscript)
- The three build-A runs and the two build-B runs used the first version of m2_ca_cs_extra.py, which
  did not log the loaded library. The loaded file was confirmed separately in the same shell setup;
  see the record file.
- The run of 29 September 2026 that underlies Table "ops" did not record the loaded library; its
  build is inferred from the agreement of its timings with the build-A repeats.
- Home-directory paths were replaced by "~" in the copied text files.

Benchmark script SHA-256 (original file): 37c53c1f2808969d61e377a93a49926a3c05428c503fe77c8a3a67a039316074

Note on dates: the Homebrew liboqs file on this host is dated 2026-10-22, after the 29 September run, and the source build (build A) is dated 2026-07-22. The build used on 29 September is therefore inferred, not recorded.
