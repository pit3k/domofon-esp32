import numpy as np, math
F=[697,770,852,941,1209,1336,1477,1633]; K=["123A","456B","789C","*0#D"]
fs=8000;N=205
co=[2*math.cos(2*math.pi*f/fs) for f in F]
def decode(x,minamp=25,twist=8,grp=6,ratio=0.4):
    out=[];dc=x[0]
    for b in range(len(x)//N):
        blk=x[b*N:(b+1)*N]-dc
        P=[]
        for c in co:
            s1=s2=0
            for v in blk: s0=v+c*s1-s2; s2=s1; s1=s0
            P.append(max(0,2*(s1*s1+s2*s2-c*s1*s2)/N))
        E=(blk**2).sum()-blk.sum()**2/N; dc+=blk.mean()
        r=int(np.argmax(P[:4])); c=4+int(np.argmax(P[4:]))
        ar=math.sqrt(2*P[r]/N); ac=math.sqrt(2*P[c]/N); d='-'
        g=10**(grp/10)
        if ar>=minamp and ac>=minamp and abs(10*math.log10(P[c]/P[r]))<=twist and all(P[i]*g<=P[r] for i in range(4) if i!=r) and all(P[i]*g<=P[c] for i in range(4,8) if i!=c) and (P[r]+P[c])>=ratio*E:
            d=K[r][c-4]
        out.append(d)
    return ''.join(out)
rng=np.random.default_rng(1)
def sig(digits,amp,noise,ms=80,gap=60):
    t=[]
    for dch in digits:
        for ri,row in enumerate(K):
            if dch in row: ci=row.index(dch);break
        n=int(fs*ms/1000);tt=np.arange(n)/fs
        t.append(amp*(np.sin(2*np.pi*F[ri]*tt)+np.sin(2*np.pi*F[4+ci]*tt*1.015)))  # +1.5% freq err
        t.append(np.zeros(int(fs*gap/1000)))
    s=np.concatenate(t)+2048+rng.normal(0,noise,sum(len(a) for a in t))
    return np.round(np.clip(s,0,4095))
for amp,noise in [(200,5),(60,10),(30,10),(400,30)]:
    print(amp,noise,decode(sig("1234567890*#",amp,noise)))
# speech-like: sum of many tones
tt=np.arange(fs*2)/fs; sp=sum(80*np.sin(2*np.pi*f*tt+rng.random()*6) for f in rng.uniform(200,3000,15))+2048
print('speech',decode(np.round(sp)))
