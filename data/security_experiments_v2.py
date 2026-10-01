#!/usr/bin/env python3
"""
security_experiments_v2.py -- implementation-level threat experiments with
independent inputs in every trial (supersedes the security block of
bench_pqcbas.py, whose CCSA and TCSA loops re-evaluated one fixed input).

These are correctness experiments (accept / reject), not timings, so the
results do not depend on the host. Run:  python3 security_experiments_v2.py
Output: security_experiments_v2.json
"""
import hashlib, json, math, platform, secrets, random
import numpy as np
import oqs

ALG = "ML-DSA-65"
TRIALS = 10_000
POOL = 256            # distinct honest signers with distinct keys
KAPPA = 32
H_CERT, H_SIGN, H_AGG = b"PQ-CBAS-DSH/CERT", b"PQ-CBAS-DSH/SIGN", b"PQ-CBAS-DSH/AGG"
rng = random.Random(20260929)

def xof(tag, data, n=KAPPA):
    return hashlib.shake_256(tag + data).digest(n)

def lp(x):                      # length-prefixed field (prefix-free encoding)
    return len(x).to_bytes(4, "big") + x

def mu_cert(ID, pk):
    return xof(H_CERT, lp(ID) + lp(pk) + lp(b"ctx_cert"))

def mu_sign(T):
    return xof(H_SIGN, lp(T["ID"]) + lp(T["m"]) + lp(T["pk"]) + lp(T["gamma"]) + lp(T["fresh"]))

def enc(T):
    return lp(T["ID"]) + lp(T["m"]) + lp(T["pk"]) + lp(T["gamma"]) + lp(T["sigma"]) + lp(T["fresh"])

# ---------------------------------------------------------------- setup
ca = oqs.Signature(ALG); pk_ca = ca.generate_keypair()
signers = []
for _ in range(POOL):
    s = oqs.Signature(ALG); pk = s.generate_keypair(); ID = secrets.token_bytes(16)
    signers.append({"s": s, "pk": pk, "ID": ID, "gamma": ca.sign(mu_cert(ID, pk))})
V = oqs.Signature(ALG)

def fresh_tuple(i=None):
    k = signers[rng.randrange(POOL) if i is None else i]
    T = {"ID": k["ID"], "m": secrets.token_bytes(100), "pk": k["pk"], "gamma": k["gamma"],
         "fresh": secrets.token_bytes(8)}
    T["sigma"] = k["s"].sign(mu_sign(T))
    return T

def verify_tuple(T):
    return V.verify(mu_cert(T["ID"], T["pk"]), T["gamma"], pk_ca) and V.verify(mu_sign(T), T["sigma"], T["pk"])

def aggregate(ts):
    ts = sorted(ts, key=enc)                                   # Sort_canon on full encoding
    return {"tau": xof(H_AGG, b"".join(enc(T) for T in ts)), "ts": ts}

def aggverify(agg, ts):
    if not all(verify_tuple(T) for T in ts):
        return False
    return xof(H_AGG, b"".join(enc(T) for T in sorted(ts, key=enc))) == agg["tau"]

res = {}
# FRA: random byte strings presented as signatures on fresh transcripts
ok = 0
for _ in range(TRIALS):
    T = fresh_tuple(); T["sigma"] = secrets.token_bytes(len(T["sigma"]))
    ok += verify_tuple(T)
res["FRA"] = ok

# TCSA: move one component (sigma, m, fresh, or ID/cert) from an independent tuple j into tuple i
ok = 0; kinds = {"sigma": 0, "m": 0, "fresh": 0, "identity": 0}
for _ in range(TRIALS):
    i, j = rng.sample(range(POOL), 2)
    Ti, Tj = fresh_tuple(i), fresh_tuple(j)
    kind = rng.choice(list(kinds)); kinds[kind] += 1
    if kind == "identity":
        Ti["ID"], Ti["gamma"] = Tj["ID"], Tj["gamma"]
    else:
        Ti[kind] = Tj[kind]
    ok += verify_tuple(Ti)
res["TCSA"] = ok; res["TCSA_component_mix"] = kinds

# CCSA: present a CA certificate signature as an OBU message signature under pk_CA,
# with the message fields chosen to mirror the certificate transcript
ok_dsh = ok_ctrl = 0
for _ in range(TRIALS):
    k = signers[rng.randrange(POOL)]
    x = lp(k["ID"]) + lp(k["pk"]) + lp(b"ctx_cert")
    forged_mu = xof(H_SIGN, x)                     # the transcript an OBU signature would be checked against
    ok_dsh += V.verify(forged_mu, k["gamma"], pk_ca)
    ok_ctrl += V.verify(hashlib.shake_256(x).digest(KAPPA),                       # control: no tags,
                        ca.sign(hashlib.shake_256(x).digest(KAPPA)), pk_ca)       # same encoding
res["CCSA_with_DSH"] = ok_dsh
res["CCSA_control_without_DSH"] = ok_ctrl

# AMA mutation: flip one random byte of the anchor of a fresh random aggregate
ok = 0
for _ in range(TRIALS):
    ts = [fresh_tuple() for _ in range(rng.randint(2, 8))]
    agg = aggregate(ts); b = bytearray(agg["tau"]); b[rng.randrange(len(b))] ^= 1 << rng.randrange(8)
    ok += aggverify({"tau": bytes(b)}, ts)
res["AMA_mutation"] = ok

# AMA substitution: replace a random constituent with an independent valid tuple
ok = 0
for _ in range(TRIALS):
    ts = [fresh_tuple() for _ in range(rng.randint(2, 8))]
    agg = aggregate(ts); ts2 = list(ts); ts2[rng.randrange(len(ts2))] = fresh_tuple()
    ok += aggverify(agg, ts2)
res["AMA_substitution"] = ok

def cp_upper(n, alpha=0.05):     # one-sided Clopper-Pearson upper bound for 0 successes
    return 1 - alpha ** (1 / n)

res.update({"trials": TRIALS, "independent_inputs_per_trial": True,
            "cp95_upper_bound_zero_successes": cp_upper(TRIALS),
            "alg": ALG, "liboqs": oqs.oqs_version(), "liboqs_python": oqs.oqs_python_version(),
            "python": platform.python_version(), "note": "correctness experiment; host-independent"})
json.dump(res, open("security_experiments_v2.json", "w"), indent=1)
print(json.dumps(res, indent=1))
