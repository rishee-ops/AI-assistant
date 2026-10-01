import numpy as np, subprocess, math, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1080,1920; FPS=30000/1001; DUR=19.935; NF=int(DUR*FPS)
FB='/root/.fonts/Montserrat-ExtraBold.ttf'; FM='/root/.fonts/Montserrat-Bold.ttf'
NAVY=(11,30,63); TEAL=(20,184,196); ORANGE=(255,138,31); WHITE=(255,255,255); YEL=(255,214,10)
fonts={}
def F(sz,b=True):
    k=(sz,b)
    if k not in fonts: fonts[k]=ImageFont.truetype(FB if b else FM,sz)
    return fonts[k]
def clamp(x,a=0,b=1): return max(a,min(b,x))
def eo(x): x=clamp(x); return 1-(1-x)**3
def eback(x):
    x=clamp(x); c=1.7; return 1+(c+1)*(x-1)**3+c*(x-1)**2
def prog(t,a,d): return clamp((t-a)/d)

# ---------- sprites ----------
def text_sprite(txt,sz,fill=WHITE,stroke=0,sc=(0,0,0),shadow=True,bold=True):
    f=F(sz,bold); bb=f.getbbox(txt,stroke_width=stroke)
    w,h=bb[2]-bb[0]+40,bb[3]-bb[1]+40
    im=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(im)
    if shadow:
        sh=Image.new('RGBA',(w,h),(0,0,0,0)); ImageDraw.Draw(sh).text((20-bb[0]+4,20-bb[1]+6),txt,font=f,fill=(0,0,0,150),stroke_width=stroke,stroke_fill=(0,0,0,150))
        im=Image.alpha_composite(im,sh.filter(ImageFilter.GaussianBlur(6))); d=ImageDraw.Draw(im)
    d.text((20-bb[0],20-bb[1]),txt,font=f,fill=fill,stroke_width=stroke,stroke_fill=sc)
    return im
cache={}
def TS(*a,**k):
    key=(a,tuple(sorted(k.items())))
    if key not in cache: cache[key]=text_sprite(*a,**k)
    return cache[key]
def paste(base,spr,cx,cy,scale=1.0,alpha=1.0,rot=0):
    if scale<=0.01 or alpha<=0.01: return
    s=spr
    if abs(scale-1)>1e-3: s=s.resize((max(1,int(s.width*scale)),max(1,int(s.height*scale))),Image.BILINEAR)
    if rot: s=s.rotate(rot,Image.BILINEAR,expand=True)
    if alpha<1:
        s=s.copy(); a=s.getchannel('A').point(lambda v:int(v*alpha)); s.putalpha(a)
    base.alpha_composite(s,(int(cx-s.width/2),int(cy-s.height/2)))

def load(f,h):
    im=Image.open(f).convert('RGBA'); return im.resize((int(im.width*h/im.height),h),Image.LANCZOS)
COURSE=load('course_cut.png',520); COURSE_S=load('course_cut.png',330)
ST1=load('bk1_cut.png',1000); ST2=load('bk2_cut.png',1000)
ST1s=load('bk1_cut.png',640)
def glow(im,col,r=30):
    a=im.getchannel('A'); g=Image.new('RGBA',im.size,col+(0,)); g.putalpha(a.point(lambda v:int(v*0.8)))
    pad=r*2; c=Image.new('RGBA',(im.width+pad*2,im.height+pad*2),(0,0,0,0)); c.alpha_composite(g,(pad,pad))
    c=c.filter(ImageFilter.GaussianBlur(r)); c.alpha_composite(im,(pad,pad)); return c
COURSE_G=glow(COURSE,(255,255,255)); COURSE_SG=glow(COURSE_S,(255,255,255),20)
ST1s_G=glow(ST1s,(255,255,255),18)

