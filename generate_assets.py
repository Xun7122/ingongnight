"""Create original, lightweight SVG puzzle art. Run from the project root."""
from pathlib import Path
from html import escape
A = Path(__file__).resolve().parent / 'assets'
A.mkdir(exist_ok=True)

def svg(content, w=920,h=550,bg='#f7f0df'):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img"><rect width="{w}" height="{h}" fill="{bg}"/>{content}</svg>'''

def write(name,s):
 (A/name).write_text(s, encoding='utf-8')

def circle(cx,cy,r,fill):return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'

def star(cx,cy,r=20,fill='#dcb85e'):
 import math
 pts=[]
 for k in range(10):
  a=-math.pi/2+k*math.pi/5
  d=r if k%2==0 else r*.42
  pts.append(f'{cx+math.cos(a)*d:.1f},{cy+math.sin(a)*d:.1f}')
 return f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="#926a28" stroke-width="3"/>'

# 4 foil samples with fully legible large marker in the center.
# A variation on the selection puzzle with same-gold foil and distinctly different marks.
for marker in ['K','R','W','M']:
 content='''<defs><linearGradient id="foil" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff6c5"/><stop offset=".44" stop-color="#cda144"/><stop offset=".8" stop-color="#f8e4a1"/><stop offset="1" stop-color="#a87b32"/></linearGradient></defs>
 <rect x="29" y="30" width="862" height="490" rx="16" fill="url(#foil)" stroke="#74521f" stroke-width="8"/>
 <rect x="51" y="50" width="818" height="450" rx="6" fill="none" stroke="#795c29" stroke-width="3"/>
 <path d="M80 135H840 M80 412H840" stroke="#6d4b22" stroke-width="2"/>
 <text x="460" y="97" text-anchor="middle" font-family="Georgia,serif" font-size="25" fill="#4d3620" letter-spacing="6">THE WONDER FACTORY</text>
 <text x="460" y="342" text-anchor="middle" font-family="Georgia,serif" font-size="214" font-weight="bold" fill="#3c2b1d">'''+marker+'''</text>
 <text x="460" y="468" text-anchor="middle" font-family="Georgia,serif" font-size="25" fill="#614826">A SPECIAL TICKET</text>'''
 write('ticket-mark-'+marker.lower()+'.svg',svg(content,w=920,h=550,bg='#eee5ce'))

for num in ['071','170','107','017']:
 content='''<defs><linearGradient id="foil" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#eed28d"/><stop offset=".3" stop-color="#f9e6b1"/><stop offset=".65" stop-color="#d5ac54"/><stop offset="1" stop-color="#ffeab3"/></linearGradient></defs>
 <rect x="33" y="34" width="854" height="482" rx="18" fill="url(#foil)" stroke="#997b48" stroke-width="8"/>
 <rect x="55" y="57" width="810" height="436" fill="none" stroke="#644b2d" stroke-width="2"/>
 <text x="460" y="155" text-anchor="middle" font-family="Georgia,serif" font-size="42" font-weight="bold" fill="#51381a">GOLDEN TICKET</text>
 <text x="460" y="365" text-anchor="middle" font-family="Arial,sans-serif" font-size="170" font-weight="900" letter-spacing="22" fill="#3f2a1e">'''+num+'''</text>
 <text x="460" y="450" text-anchor="middle" font-family="Georgia,serif" font-size="26" fill="#5b4328">SERIAL NUMBER</text>'''
 write('ticket-number-'+num+'.svg',svg(content,w=920,h=550,bg='#eee5ce'))

# Observation puzzles. Layout is intentionally clean and flat; no AI-fantasy lighting.
factory='''<rect x="46" y="40" width="828" height="468" rx="24" fill="#fff9ed" stroke="#dfd3bb" stroke-width="3"/>
<path d="M86 428H834" stroke="#816b56" stroke-width="5"/>
<path d="M170 422V262l115-52v45l95-45v45l98-40v207Z" fill="#a27b70" stroke="#60453d" stroke-width="6"/>
<rect x="218" y="308" width="65" height="112" fill="#5c4c48"/><rect x="311" y="308" width="67" height="112" fill="#5c4c48"/><rect x="396" y="308" width="61" height="112" fill="#5c4c48"/>
<path d="M510 422V201H720V422" fill="#bd9480" stroke="#624e40" stroke-width="6"/><path d="M561 203V100M651 203V125" stroke="#926a55" stroke-width="26"/>
<path d="M561 103C543 80 584 55 561 32M651 126C634 101 677 83 655 60" stroke="#ddd0bf" stroke-width="15" fill="none" stroke-linecap="round"/>
'''
for pos in [(115,120),(370,95),(490,155),(782,273)]:factory+=star(*pos,29)
write('quiz-factory-stars.svg',svg(factory))

