"""Recompute all ESP32 statistics from the 12 validated raw serial logs.
Usage: python3 analyze_esp32.py <log_dir> <out_prefix>
Validated logs: {uecc,final,ecdsa}_unit{A,B}_run{1,2}.log (+ .mac). Fixed seed, 20,000 bootstrap resamples."""
import json, math, os, re, sys
import numpy as np
from scipy import stats as sps
d, outp = sys.argv[1], sys.argv[2]
SEED, NB = 20261003, 20000
OPS = {'uecc': {'KG': 'keygen', 'S': 'sign_digest', 'F': 'frame_sign', 'V': 'verify', 'H': 'sha256'},
       'ecdsa': {'KG': 'keygen', 'S': 'sign_digest', 'F': 'frame_sign', 'V': 'verify', 'H': 'sha256'},
       'final': {'RAW_SIGN': 'sign_core', 'RAW_FRAME_SIGN': 'frame_sign', 'RAW_VERIFY': 'verify'}}
def load(plat, unit, run):
    b = '%s/%s_unit%s_run%d' % (d, plat, unit, run)
    L = open(b + '.log', errors='replace').read().replace('\r', '').split('\n')
    out = {}
    for key, name in OPS[plat].items():
        pat = re.compile(r'^%s,(\d+),([0-9]+\.[0-9]{6})$' % key)
        v = [(int(m.group(1)), float(m.group(2))) for m in map(pat.match, L) if m]
        assert [i for i, _ in v] == list(range(len(v))), (b, name)
        out[name] = np.array([x for _, x in v])
    ex = {}
    if plat == 'final':
        for k, n in (('keypair', 'keygen'), ('DSH-48', 'dsh48')):
            for l in L:
                m = re.match(r'^%s\s+mean=([0-9.]+) sd=([0-9.]+)' % re.escape(k), l)
                if m: ex[n] = (float(m.group(1)), float(m.group(2)))
        seq = {}
        for l in L:
            m = re.match(r'^m=(\d+) n=\d+ mean=([0-9.]+)', l)
            if m: seq[int(m.group(1))] = float(m.group(2))
        ex['seq'] = seq
    return out, ex
def wilson(k, n, z=1.959964):
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return 100 * (c - h), 100 * (c + h)
def summ(v):
    return dict(n=int(len(v)), mean=float(v.mean()), sd=float(v.std(ddof=1)), median=float(np.median(v)),
                p90=float(np.percentile(v, 90)), p95=float(np.percentile(v, 95)), p99=float(np.percentile(v, 99)),
                min=float(v.min()), max=float(v.max()))
def boot(v, fn):
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(v), size=(NB, len(v)))
    r = np.array([fn(v[i]) for i in idx]) if False else None
    s = np.sort(v)
    res = []
    for q in fn:
        res.append(np.percentile(v[idx], q, axis=1))
    return [(float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))) for x in res]
R = {}
data = {}
for plat in OPS:
    for u in 'AB':
        for r in (1, 2):
            data[(plat, u, r)] = load(plat, u, r)
res = {'per_run': {}, 'pooled': {}, 'per_unit': {}}
for (plat, u, r), (dd, ex) in data.items():
    res['per_run']['%s_%s%d' % (plat, u, r)] = {k: summ(v) for k, v in dd.items()}
    if ex: res['per_run']['%s_%s%d' % (plat, u, r)]['device_summary'] = {k: v for k, v in ex.items()}
for plat in OPS:
    for name in OPS[plat].values():
        allv = np.concatenate([data[(plat, u, r)][0][name] for u in 'AB' for r in (1, 2)])
        rm = [float(data[(plat, u, r)][0][name].mean()) for u in 'AB' for r in (1, 2)]
        e = summ(allv); e['run_means'] = rm; e['mean_of_run_means'] = float(np.mean(rm)); e['run_mean_min'] = min(rm); e['run_mean_max'] = max(rm)
        e['unit_means'] = {u: float(np.mean([data[(plat, u, r)][0][name].mean() for r in (1, 2)])) for u in 'AB'}
        for B in (200, 100, 50):
            k = int((allv > B).sum()); lo, hi = wilson(k, len(allv))
            e['over%d' % B] = dict(k=k, n=int(len(allv)), pct=100 * k / len(allv), wilson=[lo, hi],
                                   per_run_pct=[100 * float((data[(plat, u, r)][0][name] > B).mean()) for u in 'AB' for r in (1, 2)])
        res['pooled']['%s/%s' % (plat, name)] = e
        if plat == 'final' and name in ('sign_core', 'frame_sign'):
            cis = boot(allv, [50, 90, 95, 99])
            e['boot'] = dict(median=cis[0], p90=cis[1], p95=cis[2], p99=cis[3], B=NB, seed=SEED)
            a = np.concatenate([data[(plat, 'A', r)][0][name] for r in (1, 2)]); b = np.concatenate([data[(plat, 'B', r)][0][name] for r in (1, 2)])
            e['unit_test'] = dict(ks_p=float(sps.ks_2samp(a, b).pvalue), mwu_p=float(sps.mannwhitneyu(a, b).pvalue), mean_A=float(a.mean()), mean_B=float(b.mean()),
                                  median_A=float(np.median(a)), median_B=float(np.median(b)))
            r1 = [data[(plat, u, r)][0][name] for u in 'AB' for r in (1, 2)]
            e['run_kruskal_p'] = float(sps.kruskal(*r1).pvalue)