# ---------- background ----------
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
BASE=np.zeros((H,W,3),np.float32)
g=(yy/H)[...,None]
BASE=np.array(NAVY)*(1-g)+np.array((8,70,110))*g
def blob(r,col):
    p=r//2; im=Image.new('RGBA',(r*2+p*2,r*2+p*2),col+(0,)); ImageDraw.Draw(im).ellipse((p,p,p+r*2,p+r*2),fill=col+(140,))
    return im.filter(ImageFilter.GaussianBlur(r//4))
BLOBS=[(blob(380,TEAL),0.3,0.25,0.7),(blob(320,ORANGE),0.75,0.7,1.1),(blob(260,(90,80,220)),0.2,0.8,0.9)]
BASEIM=Image.fromarray(BASE.astype(np.uint8)).convert('RGBA')
def background(t):
    im=BASEIM.copy()
    for b,x,y,sp in BLOBS:
        cx=W*(x+0.12*math.sin(t*sp)); cy=H*(y+0.08*math.cos(t*sp*1.3))
        im.alpha_composite(b,(int(cx-b.width/2),int(cy-b.height/2)))
    d=ImageDraw.Draw(im)
    # drifting dot grid
    off=(t*40)%90
    for gy in range(-1,23):
        for gx in range(13):
            x=gx*90+((gy%2)*45); y=gy*90+off
            d.ellipse((x-3,y-3,x+3,y+3),fill=(255,255,255,40))
    # rotating rings
    for i,(cx,cy,r,w,col,sp) in enumerate([(W*0.85,H*0.12,150,10,TEAL,60),(W*0.12,H*0.9,200,8,ORANGE,-45)]):
        a0=t*sp; d.arc((cx-r,cy-r,cx+r,cy+r),a0,a0+250,fill=col+(200,),width=w)
        d.arc((cx-r*0.7,cy-r*0.7,cx+r*0.7,cy+r*0.7),-a0*1.5,-a0*1.5+120,fill=WHITE+(120,),width=w//2)
    # floating plus signs
    for i in range(8):
        x=(i*157+40)%W; y=(H-(t*70+i*260))%H; s=14+(i%3)*6
        d.line((x-s,y,x+s,y),fill=WHITE+(90,),width=5); d.line((x,y-s,x,y+s),fill=WHITE+(90,),width=5)
    return im

# ---------- timeline ----------
BG=[(6.6,7.35,'brand'),(10.1,11.25,'courses'),(13.1,15.75,'students'),(17.7,DUR+0.1,'outro')]
TALK=[(0,6.6,1.0,1.06),(7.35,10.1,1.0,1.04),(11.25,13.1,1.0,1.05),(15.75,17.7,1.04,1.08)]
SUBS=[ # (start,end,[(word,t,hl)])
 (0.0,0.86,[('HI,',0.0,0),('I',0.7,0),('AM',0.72,0)]),
 (0.86,1.62,[('RISHEE',0.86,1),('RHUDRA',1.14,1)]),
 (1.62,4.74,[('AND',1.62,0),('I',3.0,0),('AM',3.44,0)]),
 (4.74,5.44,[('THE',4.74,0),('DEPUTY',4.98,1),('DIRECTOR',5.12,1)]),
 (5.44,6.6,[('AT',5.44,0),('SKILL',5.76,1),('ARBITRAGE',6.0,1)]),
 (7.35,8.42,[('I',7.5,0),('TAKE',7.98,0),('CARE',8.22,0)]),
 (8.42,8.96,[('OF',8.42,0),('SOME',8.56,0),('OF THE',8.72,0)]),
 (8.96,10.1,[('COURSES',8.96,1),('AROUND',9.28,0),('HERE',9.64,0)]),
 (11.25,11.82,[('AND',11.3,0),('YEAH,',11.44,0)]),
 (11.82,12.56,[('THIS IS',11.82,0),('PRETTY',12.14,0),('MUCH',12.32,0)]),
 (12.56,13.1,[('WHAT',12.56,0),('I',12.68,1),('DO.',12.82,1)]),
 (15.75,16.6,[('SO',15.8,0),('THIS',16.12,0),('IS',16.44,0)]),
 (16.6,17.7,[('JUST',16.6,0),('AN',16.8,0),('INTRO',16.96,1),('VIDEO',17.2,1)]),
]
def in_bg(t):
    for a,b,k in BG:
        if a<=t<b: return a,b,k
    return None

def subtitles(im,t):
    for a,b,words in SUBS:
        if not(a<=t<b): continue
        if in_bg(t): return
        sprs=[]
        for w,wt,hl in words:
            on=t>=wt-0.03
            col=YEL if (hl and on) else WHITE
            sprs.append((TS(w,84,fill=col,stroke=8,sc=(0,0,0)),wt,on))
        gap=-18; total=sum(s.width for s,_,_ in sprs)+gap*(len(sprs)-1)
        maxw=980
        sc=min(1,maxw/total); x=W/2-total*sc/2; y=1640
        for s,wt,on in sprs:
            if not on: x+=(s.width+gap)*sc; continue
            p=prog(t,wt-0.03,0.18); k=sc*(0.6+0.4*eback(p))
            paste(im,s,x+s.width*sc/2,y-14*(1-eo(p)),k,eo(p*2))
            x+=(s.width+gap)*sc
        return

def rrect(d,box,r,fill): d.rounded_rectangle(box,r,fill=fill)

def lower_third(im,t):
    a,b=0.35,6.45
    if not(a<=t<b): return
    pin=eo(prog(t,a,0.5)); pout=eo(prog(t,b-0.35,0.35)); vis=pin*(1-pout)
    layer=Image.new('RGBA',(W,300),(0,0,0,0)); d=ImageDraw.Draw(layer)
    bw=int(760*eo(prog(t,a,0.45))*(1-pout))
    rrect(d,(60,30,60+max(bw,30),150),24,ORANGE+(255,))
    rrect(d,(60,150,60+max(int(bw*0.92),30),230),20,(255,255,255,240))
    d.rectangle((60,30,74,230),fill=TEAL+(255,))
    if pin>0.5:
        ta=clamp((pin-0.5)*2)*(1-pout)
        n=TS('RISHEE RHUDRA',64,shadow=False); r=TS('Deputy Director · Skill Arbitrage',36,fill=NAVY,shadow=False,bold=False)
        paste(layer,n,100+n.width/2-20+(1-ta)*-40,92,1,ta)
        paste(layer,r,100+r.width/2-20+(1-ta)*-40,190,1,ta)
    im.alpha_composite(layer,(0,125-int((1-vis)*30)))

def corner_fx(im,t):
    d=ImageDraw.Draw(im)
    # animated corner brackets
    L=90+10*math.sin(t*3); m=40; c=WHITE+(200,); w=8
    for (x,y,sx,sy) in [(m,m,1,1),(W-m,m,-1,1),(m,H-m,1,-1),(W-m,H-m,-1,-1)]:
        d.line((x,y,x+sx*L,y),fill=c,width=w); d.line((x,y,x,y+sy*L),fill=c,width=w)
    # rec dot + live tag
    if int(t*2)%2==0: d.ellipse((80,90,104,114),fill=(255,60,60,255))
    paste(im,TS('INTRO',34,shadow=False),180,102,1,0.9)
    # spinning arc top-right
    a0=t*120; d.arc((W-210,70,W-70,210),a0,a0+270,fill=TEAL+(230,),width=10)
    d.arc((W-180,100,W-100,180),-a0,-a0+180,fill=ORANGE+(230,),width=8)

def badge(im,t,a,b,txt,cx,cy,col=TEAL,icon=None):
    if not(a<=t<b): return
    p=eback(prog(t,a,0.35)); o=eo(prog(t,b-0.25,0.25))
    s=TS(txt,52,shadow=False)
    pad=Image.new('RGBA',(s.width+60,s.height+20),(0,0,0,0)); dd=ImageDraw.Draw(pad)
    dd.rounded_rectangle((0,0,pad.width-1,pad.height-1),36,fill=col+(255,)); pad.alpha_composite(s,(30,10))
    paste(im,pad,cx,cy,p*(1-o),1-o,rot=-4)

def talk_overlays(im,t):
    corner_fx(im,t); lower_third(im,t)
    badge(im,t,5.7,6.6,'SKILL ARBITRAGE',W/2,1470,ORANGE)
    # course PNG + student when talking about courses
    if 8.9<=t<10.1:
        p=eback(prog(t,8.9,0.45)); fl=12*math.sin(t*5)
        paste(im,COURSE_SG,240,1420+fl,p,1,rot=6*math.sin(t*3))
        badge(im,t,9.0,10.1,'COURSES',240,1260,ORANGE)
        p2=eo(prog(t,9.2,0.45))
        paste(im,ST1s_G,W-190+(1-p2)*500,1400,1,1)
    badge(im,t,12.6,13.1,'✓ WHAT I DO',W/2,1000,TEAL) if False else None
    if 12.56<=t<13.1:
        p=eback(prog(t,12.56,0.3)); d=ImageDraw.Draw(im)
        cx,cy,r=W-170,1380,int(70*p)
        if r>2:
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=TEAL+(255,))
            d.line((cx-r*0.45,cy,cx-r*0.1,cy+r*0.35,cx+r*0.5,cy-r*0.35),fill=WHITE,width=max(2,int(14*p)),joint='curve')
    if 16.9<=t<17.7:
        p=eback(prog(t,16.9,0.3)); d=ImageDraw.Draw(im)
        cx,cy,r=W-170,1380,int(80*p)
        if r>2:
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=ORANGE+(255,))
            d.polygon([(cx-r*0.3,cy-r*0.45),(cx-r*0.3,cy+r*0.45),(cx+r*0.5,cy)],fill=WHITE)

def bg_scene(t,a,b,kind):
    im=background(t); lt=t-a
    if kind=='brand':
        p=eback(prog(lt,0.08,0.35))
        d=ImageDraw.Draw(im)
        for i in range(3):
            r=int(250+eo(prog(lt,0.05+i*0.08,0.6))*420); al=int(200*(1-prog(lt,0.05+i*0.08,0.6)))
            d.ellipse((W/2-r,H/2-r,W/2+r,H/2+r),outline=WHITE+(al,),width=6)
        paste(im,TS('SKILL',150,fill=WHITE),W/2,H/2-90,p)
        paste(im,TS('ARBITRAGE',120,fill=ORANGE),W/2,H/2+60,eback(prog(lt,0.15,0.35)))
        uw=int(560*eo(prog(lt,0.3,0.3)))
        d.rounded_rectangle((W/2-uw/2,H/2+150,W/2+uw/2,H/2+166),8,fill=TEAL+(255,))
    elif kind=='courses':
        h=TS('OUR',90,fill=WHITE); h2=TS('COURSES',140,fill=YEL)
        paste(im,h,W/2-(1-eo(prog(lt,0,0.3)))*W,560,1)
        paste(im,h2,W/2+(1-eo(prog(lt,0.08,0.3)))*W,690,1)
        d=ImageDraw.Draw(im); r=330
        d.ellipse((W/2-r,1150-r,W/2+r,1150+r),fill=(255,255,255,30),outline=TEAL+(255,),width=6)
        paste(im,COURSE_G,W/2,1150+10*math.sin(lt*6),eback(prog(lt,0.15,0.4)))
        for i in range(6):
            ang=lt*1.6+i*math.pi/3; R=430
            x=W/2+R*math.cos(ang); y=1150+R*0.55*math.sin(ang); s=eo(prog(lt,0.2+i*0.05,0.3))
            rr=int(26*s); col=[ORANGE,TEAL,YEL][i%3]
            if rr>1: d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=col+(255,))
    elif kind=='students':
        d=ImageDraw.Draw(im)
        for i,(cx,col) in enumerate([(W*0.3,ORANGE),(W*0.72,TEAL)]):
            r=int(300*eback(prog(lt,0.1+i*0.12,0.45)))
            if r>2: d.ellipse((cx-r,1300-r,cx+r,1300+r),fill=col+(230,))
        p1=eo(prog(lt,0.2,0.5)); p2=eo(prog(lt,0.35,0.5))
        paste(im,ST1,W*0.3-(1-p1)*800,1420+(1-p1)*0,1)
        paste(im,ST2,W*0.74+(1-p2)*800,1420,1)
        for i,(w,col) in enumerate([('LEARN.',WHITE),('GROW.',YEL),('SUCCEED.',ORANGE)]):
            st=0.6+i*0.45; p=eback(prog(lt,st,0.35))
            paste(im,TS(w,120,fill=col),W/2,330+i*150,p,clamp(p*2))
    elif kind=='outro':
        d=ImageDraw.Draw(im)
        cw=int(900*eo(prog(lt,0.05,0.4)))
        d.rounded_rectangle((W/2-cw/2,620,W/2+cw/2,1300),48,fill=(255,255,255,235))
        if lt>0.3:
            paste(im,TS('RISHEE RHUDRA',96,fill=NAVY,shadow=False),W/2,760-(1-eo(prog(lt,0.3,0.35)))*40,1,eo(prog(lt,0.3,0.35)))
            bw=int(560*eo(prog(lt,0.5,0.3)))
            d.rounded_rectangle((W/2-bw/2,850,W/2+bw/2,862),6,fill=ORANGE+(255,))
            paste(im,TS('Deputy Director',62,fill=(40,60,90),shadow=False,bold=False),W/2,940,1,eo(prog(lt,0.6,0.3)))
            paste(im,TS('SKILL ARBITRAGE',78,fill=TEAL,shadow=False),W/2,1060,eback(prog(lt,0.8,0.35)))
            paste(im,COURSE_S.resize((190,int(190*COURSE_S.height/COURSE_S.width))),W/2,1190,eback(prog(lt,1.0,0.35)))
        msg="Let's learn together!"; n=int(clamp((lt-1.0)/0.6)*len(msg))
        if n: paste(im,TS(msg[:n],70,fill=YEL),W/2,1480,1)
    return im

