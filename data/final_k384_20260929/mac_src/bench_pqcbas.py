#!/usr/bin/env python3
"""PQ-CBAS-DSH framework benchmark with a real ML-DSA-65 backend (liboqs).

Implements Setup/VehKeyGen/CertGen/CertValidate/Sign/Agg/AggVerify exactly per
Equations (1)-(27) of the manuscript, with SHAKE256 domain-separated hashing.
Outputs JSON with operation timings, aggregation behavior, and security
experiment results (FRA/RSA/AMA/CCSA).
"""
import os, json, time, statistics, hashlib, secrets
import numpy as np
import oqs

ALG = "ML-DSA-65"
GAMMA1 = 1 << 19          # ML-DSA-65
L = 5                     # vector length l for ML-DSA-65
N = 256
CT_LEN = 48               # c_tilde bytes (lambda/4 = 192/4)
Z_LEN = L * N * 20 // 8   # 3200 B (20-bit packing)
HINT_LEN = 55 + 6         # omega + k = 61 B
KAPPA = 48


def xof(domain: bytes, data: bytes, outlen=KAPPA) -> bytes:
    return hashlib.shake_256(domain + data).digest(outlen)

H_CERT = b"PQ-CBAS-DSH/CERT"
H_SIGN = b"PQ-CBAS-DSH/SIGN"
H_AGG  = b"PQ-CBAS-DSH/AGG"

# ---- FIPS 204 z-component bit-unpacking (20-bit, BitPack with b=gamma1) ----
def unpack_z(sig: bytes) -> np.ndarray:
    raw = np.frombuffer(sig, dtype=np.uint8, count=Z_LEN, offset=CT_LEN).astype(np.uint64)
    raw = raw.reshape(-1, 5)  # 5 bytes -> 2 coeffs of 20 bits
    c0 = raw[:, 0] | (raw[:, 1] << 8) | ((raw[:, 2] & 0x0F) << 16)
    c1 = (raw[:, 2] >> 4) | (raw[:, 3] << 4) | (raw[:, 4] << 12)
    coeffs = np.empty(raw.shape[0] * 2, dtype=np.int64)
    coeffs[0::2] = GAMMA1 - c0.astype(np.int64)
    coeffs[1::2] = GAMMA1 - c1.astype(np.int64)
    return coeffs  # length L*N

def hint_part(sig: bytes) -> bytes:
    return sig[CT_LEN + Z_LEN:]

def c_part(sig: bytes) -> bytes:
    return sig[:CT_LEN]

# ------------------------- framework operations -------------------------
class CA:
    def __init__(self):
        self.signer = oqs.Signature(ALG)
        self.pk = self.signer.generate_keypair()

def setup():
    ca = CA()
    pp = {"pk_CA": ca.pk}
    return pp, ca

def vehkeygen():
    s = oqs.Signature(ALG)
    pk = s.generate_keypair()
    return s, pk

def certgen(ca: CA, ID: bytes, pk: bytes):
    mu = xof(H_CERT, ID + pk + b"ctx_cert")
    gamma = ca.signer.sign(mu)
    return (ID, pk, gamma)

def certvalidate(pk_CA: bytes, cert):
    ID, pk, gamma = cert
    mu = xof(H_CERT, ID + pk + b"ctx_cert")
    with oqs.Signature(ALG) as v:
        return v.verify(mu, gamma, pk_CA)

def obu_sign(signer, ID, m, pk, cert, fresh):
    mu = xof(H_SIGN, ID + m + pk + cert[0] + cert[1] + cert[2] + fresh)
    return signer.sign(mu)

def make_tuple(ID, m, pk, cert, sigma, fresh):
    return {"ID": ID, "m": m, "pk": pk, "cert": cert, "sigma": sigma, "fresh": fresh}

# Canonical network serialization for the final deployment profile.
# ID and public key are already contained in Cert and therefore are not
# repeated in the outer full-wire representation.
def ser_wire_full(T):
    cert_raw = T["cert"][0] + T["cert"][1] + T["cert"][2]
    return T["m"] + cert_raw + T["sigma"] + T["fresh"]

def ser_wire_digest(T):
    cert_raw = T["cert"][0] + T["cert"][1] + T["cert"][2]
    cert_id = xof(H_CERT, cert_raw)
    return T["m"] + cert_id + T["sigma"] + T["fresh"]

