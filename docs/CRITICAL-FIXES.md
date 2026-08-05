# PQ-CBAS-DSH — Critical-Issue Fix Log

## ⚠️ READ FIRST: version mismatch

The `paper_ieee.tex` inside `PQ-CBAS-DSH_artifact-3.zip` is **older** than the
uploaded PDF (`PQ-CBAS-DSH_IEEE-report-kiehtyad.pdf`): ~181 sentences differ.
All edits below were applied to that **older** `.tex`, because no newer `.tex`
was supplied.

Two things follow:

1. The rebuilt PDF may be missing prose revisions present in your newest draft.
2. Some issues I first reported were already fixed in your newest PDF — see
   "Retracted" below.

**Recommended action:** apply the patches below to your *newest* `.tex`, not to
the rebuilt file, then re-run the elsarticle conversion.

---

## Retracted from the earlier review

- **"`60` vs `wc = 49` inconsistency"** and **"`m(γ2−β)` vs `m(γ2+60·2^(d−1))`
  contradiction"** — already corrected in your newest PDF. Withdrawn.

The deeper error below, however, **survives into the newest version**.

---

## CRITICAL #1 — RespCheck is vacuous as written (Theorem 2 / Lemma 7)

### The error

The manuscript states (newest version, Section V-F):

> each valid response satisfies `Az_i − c_i·t_{1,i}·2^d = w_{1,i} + c_i·t_{0,i}`
> (FIPS 204 §3.7) with `‖w_{1,i}‖∞ ≤ γ2`

This relation is incorrect. Deriving from FIPS 204 with `t = A·s1 + s2`,
`t1·2^d = t − t0`, `z = y + c·s1`, `w = A·y`:

```
Az − c·t1·2^d = A(y + c·s1) − c·(A·s1 + s2 − t0)
              = w − c·s2 + c·t0
```

Decomposing `w = 2γ2·w1 + w0` with `‖w0‖∞ ≤ γ2` (HighBits/LowBits):

```
Az − c·t1·2^d = 2γ2·w1 + w0 − c·s2 + c·t0
```

Two discrepancies against the manuscript:

| | manuscript | correct |
|---|---|---|
| high-bits term | `w_{1,i}` | `2γ2·w_{1,i}` (scale factor `2γ2` omitted) |
| secret term | *absent* | `− c_i·s_{2,i}`, norm ≤ `β = wc·η = 196` |

### Why it is fatal, not cosmetic

`w_i = A·y_i` is near-uniform over `R_q^k`. Therefore
`A·z̄ − Σ c_i·t_{1,i}·2^d` has **no non-trivial infinity-norm bound**, and
Equation (45) as written accepts essentially any `z̄`. Obligation O3 is not
discharged, so Theorem 2 / Corollary 3 do not hold.

### Fix applied

`w̄1 = Σ w_{1,i}` is now carried in the aggregate object and subtracted:

```
W̄ = A·z̄ − Σ c_i·t_{1,i}·2^d − 2γ2·w̄1   (mod q)
RespCheck = 1  iff  ‖W̄‖∞ ≤ B_W
B_W = m·(γ2 + β + wc·2^(d−1)) = 462,788·m
```
at ML-DSA-65 (`γ2 = 261,888`, `β = 196`, `wc·2^(d−1) = 200,704`).

Changed: Eq. (31b) added; Eq. (33), (35), (40) now bind `w̄1`; Eq. (44b)–(44g)
rewritten with full derivation; Lemma 7 statement and proof rewritten.

---

## CRITICAL #2 — Module-SIS instance is vacuous for m ≥ 10

Lemma 7's forking extracts a vector of norm ≤ `2·B_W`. Module-SIS is
meaningful only while `2·B_W < q`:

```
m_max = ⌊(q−1) / (2·(γ2+β+wc·2^(d−1)))⌋ = ⌊8380416 / 925576⌋ = 9
```

| m | 2·B_W | vs q = 8,380,417 |
|---|---|---|
| 9 | 8,330,184 | OK |
| 10 | 9,255,760 | **≥ q — trivially solvable** |
| 25 | 23,139,400 | **vacuous** |
| 64 | 59,236,864 | **vacuous** |

The evaluation runs at `t ≈ 18–25` (Tables VIII–IX) and up to `t = 64`
(Table XII). **The compact proof does not cover any evaluated batch size.**

**Fix applied:** Theorem 2, Corollary 3 and Lemma 7 now carry the explicit
hypothesis `m ≤ m_max = 9` (Eq. 44g), stated as necessary rather than
technical. Sub-batching is identified as the only way to invoke the result.

---

## CRITICAL #3 — compact extension yields no size saving in its valid range

`w̄1` costs `k·256 = 1,536 B` at ML-DSA-65 (`k = 6`; coefficients ≤ 15m ≤ 135
for m ≤ 9, so 8 bits each).

| object at m = 9 | size |
|---|---|
| linear aggregate | 5,616 B |
| compact core + `w̄1` | ~6,752 B |
| **difference** | **+1,136 B (compact is larger)** |

The `O(m) → O(1)` claim is asymptotically true but **not realized at ML-DSA-65
within the batch range the security proof covers**. Crossover would occur near
m ≈ 33, well beyond `m_max = 9`.

