import re,statistics as st,json
out={}
for run in ('run1','run2'):
    raw=open(run+'.log','rb').read().decode('latin1').replace('\r','')
    d={k:[] for k in 'KG S F V H'.split()}
    for ln in raw.split('\n'):
        m=re.search(r'(KG|S|F|V|H),(\d+),(\d+\.\d+)\s*$',ln)
        if m: d[m.group(1)].append(float(m.group(3)))
    summ=[l for l in raw.split('\n') if re.search(r'(KEYGEN|SIGN|VERIFY|SHA256|FRAME|DER|NEG)',l) and not re.match(r'(KG|S|F|V|H),',l)]
    r={}
    for k,v in d.items():
        if v:
            s=sorted(v)
            r[k]=dict(n=len(v),mean=round(st.mean(v),3),med=round(st.median(v),3),p95=s[int(.95*(len(s)-1))],p99=s[int(.99*(len(s)-1))],max=s[-1],over100=sum(x>100 for x in v))
        else: r[k]=dict(n=0)
    out[run]=r
    print(run,json.dumps(r))
    print('\n'.join(summ[:40]))
json.dump(out,open('summary.json','w'),indent=1)