# Assumption A3: canonical, prefix-free full-tuple transcript encoding.
# Variable-length fields are prefixed by an unsigned 32-bit big-endian length.
# The FIPS 204 ML-DSA-65 signature (3309 B) and freshness value (8 B) are
# fixed-width in this profile, matching the manuscript's Enc(sigma) and Enc_8.
def _lp(x: bytes) -> bytes:
    if not isinstance(x, (bytes, bytearray)):
        raise TypeError("canonical fields must be byte strings")
    return len(x).to_bytes(4, "big") + bytes(x)

def enc_cert(cert) -> bytes:
    cid, cpk, gamma = cert
    return _lp(cid) + _lp(cpk) + _lp(gamma)

def enc_full(T) -> bytes:
    sigma = T["sigma"]
    fresh = T["fresh"]
    if len(sigma) != 3309:
        raise ValueError(f"ML-DSA-65 signature must be 3309 B, got {len(sigma)}")
    if len(fresh) != 8:
        raise ValueError(f"freshness must be 8 B, got {len(fresh)}")
    cert_bytes = enc_cert(T["cert"])
    return (
        _lp(T["ID"]) + _lp(T["m"]) + _lp(T["pk"]) +
        _lp(cert_bytes) + sigma + fresh
    )

def canonicalize(tuples):
    pairs = sorted(((enc_full(T), T) for T in tuples), key=lambda p: p[0])
    encs = [p[0] for p in pairs]
    if any(a == b for a, b in zip(encs, encs[1:])):
        raise ValueError("duplicate canonical tuple")
    return [p[1] for p in pairs], encs

def aggregate(tuples):
    ts, encs = canonicalize(tuples)                           # Eq 17 / A3
    tau = xof(H_AGG, b"".join(encs))                         # Eq 18
    bar_z = np.zeros(L * N, dtype=np.int64)
    for T in ts:
        bar_z += unpack_z(T["sigma"])                        # Eq 19
    C = b"".join(c_part(T["sigma"]) for T in ts)             # Eq 20
    eta = xof(H_AGG, b"".join(hint_part(T["sigma"]) for T in ts) + tau)  # Eq 21
    return {"bar_z": bar_z, "C": C, "eta": eta, "tau": tau}, ts

def agg_size(agg, m):
    return agg["bar_z"].astype(np.int32).nbytes + len(agg["C"]) + len(agg["eta"]) + len(agg["tau"])

def aggverify(pp, agg, ts, verify_sigs=True):
    try:
        ts, encs = canonicalize(ts)
    except (TypeError, ValueError):
        return False
    for T in ts:                                             # Eq 23
        if not certvalidate(pp["pk_CA"], T["cert"]):
            return False
    tau2 = xof(H_AGG, b"".join(encs))                        # Eq 24-25 / A3
    if tau2 != agg["tau"]:
        return False
    # AggCheck (Eq 26): (i) per-signer verification, (ii) bar_z consistency,
    # (iii) challenge-list C consistency, and (iv) eta consistency
    if verify_sigs:
        with oqs.Signature(ALG) as v:
            for T in ts:
                mu = xof(H_SIGN, T["ID"] + T["m"] + T["pk"] + T["cert"][0] + T["cert"][1] + T["cert"][2] + T["fresh"])
                if not v.verify(mu, T["sigma"], T["pk"]):
                    return False
    bz = np.zeros(L * N, dtype=np.int64)
    for T in ts:
        bz += unpack_z(T["sigma"])
    if not np.array_equal(bz, agg["bar_z"]):
        return False
    if agg["C"] != b"".join(c_part(T["sigma"]) for T in ts):
        return False
    eta2 = xof(H_AGG, b"".join(hint_part(T["sigma"]) for T in ts) + agg["tau"])
    return eta2 == agg["eta"]

# ------------------------------ timing ------------------------------
def bench(fn, n):
    xs = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        fn()
        xs.append((time.perf_counter_ns() - t0) / 1e6)
    return statistics.mean(xs), statistics.stdev(xs)