# ---------- main ----------
dec=subprocess.Popen(['ffmpeg','-v','error','-i','in.mp4','-vf','hflip,scale=1080:1920:flags=lanczos,unsharp=5:5:0.6,eq=contrast=1.06:saturation=1.12,fps=30000/1001','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30000/1001','-i','-','-i','mix.wav','-map','0:v','-map','1:a','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart','out.mp4'],stdin=subprocess.PIPE)
only=set(int(x) for x in sys.argv[1:])
for i in range(NF+5):
    raw=dec.stdout.read(W*H*3)
    if len(raw)<W*H*3: break
    t=i/FPS
    if only and i not in only: continue
    fr=Image.frombuffer('RGB',(W,H),raw).convert('RGBA')
    # slow zoom per talk segment
    for a,b,z0,z1 in TALK:
        if a<=t<b+0.4:
            z=z0+(z1-z0)*clamp((t-a)/(b-a)); cw,ch=W/z,H/z; x0=(W-cw)/2; y0=(H-ch)/2*0.6
            fr=fr.transform((W,H),Image.EXTENT,(x0,y0,x0+cw,y0+ch),Image.BILINEAR); break
    talk_overlays(fr,t); subtitles(fr,t)
    bgi=in_bg(t)
    if bgi:
        a,b,k=bgi; bgim=bg_scene(t,a,b,k)
        # circle wipe in / out
        rin=eo(prog(t,a,0.22)); rout=eo(prog(t,b-0.18,0.18)) if b<DUR else 0
        R=math.hypot(W,H)/2*(rin*(1-rout))
        m=Image.new('L',(W,H),0); ImageDraw.Draw(m).ellipse((W/2-R,H/2-R,W/2+R,H/2+R),fill=255)
        fr=Image.composite(bgim,fr,m)
        if 0<rin<1 or 0<rout<1:
            ImageDraw.Draw(fr).ellipse((W/2-R,H/2-R,W/2+R,H/2+R),outline=ORANGE+(255,),width=14)
    if only: fr.convert('RGB').save(f'prev_{i}.jpg',quality=80); continue
    enc.stdin.write(fr.convert('RGB').tobytes())
    if i%60==0: print(i,'/',NF,flush=True)
enc.stdin.close(); enc.wait(); dec.wait()
