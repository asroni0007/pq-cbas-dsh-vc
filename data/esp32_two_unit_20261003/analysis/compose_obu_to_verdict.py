#!/usr/bin/env python3
"""Compose OBU signing time (measured ESP32 samples) with the RSU collection-window wait.

Model (all inputs measured or stated, nothing simulated):
  V = S + U + T_proc,  S = one measured ESP32 signing time (empirical, n=2000 per scheme),
  U ~ Uniform(0, W) (arrival at a random phase of the collection window; the E2E runs
  show a mean wait of W/2), T_proc = fixed RSU processing time (Pi 5 full mode, W=90 ms,
  highway-n20: 7.17 ms mean; reused for every W, which overstates it for small W).
Radio transport and the OBU-to-RSU hop are NOT included, so the results are upper bounds
on the fraction of messages that meet a budget.  S and U are treated as independent.
P(V <= B) = mean over measured S of clip((B - S - T_proc) / W, 0, 1).
"""
import re, os, numpy as np
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
def load(plat, key):
    v = []
    for u in 'AB':
        for r in (1, 2):
            L = open('%s/%s_unit%s_run%d.log' % (d, plat, u, r), errors='replace').read().replace('\r', '').split('\n')
            pat = re.compile(r'^%s,(\d+),([0-9]+\.[0-9]{6})$' % key)
            v += [float(m.group(2)) for m in map(pat.match, L) if m]
    return np.array(v)
S = {'ML-DSA-65 framework signing': load('final', 'RAW_FRAME_SIGN'),
     'ECDSA-P256 micro-ecc': load('uecc', 'F'),
     'ECDSA-P256 mbedTLS': load('ecdsa', 'F'),
     'no OBU signing time (RSU-arrival view)': np.zeros(1)}
T = 7.17
print('T_proc = %.2f ms; n samples: %s' % (T, {k: len(v) for k, v in S.items()}))
for B in (100.0, 200.0):
    print('\nBudget B = %.0f ms: P(S + U + T_proc <= B), percent' % B)
    Ws = (10, 30, 50, 90)
    print('%-42s' % 'signer' + ''.join('  W=%-4d' % w for w in Ws))
    for k, s in S.items():
        print('%-42s' % k + ''.join('  %6.1f' % (100 * np.clip((B - s - T) / w, 0, 1).mean()) for w in Ws))