# A tray of four different wrappers; question asks for the one with W.
wrappers='''<rect x="42" y="33" width="836" height="480" rx="23" fill="#fffaf0" stroke="#ded3c3" stroke-width="4"/>
<text x="460" y="90" text-anchor="middle" font-family="Arial,sans-serif" font-size="30" font-weight="700" fill="#4e3e36">CHOCOLATE WRAPPERS</text>'''
colors=['#8c78b6','#b45b66','#6d8e7c','#c0a357']
letters=['C','W','C','C']
for i,(c,letter) in enumerate(zip(colors,letters)):
 x=110+i*195
 wrappers+=f'''<g><rect x="{x}" y="162" width="145" height="226" rx="9" fill="{c}" stroke="#473c41" stroke-width="4"/>
 <rect x="{x+12}" y="174" width="121" height="202" rx="4" fill="none" stroke="#fff3cc" stroke-width="3"/>
 <rect x="{x+27}" y="236" width="91" height="93" rx="48" fill="#ead4a0"/>
 <text x="{x+72.5}" y="308" font-family="Georgia,serif" font-weight="bold" text-anchor="middle" font-size="71" fill="#4d3c24">{letter}</text></g>'''
write('quiz-chocolate-wrapper.svg',svg(wrappers))

# Find the one out-of-pattern candy with a missing central square.
mix='''<rect x="45" y="38" width="830" height="476" rx="25" fill="#fff9ee" stroke="#e2d4bd" stroke-width="4"/>
<text x="460" y="100" text-anchor="middle" font-size="28" font-family="Arial,sans-serif" font-weight="700" fill="#5f4d3f">ONE IS DIFFERENT</text>'''
for i,label in enumerate('ABCD'):
 x=96+i*196;y=185
 mix+=f'<rect x="{x}" y="{y}" rx="18" width="142" height="176" fill="#faf4e3" stroke="#d4bea5" stroke-width="4"/><text x="{x+71}" y="416" text-anchor="middle" font-family="Arial" font-weight="700" font-size="30" fill="#6c5247">{label}</text>'
 for k in range(6):
  if i==2 and k==4:continue
  bx=x+22+(k%2)*56;by=y+25+(k//2)*47
  mix+=f'<rect x="{bx}" y="{by}" width="48" height="39" rx="5" fill="#825037" stroke="#5d3427" stroke-width="2"/><rect x="{bx+8}" y="{by+7}" width="32" height="25" rx="3" fill="#996147"/>'
write('quiz-chocolate-different.svg',svg(mix))

# In an otherwise chocolate factory image, find the one striped candy.
candy='''<rect x="45" y="36" width="830" height="478" rx="25" fill="#fff9ee" stroke="#ddc9ad" stroke-width="3"/>
<text x="460" y="101" text-anchor="middle" font-family="Arial" font-size="29" font-weight="700" fill="#665044">THE CANDY COUNTER</text>'''
for i,(x,y) in enumerate([(220,202),(458,202),(696,202),(220,387),(458,387),(696,387)]):
 candy+=circle(x,y,61,'#d58d81' if i!=4 else '#eed1ac')
 candy+=circle(x,y,48,'#f2d4a8')
 for k in range(8):
  import math
  ang=k*math.pi/4
  inner=17;outer=53
  X=x+inner*math.cos(ang);Y=y+inner*math.sin(ang)
  Z=x+outer*math.cos(ang);W=y+outer*math.sin(ang)
  candy+=f'<path d="M{X:.1f},{Y:.1f}L{Z:.1f},{W:.1f}" stroke="{"#f4faf5" if i==4 else "#c76666"}" stroke-width="12" stroke-linecap="round"/>'
write('quiz-candy-different.svg',svg(candy))

print('Generated SVG puzzle assets:',len(list(A.glob('*.svg'))))