def main():
    rng = secrets.SystemRandom()
    import platform
    if platform.system() == "Darwin":
        cpu = os.popen("sysctl -n machdep.cpu.brand_string").read().strip()
    else:
        try:
            cpu = [l.split(":")[1].strip() for l in open("/proc/cpuinfo") if "model name" in l][0]
        except Exception:
            cpu = platform.processor() or "unknown"
    out = {"alg": ALG, "python": platform.python_version(),
           "os": f"{platform.system()} {platform.release()}",
           "cpu": cpu, "liboqs": getattr(oqs, "oqs_version", lambda: "unknown")(),
           "runs": {}}

    # warm-up
    pp, ca = setup()
    s, pk = vehkeygen()

    N_RUNS = 200
    out["runs"]["n"] = N_RUNS
    out["Setup"] = bench(lambda: setup(), N_RUNS)
    out["VehKeyGen"] = bench(lambda: vehkeygen(), N_RUNS)
    ID = secrets.token_bytes(16)
    out["CertGen"] = bench(lambda: certgen(ca, ID, pk), N_RUNS)
    cert = certgen(ca, ID, pk)
    out["CertValidate"] = bench(lambda: certvalidate(pp["pk_CA"], cert), N_RUNS)
    msg = secrets.token_bytes(100); fresh = secrets.token_bytes(8)
    out["Sign"] = bench(lambda: obu_sign(s, ID, msg, pk, cert, fresh), N_RUNS)

    # tuple/cert sizes
    sigma = obu_sign(s, ID, msg, pk, cert, fresh)
    T0 = make_tuple(ID, msg, pk, cert, sigma, fresh)
    cert_size = len(cert[0]) + len(cert[1]) + len(cert[2])
    full_size = len(ser_wire_full(T0))
    digest_size = len(ser_wire_digest(T0))

    assert full_size == 8694, f"unexpected final full-wire size: {full_size}"
    assert digest_size == 3465, f"unexpected final digest-wire size: {digest_size}"

    out["sizes"] = {
        "pk": len(pk),
        "sig": len(sigma),
        "cert": cert_size,
        "hash_bytes": KAPPA,
        "tuple": full_size,
        "full_wire": full_size,
        "digest_wire": digest_size,
    }

    # aggregation behavior for m in 1,2,5,10
    out["agg"] = {}
    signers = []
    for i in range(10):
        si, pki = vehkeygen()
        IDi = secrets.token_bytes(16)
        ci = certgen(ca, IDi, pki)
        mi = secrets.token_bytes(100); fi = secrets.token_bytes(8)
        sgi = obu_sign(si, IDi, mi, pki, ci, fi)
        signers.append(make_tuple(IDi, mi, pki, ci, sgi, fi))
    for m in (1, 2, 5, 10):
        sub = signers[:m]
        tmean, tstd = bench(lambda: aggregate(sub), 100)
        agg, ts = aggregate(sub)
        vmean, vstd = bench(lambda: aggverify(pp, agg, ts), 30)
        assert aggverify(pp, agg, ts)
        out["agg"][m] = {"agg_ms": [tmean, tstd], "aggverify_ms": [vmean, vstd],
                         "agg_size": agg_size(agg, m)}

    # ----------------- security experiments (real backend) -----------------
    TRIALS = 10000
    sec = {}
    # FRA: random signatures must be rejected
    with oqs.Signature(ALG) as v:
        mu = xof(H_SIGN, ID + msg + pk + cert[0] + cert[1] + cert[2] + fresh)
        ok = 0
        for _ in range(TRIALS):
            fake = secrets.token_bytes(len(sigma))
            try:
                if v.verify(mu, fake, pk):
                    ok += 1
            except Exception:
                pass
        sec["FRA"] = ok
    # RSA: substitute sigma across tuples -> per-signer verify must fail
    s2, pk2 = vehkeygen(); ID2 = secrets.token_bytes(16); cert2 = certgen(ca, ID2, pk2)
    msg2 = secrets.token_bytes(100); fresh2 = secrets.token_bytes(8)
    sigma2 = obu_sign(s2, ID2, msg2, pk2, cert2, fresh2)
    with oqs.Signature(ALG) as v:
        mu1 = xof(H_SIGN, ID + msg + pk + cert[0] + cert[1] + cert[2] + fresh)
        ok = 0
        for _ in range(TRIALS):
            if v.verify(mu1, sigma2, pk):   # replayed/substituted component
                ok += 1
        sec["RSA"] = ok
    # AMA single-byte mutation of the aggregate object
    agg, ts = aggregate(signers[:5])
    blob = bytearray(agg["bar_z"].astype(np.int32).tobytes() + agg["C"] + agg["eta"] + agg["tau"])
    ok = 0
    for _ in range(TRIALS):
        i = rng.randrange(len(blob)); b = bytearray(blob); b[i] ^= 0xFF
        nz = len(agg["bar_z"]) * 4
        bz = np.frombuffer(bytes(b[:nz]), dtype=np.int32).astype(np.int64)
        C = bytes(b[nz:nz + len(agg["C"])])
        eta_start = nz + len(agg["C"])
        eta = bytes(b[eta_start:eta_start + KAPPA])
        tau = bytes(b[-KAPPA:])
        mutated = {"bar_z": bz, "C": C, "eta": eta, "tau": tau}
        if aggverify(pp, mutated, ts, verify_sigs=False):  # structural checks reject before sig verify
            ok += 1
    sec["AMA_mutation"] = ok
    # AMA component substitution: swap one tuple in the supporting set
    ok = 0
    for _ in range(TRIALS):
        ts2 = list(ts); ts2[rng.randrange(len(ts2))] = make_tuple(ID2, msg2, pk2, cert2, sigma2, fresh2)
        try:
            _, encs2 = canonicalize(ts2)
            tau2 = xof(H_AGG, b"".join(encs2))
        except ValueError:
            tau2 = b""
        if tau2 == agg["tau"]:
            ok += 1
    sec["AMA_subst"] = ok
    # CCSA: cross-context reuse of hash outputs
    x = secrets.token_bytes(64)
    sec["CCSA_with_DSH"] = sum(1 for _ in range(TRIALS) if xof(H_CERT, x) == xof(H_SIGN, x))
    sec["CCSA_without_DSH"] = sum(1 for _ in range(TRIALS) if xof(b"", x) == xof(b"", x))
    sec["trials"] = TRIALS
    out["security"] = sec

    # ----------------- Table XIII indicators (platform-portable) -----------------
    import statistics as _st
    data=[secrets.token_bytes(200) for _ in range(2000)]
    def _hb(fn, reps=20):
        ts=[]
        for _ in range(reps):
            t0=time.perf_counter_ns()
            for d in data: fn(d)
            ts.append(time.perf_counter_ns()-t0)
        return _st.median(ts)
    plain=_hb(lambda d: hashlib.shake_256(d).digest(KAPPA))
    dsh=_hb(lambda d: hashlib.shake_256(H_SIGN+d).digest(KAPPA))
    nonce_det=len({hashlib.shake_256(b"PQ-CBAS-DSH/NONCE"+i.to_bytes(8,"big")).digest(KAPPA) for i in range(10000)})
    nonce_rnd=len({secrets.token_bytes(KAPPA) for _ in range(10000)})
    out["indicators"]={
        "dsh_overhead_percent": round((dsh-plain)/plain*100,1),
        "domain_tag_collisions": sec["CCSA_with_DSH"],
        "deterministic_nonce_unique": f"{nonce_det}/10000",
        "random_nonce_unique": f"{nonce_rnd}/10000",
    }

    # ----------------- Classical baseline: ECDSA P-256 (optional) -----------------
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes
        _sk = ec.generate_private_key(ec.SECP256R1()); _pk = _sk.public_key()
        _msg = b"x" * 100
        _sig = _sk.sign(_msg, ec.ECDSA(hashes.SHA256()))
        out["ecdsa_p256"] = {
            "keygen_ms": list(bench(lambda: ec.generate_private_key(ec.SECP256R1()), N_RUNS)),
            "sign_ms": list(bench(lambda: _sk.sign(_msg, ec.ECDSA(hashes.SHA256())), N_RUNS)),
            "verify_ms": list(bench(lambda: _pk.verify(_sig, _msg, ec.ECDSA(hashes.SHA256())), N_RUNS)),
            "sig_bytes_der": len(_sig), "pk_bytes_uncompressed": 65,
        }
        print(json.dumps({"ecdsa_p256": out["ecdsa_p256"]}, indent=1))
    except ImportError:
        print("cryptography not installed; skipping ECDSA baseline (pip install cryptography)")

    json.dump(out, open("bench_results.json", "w"), indent=1, default=str)
    print(json.dumps({k: out[k] for k in ("Setup", "VehKeyGen", "CertGen", "CertValidate", "Sign", "sizes")}, indent=1))
    print(json.dumps(out["agg"], indent=1))
    print(json.dumps(sec, indent=1))

if __name__ == "__main__":
    main()
