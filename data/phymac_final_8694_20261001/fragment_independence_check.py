#!/usr/bin/env python3
"""Compare observed logical completion with the independent-loss prediction p^n.
p = pooled fragment reception (received/generated fragments) per variant x target,
n = fragments per logical message (1,3,8). Input: ../tables/P0-7_FINAL_120_RUNS.csv"""
import csv,collections,os
f=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','tables','P0-7_FINAL_120_RUNS.csv')
A=collections.defaultdict(lambda:[0,0,0,0,0])
for r in csv.DictReader(open(f)):
    a=A[(r['variant'],int(r['target']))]
    a[0]+=float(r['generated_fragments']);a[1]+=float(r['received_fragments'])
    a[2]+=float(r['generated_logical']);a[3]+=float(r['completed_logical']);a[4]=int(r['expected_fragments'])
print("variant target n  p_frag  indep_p^n(%)  observed(%)  ratio")
for k in sorted(A,key=lambda k:(['small','digest','full'].index(k[0]),k[1])):
    g,rc,gl,cl,n=A[k];p=rc/g;i=p**n;o=cl/gl
    print(f"{k[0]:7s}{k[1]:5d} {n} {p:.5f} {100*i:12.3g} {100*o:11.3f} {o/i:10.3g}")