ds = {n: float(np.mean([data[('final', u, r)][1][n][0] for u in 'AB' for r in (1, 2)])) for n in ('keygen', 'dsh48')}
ds_rng = {n: [min(data[('final', u, r)][1][n][0] for u in 'AB' for r in (1, 2)), max(data[('final', u, r)][1][n][0] for u in 'AB' for r in (1, 2))] for n in ('keygen', 'dsh48')}
seq = {m: float(np.mean([data[('final', u, r)][1]['seq'][m] for u in 'AB' for r in (1, 2)])) for m in (1, 2, 5, 10)}
res['final_device_summary'] = dict(mean=ds, range=ds_rng, seq_mean=seq)
P = res['pooled']
fs = P['final/frame_sign']['mean_of_run_means']; sc = P['final/sign_core']['mean_of_run_means']; vm = P['final/verify']['mean_of_run_means']
rat = {}
for plat in ('ecdsa', 'uecc'):
    rat[plat] = dict(verify=P[plat + '/verify']['mean_of_run_means'] / vm, frame_sign=P[plat + '/frame_sign']['mean_of_run_means'] / fs,
                     sign_core=P[plat + '/sign_digest']['mean_of_run_means'] / sc, keygen=P[plat + '/keygen']['mean_of_run_means'] / ds['keygen'],
                     verify_range=[P[plat + '/verify']['run_mean_min'] / vm, P[plat + '/verify']['run_mean_max'] / vm])
res['ratios_vs_mldsa'] = rat
res['hsign_share'] = dict(of_frame=100 * ds['dsh48'] / fs, of_core=100 * ds['dsh48'] / sc, diff_frame_core=fs - sc)
res['cv'] = {k: P['final/' + k]['sd'] / P['final/' + k]['mean'] for k in ('sign_core', 'frame_sign')}
json.dump(res, open(outp + '.json', 'w'), indent=1)
def line(k):
    e = P[k]
    return '%-22s n=%d mean_of_runs=%.3f [%.3f,%.3f] sd=%.3f med=%.3f p90=%.3f p95=%.3f p99=%.3f max=%.3f' % (k, e['n'], e['mean_of_run_means'], e['run_mean_min'], e['run_mean_max'], e['sd'], e['median'], e['p90'], e['p95'], e['p99'], e['max'])
with open(outp + '.txt', 'w') as f:
    for k in P: f.write(line(k) + '\n')
    for k in ('final/frame_sign', 'final/sign_core', 'ecdsa/frame_sign', 'ecdsa/sign_digest', 'uecc/frame_sign', 'uecc/sign_digest'):
        e = P[k]
        f.write('%s over200=%.1f%% (%d/%d, W %.1f-%.1f) over100=%.1f%% (%d/%d, W %.1f-%.1f) over50=%.1f%% (%d/%d, W %.1f-%.1f)\n' % (
            k, e['over200']['pct'], e['over200']['k'], e['over200']['n'], *e['over200']['wilson'], e['over100']['pct'], e['over100']['k'], e['over100']['n'], *e['over100']['wilson'],
            e['over50']['pct'], e['over50']['k'], e['over50']['n'], *e['over50']['wilson']))
        f.write('   per-run over100 %%: %s; over200: %s; over50: %s\n' % ([round(x, 1) for x in e['over100']['per_run_pct']], [round(x, 1) for x in e['over200']['per_run_pct']], [round(x, 1) for x in e['over50']['per_run_pct']]))
    for k in ('final/frame_sign', 'final/sign_core'):
        e = P[k]; b = e['boot']
        f.write('%s boot median %.1f-%.1f p90 %.1f-%.1f p95 %.1f-%.1f p99 %.1f-%.1f; unit_test %s; kruskal_runs_p=%.3g\n' % (k, *b['median'], *b['p90'], *b['p95'], *b['p99'], e['unit_test'], e['run_kruskal_p']))
    f.write('device summary keygen/dsh mean %s range %s seq %s\n' % (ds, ds_rng, seq))
    f.write('ratios %s\nhsign %s\ncv %s\n' % (json.dumps(rat), json.dumps(res['hsign_share']), json.dumps(res['cv'])))
    f.write('unit means: %s\n' % json.dumps({k: P[k]['unit_means'] for k in P}))
print(open(outp + '.txt').read())