**Fix applied:** abstract, contributions, discussion, validity boundaries and
conclusion now report this explicitly and reposition PQ-CBAS-DSH-C as an open
design direction, not a demonstrated improvement.

---

## CRITICAL #4 — framing of the aggregate layer

The paper already concedes "cryptographic saving is zero by design" (Table VII)
but the abstract did not. **Fix applied:** abstract now states up front that
verification remains per-signer and the contribution of the aggregate layer is
protocol-level (transcript binding, batch integrity, digest caching).

---

## Summary of edits (15 total)

| # | Location | Change |
|---|---|---|
| C1 | Eq. (31)–(35) | added `w̄1`; bound into `η_norm`, `Agg_C` |
| C2 | `B_m` paragraph | rewritten; concrete costs + admissible range |
| C3 | Eq. (44b)–(44g) | RespCheck rewritten with full FIPS 204 derivation |
| C4 | Theorem 2 | `m ≤ m_max = 9` hypothesis added |
| C5 | Corollary 3 | parameters corrected to `2B_W`; range added |
| C6 | Lemma 7 stmt | corrected bound, `w̄1` argument, range |
| C7 | Lemma 7 proof | rewritten; fork now cancels `w̄1`, `t_1` terms |
| C8 | Abstract | per-signer verification + compact caveats stated |
| C9 | Contributions | asymptotic claim paired with concrete cost |
| C10 | Contributions | "unconditional" → bounded-batch |
| C11 | Section VI | "unconditional" → bounded-batch |
| C12 | Validity boundaries | compactness boundary rewritten |
| C13 | Conclusion | repositioned as open direction |
| C14 | Conclusion | "complete proofs for both" → qualified |
| C15 | Eq. (40) | verifier-side `η'_norm` binds `w̄1` |

---

## Still open (not yet addressed — the "lainnya")

1. Evaluation on MacBook M2, not RSU/OBU-class hardware; E1 cites [31]
   (Cortex-M4) to support an Apple-M2 result.
2. "End-to-end" excludes transport delay and wireless contention; abstract
   disclaimer still weaker than the body.
3. CI95 from 5 seeds (3 for SUMO) — t-distribution correction unstated.
4. `Sort_canon` (basis of Assumption A3) never concretely defined.
5. Comparison against [16]–[21], [24] is lower-bound only.

---

## ⚠️ Verify before submitting

The derivations above were checked symbolically and numerically against
FIPS 204, but they change the security argument of your paper. Please verify
Eq. (44c)–(44g) and the Lemma 7 proof independently before submission.

---

# PART 2 — Non-critical (strict-review) fixes

## Second retraction

- **"E1 cites [31], which measures Cortex-M4 rather than Apple M2."** Wrong.
  Reference [31] is *"ESPM-D: … for Dilithium on ARM Cortex-M4 **and Apple M2**"* —
  it does cover the measurement platform. Withdrawn.
- The valid residue is **generalization**, not citation: "on ARM" spans
  desktop-class Apple silicon (wide NEON) and embedded Cortex-M/R (no wide
  SIMD). Only the former was measured. Fixed by scoping the claim.

## Edits applied (M1–M10)

| # | Issue | Change |
|---|---|---|
| M1 | E1 over-generalized to "ARM" | scoped to *desktop-class Apple-silicon ARM* in abstract + contributions; explicitly not claimed for embedded ARM |
| M2 | transport exclusion under-disclosed in abstract | abstract now states E2E = window wait + verifier processing only; excludes transport, contention, queueing |
| M3 | CI95 method unstated, n small | Student-*t* multipliers stated (t=2.776 at n=5; t=4.303 at n=3); intervals declared indicative; ≥10× seeds recommended |
| M4 | `Sort_canon` undefined (basis of A3) | concrete definition: lexicographic order over fixed-width `Enc(T_i)` = ID(16B) ‖ CertID(32B) ‖ σ(3,309B); prefix-free ⇒ A3 reduces to injectivity of Enc |
| M5 | §VII-H overstated compact saving | rewritten: `w̄1` costs 1,536 B; at m=9 compact ≈6,752 B vs linear 5,616 B; crossover ≈ m=33, outside m_max=9; Fig. 6 flagged as idealized |
| M6 | cross-scheme comparison read as benchmark | explicit: no reimplementation of [16],[18],[24]; Table XIV establishes shared core cost only |
| M7 | measurement host generalization | implementation-validity boundary now names desktop-class host, absent wide SIMD on automotive cores, HSM latency floor; portable claim isolated (window dominates) |
| M8 | side-channel absent from threat table | new row: timing/power leakage, liboqs reference code unaudited → constant-time impl., masking, HSM-resident keys |
| M9 | limitations table stale | 3 rows → 11 rows; adds compact m≤9 bound, compact size regression, compact unimplemented, desktop host, transport exclusion, small seeds, lower-bound comparison |
| M10 | limitations framing | notes that three entries are results of this paper's analysis, not deferred engineering |

## Build

`5p,times` (two-column). Full-width floats kept as `table*`/`figure*`;
Tables IV and XVII set `\scriptsize` to fit. **0 errors, 0 undefined
references, 0 oversized floats, 22 pages.**
