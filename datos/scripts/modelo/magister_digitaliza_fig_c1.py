import sys
from PIL import Image
im=Image.open(sys.argv[1]).convert('RGB'); px=im.load()
Z=1657.0; PX=(1928-1386)/800.0  # px per USD
def isblue(c): r,g,b=c; return b>150 and r<80 and 90<g<150
def isor(c): r,g,b=c; return r>220 and 100<g<160 and b<60
groups={'competitiva':(isblue,[827,925,1024,1123,1222,1321,1419,1518]),'no_competitiva':(isor,[837,935,1034,1133,1232,1331,1429,1528])}
for name,(f,xs) in groups.items():
    print(name)
    for t,x0 in enumerate(xs):
        xc=x0+6
        # marker: rows where colored width >=8 among x0..x0+14
        ys=[y for y in range(1370,1950) if sum(f(px[x,y]) for x in range(x0-2,x0+16))>=9]
        m=sorted(ys)[len(ys)//2]
        # CI: contiguous colored run in center column through marker
        y=int(m); 
        while f(px[xc,y-1]) or f(px[xc-1,y-1]) or f(px[xc+1,y-1]): y-=1
        top=y; y=int(m)
        while f(px[xc,y+1]) or f(px[xc-1,y+1]) or f(px[xc+1,y+1]): y+=1
        bot=y
        ys2=[y for y in ys if top+6<y<bot-6]
        m=sum(ys2)/len(ys2)
        u=lambda yy: round((Z-yy)/PX)
        print(f'  t={t} est={u(m)} ic95=[{u(bot)},{u(top)}]')
