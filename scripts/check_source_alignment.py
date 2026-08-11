#!/usr/bin/env python3
"""Release gate for manuscript/source alignment.

This check does not require liboqs. It verifies the source-level invariants that
must hold in the archived snapshot associated with the manuscript.
"""
from pathlib import Path
import importlib.util
import sys
import types

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print(f"[OK] {msg}")


bench_path = ROOT / "src" / "bench_pqcbas.py"
bench_text = bench_path.read_text()
ok("def enc_full" in bench_text, "A3 canonical full-tuple encoder exists")
ok("def canonicalize" in bench_text, "A3 canonical ordering helper exists")
ok('key=lambda T: T["ID"]' not in bench_text, "legacy ID-only aggregate ordering removed")
ok("duplicate canonical tuple" in bench_text, "duplicate canonical tuples are rejected")
ok(bench_text.count("c0 = raw[:, 0]") == 1, "duplicate z-unpack c0 assignment removed")

# Import bench_pqcbas without requiring liboqs; encoding helpers are pure Python.
sys.modules.setdefault("oqs", types.SimpleNamespace(Signature=object))
spec = importlib.util.spec_from_file_location("bench_pqcbas_alignment", bench_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

sigma = b"s" * 3309
fresh = b"f" * 8
cert = (b"id", b"pk", b"gamma")
T1 = mod.make_tuple(b"id", b"message-A", b"pk", cert, sigma, fresh)
T2 = mod.make_tuple(b"id", b"message-B", b"pk", cert, sigma, fresh)
ordered_a, enc_a = mod.canonicalize([T2, T1])
ordered_b, enc_b = mod.canonicalize([T1, T2])
ok(enc_a == enc_b, "canonical order is independent of caller tuple order")
ok(enc_a == sorted(enc_a), "canonical order is lexicographic over Enc_full")
# Prefix-free regression: raw concatenation would collide for these field splits.
Ta = mod.make_tuple(b"a", b"bc", b"pk", cert, sigma, fresh)
Tb = mod.make_tuple(b"ab", b"c", b"pk", cert, sigma, fresh)
ok(mod.enc_full(Ta) != mod.enc_full(Tb), "length-delimited Enc_full prevents field-boundary ambiguity")
try:
    mod.canonicalize([T1, T1])
except ValueError:
    pass
else:
    raise AssertionError("duplicate canonical tuple was not rejected")
print("[OK] duplicate canonical tuple test")

esp = (ROOT / "esp32" / "PQCBAS_ESP32_Bench" / "PQCBAS_ESP32_Bench.ino").read_text()
ok("#define N_SIGN       500" in esp, "ESP32 release default uses n=500 signing trials")

transport = (ROOT / "src" / "transport_budget.py").read_text()
ok("tidak membuktikan kelayakan" in transport, "transport text does not overclaim feasibility")
ok("temuan E4" not in transport, "transport sensitivity is not misattributed to E4")

for script in ("run_bench.sh", "run_seeds.sh", "run_rpi.sh"):
    text = (ROOT / "scripts" / script).read_text()
    ok("ROOT_DIR=" in text and 'cd "$ROOT_DIR"' in text, f"{script} resolves repository root")

run_bench = (ROOT / "scripts" / "run_bench.sh").read_text()
ok("--branch 0.15.0" in run_bench, "run_bench pins liboqs 0.15.0")
ok("oqs-0.15.0" in run_bench, "run_bench uses a version-specific default prefix")
ok('startswith("0.15.0")' in run_bench, "run_bench validates the loaded liboqs runtime version")
ok("cryptography" in run_bench, "run_bench installs the ECDSA baseline dependency")

e2e = (ROOT / "src" / "e2e_workflow.py").read_text()
ok('"kind": "digest"' in e2e and '"cid": self.cert_id' in e2e,
   "synthetic digest mode transmits CertID records")
ok("first-attach-full-then-certid" in e2e, "synthetic digest cache semantics are recorded")

sumo = (ROOT / "src" / "sumo_pqcbas_bridge.py").read_text()
ok('default=0' in sumo and "one unique OBU identity per FCD vehicle" in sumo,
   "SUMO paper default uses one crypto identity per FCD vehicle")
ok("digest_cache_model" in sumo and 'default="warm"' in sumo,
   "SUMO digest steady-state cache model is explicit")

compact = (ROOT / "src" / "bench_compact.py").read_text()
ok("not a validated implementation" in compact,
   "compact exploratory code cannot be mistaken for validated paper evidence")

print("\nSOURCE_ALIGNMENT_OK")
