import numpy as np, wave
sr=48000; bpm=112; beat=60/bpm; dur=21.0; N=int(sr*dur)
L=np.zeros(N); R=np.zeros(N)
rng=np.random.default_rng(1)
def f(m): return 440*2**((m-69)/12)
def add(sig,t,pan=0.0,g=1.0):
    i=int(t*sr); j=min(N,i+len(sig))
    if i>=N: return
    s=sig[:j-i]*g
    L[i:j]+=s*(1-pan)/1; R[i:j]+=s*(1+pan)/1
def pluck(m,d=0.35):
    t=np.arange(int(sr*d))/sr; fr=f(m)
    x=sum(np.sin(2*np.pi*fr*k*t)/k**1.3 for k in range(1,7))
    return x*np.exp(-t*9)*np.minimum(1,t*400)
def pad(ms,d):
    t=np.arange(int(sr*d))/sr
    x=sum(np.sin(2*np.pi*f(m)*t*(1+dt))+0.0 for m in ms for dt in(-0.003,0.003))
    env=np.minimum(1,t/0.25)*np.minimum(1,(d-t)/0.3)
    return x*env/len(ms)
def kick():
    t=np.arange(int(sr*0.35))/sr
    ph=2*np.pi*np.cumsum(50+120*np.exp(-t*30))/sr
    return np.sin(ph)*np.exp(-t*9)
def clap():
    t=np.arange(int(sr*0.2))/sr; n=rng.standard_normal(len(t))
    n=np.convolve(n,[1,-1],'same')
    return n*np.exp(-t*25)*0.5
def hat():
    t=np.arange(int(sr*0.05))/sr; n=rng.standard_normal(len(t))
    return np.diff(np.r_[0,n])*np.exp(-t*90)*0.25
def bass(m,d):
    t=np.arange(int(sr*d))/sr; fr=f(m)
    x=np.sin(2*np.pi*fr*t)+0.3*np.sin(4*np.pi*fr*t)
    return x*np.minimum(1,t*200)*np.exp(-t*2.5)
prog=[(60,[60,64,67,72]),(55,[55,59,62,67]),(57,[57,60,64,69]),(53,[53,57,60,65])]
bar=4*beat; t=0; b=0
while t<dur:
    root,ch=prog[b%4]
    add(pad([m-12 for m in ch[:3]]+[ch[1]],bar),t,0,0.12)
    for s in range(8):
        add(pluck(ch[(s*3)%4]+12 if s%4==3 else ch[(s*3)%4]+12),t+s*beat/2,0.35*(1 if s%2 else -1),0.13)
        add(bass(root-24,beat/2*0.95),t+s*beat/2,0,0.32 if s%2==0 else 0.2)
    for q in range(4):
        add(kick(),t+q*beat,0,0.6)
        if q%2: add(clap(),t+q*beat,0,0.35)
        for e in range(2): add(hat(),t+q*beat+e*beat/2+beat/4,0.3,1)
    t+=bar; b+=1
x=np.stack([L,R],1)
x=np.tanh(x*1.4); x/=np.abs(x).max()*1.05
fade=int(sr*1.5); x[-fade:]*=np.linspace(1,0,fade)[:,None]
w=wave.open('music.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((x*32767).astype('<i2').tobytes()); w.close()
