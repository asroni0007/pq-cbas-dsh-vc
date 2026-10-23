#!/usr/bin/env python3
"""Recompute headline paper numbers from archived raw files and assert they match the manuscript."""
import numpy as np,csv,os
H=os.path.dirname(os.path.abspath(__file__));L=H+'/esp32_two_unit_20261003/logs'
S=np.array([float(l.split(',')[2]) for u in 'AB' for r in (1,2) for l in open(f'{L}/final_unit{u}_run{r}.log') if l.startswith('RAW_FRAME_SIGN,')])
chk=[]
def c(name,val,exp,tol): chk.append((name,val,exp,abs(val-exp)<=tol))
c("ESP32 sign mean ms",S.mean(),93.218,0.001);c("median",np.median(S),78.367,0.002)
c("p95",np.percentile(S,95),205.4,0.1);c("p99",np.percentile(S,99),313.1,0.2)
c("share >100 ms %",100*(S>100).mean(),31.1,0.05)
D=list(csv.DictReader(open(H+'/tables/P0-7_FINAL_120_RUNS.csv')))
def comp(v,t):
    r=[x for x in D if x['variant']==v and int(x['target'])==t];return 100*sum(float(x['completed_logical']) for x in r)/sum(float(x['generated_logical']) for x in r)
c("SMALL 10 %",comp('small',10),98.66,0.01);c("SMALL 100 %",comp('small',100),94.42,0.01)
c("DIGEST 10 %",comp('digest',10),12.32,0.01);c("DIGEST 100 %",comp('digest',100),5.99,0.01)
c("FULL 10 %",comp('full',10),0.43,0.005);c("FULL 100 %",comp('full',100),0.25,0.005)
for t,e in ((10,14.52),(25,23.49),(50,30.61),(100,32.20)):
    r=[x for x in D if x['variant']=='small' and int(x['target'])==t]
    c(f"realized tx target {t}",sum(float(x['generated_logical']) for x in r)/len(r)/1200,e,0.01)
bad=0
for n,v,e,ok in chk:
    print(f"{'OK  ' if ok else 'FAIL'} {n}: {v:.3f} (paper {e})");bad+=not ok
print("mismatches:",bad);raise SystemExit(bad)
