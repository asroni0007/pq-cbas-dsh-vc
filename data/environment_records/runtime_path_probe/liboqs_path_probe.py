import os, sys, time, platform, subprocess, threading, shutil, glob, re
import oqs
OUT = os.path.expanduser("~/Desktop/liboqs_probe_%s.txt" % platform.node().split('.')[0])
log = open(OUT, "w")
def P(*a):
    s = " ".join(str(x) for x in a); print(s); log.write(s + "\n"); log.flush()
def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    except Exception as e:
        class R: stdout = ""; stderr = str(e)
        return R()
P("host:", platform.platform(), platform.machine(), "python", platform.python_version())
for k in ("oqs_version", "oqs_python_version"):
    f = getattr(oqs, k, None)
    if f:
        try: P(k + ":", f())
        except Exception as e: P(k, "error", e)
P("ML-DSA-65 enabled:", "ML-DSA-65" in oqs.get_enabled_sig_mechanisms())
pid = os.getpid()
# loaded liboqs file
paths = set()
if os.path.exists("/proc/self/maps"):
    for l in open("/proc/self/maps"):
        m = re.search(r"(/\S*liboqs\S*)", l)
        if m: paths.add(m.group(1))
else:
    for l in sh("lsof -p %d" % pid).stdout.splitlines():
        m = re.search(r"(/\S*liboqs\S*)", l)
        if m: paths.add(m.group(1))
if not paths:
    paths = set(glob.glob(os.path.expanduser("~/_oqs/lib/liboqs*")))
P("liboqs files:", sorted(paths))
for p in sorted(paths):
    rp = os.path.realpath(p)
    if rp.endswith((".a",)) : continue
    P("---", rp, os.path.getsize(rp), "bytes")
    sha = sh("shasum -a 256 '%s'" % rp).stdout.strip(); P("sha256:", sha)
    flag = "-D --defined-only" if sys.platform.startswith("linux") else "-gU"
    syms = sh("nm %s '%s'" % (flag, rp)).stdout.splitlines()
    P("exported symbols total:", len(syms))
    hit = [s for s in syms if re.search(r"ml_dsa_65|mldsa65|MLDSA65|mldsa|dilithium", s, re.I)]
    P("ML-DSA-65 related exported symbols:", len(hit))
    for s in hit[:40]: P("  ", s)
    P("file:", sh("file '%s'" % rp).stdout.strip())
    P("strings (impl hints):")
    for s in sh("strings -a '%s' | grep -iE 'mldsa-native|mldsa_native|pqcrystals.*(ref|avx2|aarch64)|OQS_DIST_BUILD|ml-dsa-65'" % rp).stdout.splitlines()[:15]: P("  ", s)
# workload
stop = False
def work():
    with oqs.Signature("ML-DSA-65") as s:
        pk = s.generate_keypair(); msg = b"x" * 200
        while not stop:
            sig = s.sign(msg); assert s.verify(msg, sig, pk)
t = threading.Thread(target=work); t.start(); time.sleep(1.5)
P("--- profiling workload (sign+verify loop), pid", pid)
if sys.platform == "darwin":
    r = sh("sample %d 4 -mayDie" % pid)
    txt = r.stdout + r.stderr
    sel = [l for l in txt.splitlines() if re.search(r"liboqs|mldsa|ml_dsa|dilithium|keccak|shake|OQS_|PQCP|pqcrystals", l, re.I)]
    P("\n".join(sel[:60]) or "(no matching frames) " + txt[:800])
else:
    if not shutil.which("perf"):
        P("perf NOT installed: run  sudo apt install -y linux-perf  (or linux-tools-generic)")
    else:
        d = "/tmp/probe.perf"
        r = sh("perf record -o %s -F 999 -g -p %d -- sleep 4 2>&1" % (d, pid)); P(r.stdout[-400:])
        r = sh("perf report -i %s --stdio --no-children --sort dso,symbol 2>/dev/null | grep -v '^#' | grep -v '^$' | head -45" % d)
        P(r.stdout or "(perf report empty; try: sudo sysctl kernel.perf_event_paranoid=-1 and rerun)")
stop = True; t.join()
P("\nSaved:", OUT)
