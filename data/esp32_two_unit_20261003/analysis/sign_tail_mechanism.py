#!/usr/bin/env python3
"""ESP32 ML-DSA-65 signing-time tail: test the rejection-loop (geometric) explanation.
Reads logs/final_unit{A,B}_run{1,2}.log (RAW_FRAME_SIGN,i,ms). Model: t = t0 + (k-1)*c, k~Geom(q).
c is fit by least squares on rounded k; q by MLE (1/mean k)."""
import numpy as np,os,sys
L=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','logs')
S=np.array([float(l.split(',')[2]) for u in 'AB' for r in (1,2) for l in open(f'{L}/final_unit{u}_run{r}.log') if l.startswith('RAW_FRAME_SIGN,')])
t0=S.min();n=len(S)
best=min(((np.std(S-(t0+(np.round((S-t0)/c))*c)),c) for c in np.arange(8,16,0.01)))
sd,c=best;k=np.round((S-t0)/c).astype(int)+1;q=1/k.mean()
print(f"n={n} t0(min)={t0:.3f} ms, per-extra-iteration cost c={c:.2f} ms, residual sd={sd:.2f} ms")
print(f"mean k={k.mean():.3f}  MLE q={q:.4f}  (FIPS 204 ML-DSA-65 expected repetitions ~5.1)")
print("k  observed  geometric_expected")
for j in range(1,13):
    print(f"{j:2d} {np.mean(k==j):8.4f} {q*(1-q)**(j-1):8.4f}")
print(f"P(k>=13) obs {np.mean(k>=13):.4f} geom {(1-q)**12:.4f}")
print(f"P(t>100ms) obs {np.mean(S>100):.4f}; geometric-model {np.mean((t0+(np.arange(1,400)-1)*c>100)*q*(1-q)**(np.arange(1,400)-1)*1)*0 + sum(q*(1-q)**(j-1) for j in range(1,400) if t0+(j-1)*c>100):.4f}")
