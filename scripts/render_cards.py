#!/usr/bin/env python3
"""Render self-contained, GitHub-README-friendly SVG cards.

Usage:
    python scripts/render_cards.py           # animated, live data if available
    STATIC=1 python scripts/render_cards.py  # final frame, no motion

All graphics are native SVG; no JS, external SVG images, foreignObject or remote fonts.
Fira Code and Inter (or installed fallbacks) are subset via pyftsubset into WOFF
and embedded as base64 in each card. The font files themselves are not copied.
"""
from __future__ import annotations
import base64
import calendar
from collections import defaultdict
import datetime as dt
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape, quoteattr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cards'
CFG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
DATA = json.loads((ROOT / 'data' / 'contributions.json').read_text(encoding='utf-8'))
STATIC = os.environ.get('STATIC', '0').strip().lower() in ('1', 'true', 'yes')
B = CFG['brand']


def txt(v):
    return escape(str(v), {'"': '&quot;', "'": '&apos;'})


def el_text(x, y, content, size=24, *, fill=None, weight=500, family='sans', extra=''):
    f = 'SohailMono' if family == 'mono' else 'SohailSans'
    return f'<text x="{x}" y="{y}" font-family="{f}, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill or B["text"]}" {extra}>{txt(content)}</text>'


def rect(x, y, w, h, fill, rx=16, stroke=None, sw=1, extra=''):
    stroke_part = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{stroke_part} {extra}/>'


def line(x1, y1, x2, y2, color=None, sw=1, extra=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color or B["line"]}" stroke-width="{sw}" {extra}/>'


def circle(x, y, r, fill, extra=''):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" {extra}/>'


def font_path(family, env_key, fallback):
    explicit = os.environ.get(env_key)
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise FileNotFoundError(f'{env_key} points to a missing file: {p}')
        return p
    try:
        result = subprocess.run(['fc-match', '-f', '%{file}', family], capture_output=True, text=True, check=True)
        path = Path(result.stdout.strip())
        if path.is_file():
            return path
    except (OSError, subprocess.CalledProcessError):
        pass
    windows_fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    if env_key == 'FIRA_CODE_FONT':
        candidates = [Path(fallback), windows_fonts / 'CascadiaCode.ttf', windows_fonts / 'consola.ttf', windows_fonts / 'cour.ttf']
    else:
        candidates = [Path(fallback), windows_fonts / 'segoeui.ttf', windows_fonts / 'arial.ttf']
    for p in candidates:
        if p.is_file():
            return p
    raise RuntimeError(f'No usable font found for {family}; set {env_key} to a locally installed .ttf/.otf font path')


def make_embedded_fonts():
    # Subset only glyphs present in cards. User-supplied project strings included.
    text = json.dumps(CFG, ensure_ascii=False) + json.dumps(DATA, ensure_ascii=False)
    text += '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    text += " • / - _ : + ( ) . , ? ! # @ & | — · → ↗ ✓ GitHub contribution streak active days busiest day"
    font_css = []
    fonts = [
        ('SohailMono', font_path('Fira Code', 'FIRA_CODE_FONT', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')),
        ('SohailSans', font_path('Inter', 'INTER_FONT', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')),
    ]
    with tempfile.TemporaryDirectory(prefix='svg-fonts-') as temp:
        tmp = Path(temp)
        chars = tmp / 'chars.txt'
        chars.write_text(text, encoding='utf-8')
        for family, src in fonts:
            woff = tmp / f'{family}.woff'
            command = [
                sys.executable, '-m', 'fontTools.subset', str(src), '--text-file=' + str(chars),
                '--output-file=' + str(woff), '--flavor=woff',
                '--layout-features=*', '--no-hinting', '--notdef-glyph', '--notdef-outline',
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except FileNotFoundError as exc:
                raise RuntimeError('fontTools missing. Install: pip install "fonttools[woff]"') from exc
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f'Font subsetting failed for {src}: {exc.stderr[-1200:]}') from exc
            encoded = base64.b64encode(woff.read_bytes()).decode('ascii')
            font_css.append("@font-face{font-family:'" + family + "';src:url('data:font/woff;base64," + encoded + "') format('woff');font-style:normal;font-weight:100 900;}")
    return '\n'.join(font_css)


FONTS = ''


def svg_shell(name, width, height, inner, *, delay=0, description='', animation=True):
    css = [FONTS, f'''
      .reveal{{animation:enter .9s cubic-bezier(.2,.7,.2,1) both;animation-delay:{delay:.2f}s}}
      .float{{animation:float 5.2s ease-in-out infinite}}
      .glow{{animation:glow 4.0s ease-in-out infinite}}
      .trace{{stroke-dasharray:9 10;animation:dash 16s linear infinite}}
      @keyframes enter{{from{{opacity:0;transform:translateY(13px)}}to{{opacity:1;transform:translateY(0)}}}}
      @keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-7px)}}}}
      @keyframes glow{{0%,100%{{opacity:.55}}50%{{opacity:.95}}}}
      @keyframes dash{{to{{stroke-dashoffset:-380}}}}
      @media (prefers-reduced-motion: reduce){{
        *,*::before,*::after{{animation:none!important;transition:none!important;}}
        animate,animateTransform,animateMotion,.smil-only{{display:none!important;visibility:hidden!important;}}
      }}
    ''']
    if STATIC or not animation:
        css.append('*,*::before,*::after{animation:none!important;transition:none!important;} animate,animateTransform,animateMotion{display:none!important;}')
    defs = f'''
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="{B['background']}"/>
          <stop offset=".55" stop-color="{B['panel']}"/>
          <stop offset="1" stop-color="#0b1830"/>
        </linearGradient>
        <linearGradient id="accent" x1="0" y1="0" x2="1" y2=".7">
          <stop offset="0" stop-color="{B['cyan']}"/>
          <stop offset="1" stop-color="{B['blue']}"/>
        </linearGradient>
        <linearGradient id="cardfill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="{B['panel_alt']}"/>
          <stop offset="1" stop-color="{B['panel']}"/>
        </linearGradient>
        <pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1" fill="{B['cyan']}" opacity=".13"/>
        </pattern>
        <clipPath id="rounded"><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="24"/></clipPath>
      </defs>
    '''
    bg = rect(1, 1, width-2, height-2, 'url(#bg)', 24, B['line'], 1.2)
    decor = f'<g clip-path="url(#rounded)">{rect(0,0,width,height,"url(#dots)",0)}'
    decor += circle(width-40, -30, 210, B['blue'], 'opacity=".065"')
    decor += circle(width-70, height+90, 195, B['cyan'], 'opacity=".045"')
    decor += '</g>'
    title = txt(name)
    desc = txt(description or name)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
      <title id="title">{title}</title><desc id="desc">{desc}</desc>
      {defs}<style>{''.join(css)}</style>
      {bg}{decor}<g class="reveal">{inner}</g>
    </svg>\n'''


def arrow_icon(x, y):
    return f'<path d="M {x} {y+14} L {x+16} {y-2} M {x+5} {y-2} H {x+16} V {y+9}" stroke="{B["cyan"]}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'


def icon(name, x, y, scale=1):
    c = B['cyan']
    tr = f'transform="translate({x} {y}) scale({scale})"'
    if name == 'code':
        body = f'<path d="M -18 -10 L -30 0 L -18 10 M 18 -10 L 30 0 L 18 10 M 8 -20 L -8 20" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    elif name == 'network':
        body = f'{circle(-18,10,7,c)}{circle(17,-13,7,c)}{circle(20,19,7,c)}{line(-13,7,12,-10,c,3)}{line(-12,13,13,18,c,3)}{line(18,-5,19,11,c,3)}'
    else:
        body = f'<rect x="-30" y="-18" width="60" height="38" rx="5" fill="none" stroke="{c}" stroke-width="3"/><path d="M -27 -15 L 0 4 L 27 -15" fill="none" stroke="{c}" stroke-width="3"/>'
    return f'<g {tr}>{body}</g>'


def hero():
    w,h=1200,380
    inner = rect(45,42,6,290,'url(#accent)',3)
    inner += rect(79,45,231,33,'#163b57',16,B['line'])
    inner += el_text(96,67,'ENGINEER  /  BUILDER  /  CREATOR',12,fill=B['cyan'],weight=700,family='mono')
    inner += el_text(77,160,'Muhammad Sohail',66,weight=800)
    inner += el_text(80,203,'FULL STACK ENGINEER  /  NEXT.JS  /  NODE.JS',19,fill=B['cyan'],weight=700,family='mono')
    inner += el_text(80,244,CFG['tagline'],20,fill=B['muted'])
    inner += line(81,269,754,269,sw=1.3)
    for i,item in enumerate(CFG.get('focus',[])[:4]):
        x=80+i*173
        inner += rect(x,290,164,36,'#18314d',11,B['line'])
        inner += el_text(x+13,313,item,13,weight=650)
    inner += el_text(81,352,'15+ DIGITAL PROJECTS   /   PRODUCTION SYSTEMS   /   AI EXPLORATION',12,fill=B['muted'],family='mono',weight=600)
    inner += '<defs><clipPath id="portraitClip"><circle cx="1000" cy="184" r="110"/></clipPath></defs>'
    inner += circle(1000,184,135,'none',f'stroke="{B["cyan"]}" stroke-width="1.2" opacity=".30" stroke-dasharray="5 12" class="trace"')
    inner += circle(1000,184,122,'none',f'stroke="{B["blue"]}" stroke-width="2" opacity=".68"')
    inner += circle(1000,184,111,'#123b58')
    portrait = CFG.get('portrait_path')
    file = (ROOT / portrait).resolve() if portrait else None
    if file and file.is_file() and file.is_relative_to(ROOT.resolve()):
        if file.stat().st_size > 1024*1024:
            raise ValueError('Portrait exceeds 1 MB; compress it first')
        mime = mimetypes.guess_type(file.name)[0]
        if mime not in ('image/png','image/jpeg','image/webp'):
            raise ValueError('Portrait must be PNG, JPEG, or WebP')
        encoded = base64.b64encode(file.read_bytes()).decode('ascii')
        inner += f'<image href="data:{mime};base64,{encoded}" x="890" y="74" width="220" height="220" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>'
    else:
        inner += circle(1000,184,109,'#173550')
        inner += circle(1000,169,51,'#204d6e')
        inner += el_text(1000,188,'MS',49,weight=800,fill=B['text'],extra='text-anchor="middle"')
    inner += circle(1000,184,111,'none',f'stroke="{B["cyan"]}" stroke-width="3"')
    inner += circle(1097,104,9,B['cyan'],'class="glow"')
    inner += rect(884,310,232,31,'#143149',14,B['line'])
    inner += circle(903,326,5,'#56e4ae','class="glow"')
    inner += el_text(918,331,'OPEN TO COLLABORATION',13,fill=B['text'],weight=650,family='mono')
    if not STATIC:
        inner += f'<circle class="smil-only" cx="1097" cy="104" r="9" fill="{B["cyan"]}" opacity=".6"><animate attributeName="opacity" values=".4;1;.4" dur="3.5s" repeatCount="indefinite"/></circle>'
    return svg_shell('Muhammad Sohail — Full Stack Engineer',w,h,inner,description=CFG['tagline'],delay=.02)

def tile(link, delay):
    w,h=390,157
    inner=rect(24,23,70,70,'#173354',17,'#28537a')
    inner+=icon(link['icon'],59,58,.66)
    inner+=el_text(111,57,link['title'],24,weight=800)
    inner+=el_text(111,84,link['subtitle'],14,fill=B['muted'])
    inner+=line(25,115,365,115,sw=1.3)
    inner+=el_text(28,140,'EXPLORE',12,fill=B['cyan'],family='mono',weight=700)
    inner+=arrow_icon(344,123)
    return svg_shell(link['title'],w,h,inner,delay=delay,description=link['subtitle'])


def stats_from_data():
    days = DATA.get('days', [])
    if not days:
        return None
    seen=set(); parsed={}
    for item in days:
        d=dt.date.fromisoformat(item['date'])
        n=item['count']
        if not isinstance(n,int) or n<0 or d in seen:
            raise ValueError('Invalid, negative, or duplicate daily contribution data')
        seen.add(d);parsed[d]=n
    if len(parsed)<300:
        raise ValueError('Refusing to render incomplete contribution data (<300 days)')
    active=sum(n>0 for n in parsed.values())
    busiest=max(parsed,key=lambda d:parsed[d]); peak=parsed[busiest]
    last=max(parsed)
    # Today's 0 is not necessarily the end of an existing streak.
    anchor=last if parsed[last]>0 else last-dt.timedelta(days=1)
    streak=0
    while parsed.get(anchor,0)>0:
        streak+=1;anchor-=dt.timedelta(days=1)
    return {'days':parsed,'active':active,'streak':streak,'busiest':busiest,'peak':peak,'last':last}


def last_months(count=12):
    now=dt.date.today()
    year,month=now.year,now.month
    months=[]
    for _ in range(count):
        months.append((year,month))
        month-=1
        if month==0:
            month=12;year-=1
    return list(reversed(months))


def stats_card(stats):
    w,h=1200,343
    inner=rect(37,29,7,43,'url(#accent)',3)
    inner+=el_text(63,61,'CONTRIBUTION PULSE',30,weight=800)
    inner+=el_text(65,88,'Public GitHub activity  ·  Rolling 12-month overview',15,fill=B['muted'])
    if stats:
        total=DATA.get('total_contributions')
        values=[str(total if total is not None else '—'),str(stats['streak']),str(stats['active']),str(stats['peak'])]
        labels=['CONTRIBUTIONS','CURRENT STREAK','ACTIVE DAYS','BUSIEST DAY']
        foot=['GitHub calendar','consecutive days','days with activity',stats['busiest'].strftime('%d %b %Y')]
    else:
        values=['—']*4
        labels=['CONTRIBUTIONS','CURRENT STREAK','ACTIVE DAYS','BUSIEST DAY']
        foot=['Awaiting live data']*4
    for i in range(4):
        x=40+i*290
        inner+=rect(x,109,273,95,'url(#cardfill)',14,B['line'])
        inner+=el_text(x+18,133,labels[i],12,fill=B['muted'],family='mono',weight=600)
        inner+=el_text(x+18,172,values[i],35,fill=B['cyan'] if i==1 else B['text'],weight=800)
        inner+=el_text(x+105,175,foot[i],12,fill=B['muted'])
    inner+=el_text(45,231,'MONTHLY CONTRIBUTIONS',13,fill=B['muted'],family='mono',weight=700)
    months=last_months(12)
    counts=defaultdict(int)
    if stats:
        for day,n in stats['days'].items():
            counts[(day.year,day.month)]+=n
    top=max([counts[m] for m in months],default=0) or 1
    for i, ym in enumerate(months):
        x=62+i*93
        n=counts[ym]
        bh=max(3,round(60*n/top)) if stats else 3
        inner+=rect(x,311-bh,48,bh,'url(#accent)' if stats else '#203750',6)
        inner+=el_text(x+23,328,calendar.month_abbr[ym[1]],12,fill=B['muted'],weight=600,extra='text-anchor="middle"')
        if stats:
            inner+=el_text(x+24,244,str(n),11,fill=B['text'],weight=600,extra='text-anchor="middle"')
    if not stats:
        inner+=rect(335,261,540,43,'#182b44',10,B['line'])
        inner+=el_text(605,288,'Real statistics appear after the first GitHub Action run',15,fill=B['muted'],extra='text-anchor="middle"')
    return svg_shell('Monthly GitHub contributions and streak',w,h,inner,delay=.65)


def heatmap_card(stats):
    w,h=1200,275
    inner=rect(37,26,7,43,'url(#accent)',3)
    inner+=el_text(63,58,'CONTRIBUTION GRAPH',29,weight=800)
    inner+=el_text(64,83,'Actual daily public contribution counts, updated automatically',14,fill=B['muted'])
    if not stats:
        inner+=rect(45,112,1110,118,'#13243a',16,B['line'])
        inner+=el_text(600,165,'AWAITING VERIFIED GITHUB DATA',21,fill=B['cyan'],weight=700,extra='text-anchor="middle"')
        inner+=el_text(600,194,'The scheduled workflow will populate this chart. No activity has been invented.',14,fill=B['muted'],extra='text-anchor="middle"')
        return svg_shell('Contribution graph pending verified data',w,h,inner,delay=.9)
    days=stats['days'];end=stats['last']
    # Exactly 53 Sun-Sat weeks, ending with the current or next Saturday.
    saturday=end+dt.timedelta(days=(5-end.weekday())%7)
    start=saturday-dt.timedelta(days=370)
    x0=138;y0=112;step=17;cell=12
    levels=['#1c2e46','#0e526b','#087da6','#00b8dc',B['cyan']]
    max_count=max(days.values(),default=1)
    for col in range(53):
        for row in range(7):
            day=start+dt.timedelta(days=col*7+row)
            x=x0+col*step;y=y0+row*step
            if day not in days:
                color='#132237'
            else:
                n=days[day]
                idx=0 if n==0 else min(4,max(1,math.ceil(4*n/max(1,max_count))))
                color=levels[idx]
            inner+=rect(x,y,cell,cell,color,3)
    for i,lab in [(1,'Mon'),(3,'Wed'),(5,'Fri')]:
        inner+=el_text(92,y0+i*step+10,lab,12,fill=B['muted'])
    last_month=-1
    for col in range(53):
        day=start+dt.timedelta(days=col*7)
        if day.month!=last_month:
            inner+=el_text(x0+col*step,101,calendar.month_abbr[day.month],11,fill=B['muted'])
            last_month=day.month
    inner+=el_text(141,250,'LESS',11,fill=B['muted'],family='mono')
    for i,color in enumerate(levels):
        inner+=rect(187+i*20,239,14,14,color,3)
    inner+=el_text(294,250,'MORE',11,fill=B['muted'],family='mono')
    stamp=DATA.get('updated_at') or ''
    date=stamp[:10] if stamp else 'Not refreshed'
    inner+=el_text(1150,250,'Updated '+date,12,fill=B['muted'],extra='text-anchor="end"')
    return svg_shell('GitHub daily contribution graph',w,h,inner,delay=.9)


def wrap(s,limit=69,lines=2):
    words=s.split();out=[];cur=''
    for word in words:
        if len(cur+' '+word)>limit and cur:
            out.append(cur);cur=word
        else:
            cur=(cur+' '+word).strip()
    if cur:out.append(cur)
    if len(out)>lines:
        out=out[:lines]
        out[-1]=out[-1][:max(0,limit-1)].rstrip(' .')+'…'
    return out


def slug(s):
    return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')


def repo_card(item,i):
    w,h=580,216
    repo=item['repo']
    meta=DATA.get('repos',{}).get(repo,{})
    inner=rect(22,23,5,157,'url(#accent)',2)
    inner+=rect(42,23,44,30,'#163c58',9,B['line'])
    inner+=el_text(64,44,f'{i:02d}',14,fill=B['cyan'],weight=750,family='mono',extra='text-anchor="middle"')
    inner+=el_text(100,49,item['name'],23,weight=800)
    lang=meta.get('language') or 'GITHUB PROJECT'
    inner+=el_text(44,80,'FEATURED REPOSITORY   /   '+str(lang).upper(),11,fill=B['cyan'],weight=700,family='mono')
    for j,line_text in enumerate(wrap(item['description'],65,2)):
        inner+=el_text(44,109+j*21,line_text,14,fill=B['muted'])
    x=44
    for tag in item.get('tags',[])[:3]:
        width=max(80,min(150,18+len(tag)*8))
        inner+=rect(x,155,width,25,'#173550',9,B['line'])
        inner+=el_text(x+9,172,tag,11,weight=650)
        x+=width+9
    inner+=line(44,188,537,188,sw=1.1)
    stars=f"{meta['stars']} STARS" if meta and 'stars' in meta else 'PUBLIC REPOSITORY'
    inner+=el_text(45,207,stars,12,fill=B['muted'],family='mono',weight=650)
    inner+=el_text(396,207,'VIEW SOURCE',12,fill=B['cyan'],family='mono',weight=700)
    inner+=arrow_icon(536,194)
    return svg_shell(item['name']+' featured repository',w,h,inner,delay=1.25+i*.10,description=item['description'])


def expertise_card():
    w,h=1200,270
    inner=rect(38,28,6,42,'url(#accent)',3)
    inner+=el_text(63,61,'ENGINEERING CAPABILITIES',29,weight=800)
    inner+=el_text(64,87,'From polished interfaces to reliable services and data-driven products',15,fill=B['muted'])
    panels=[
        ('01','FRONTEND','React / Next.js','TypeScript / Accessible UI'),
        ('02','BACKEND','Node.js / Express.js','REST APIs / Integrations'),
        ('03','DATA & SYSTEMS','MySQL / PostgreSQL','MongoDB / Firebase'),
        ('04','INTELLIGENT APPS','LLMs / RAG / Embeddings','MCP / Agent Workflows')]
    for i,(num,title,first,second) in enumerate(panels):
        x=39+i*291
        inner+=rect(x,112,273,130,'url(#cardfill)',16,B['line'])
        inner+=rect(x+15,128,43,30,'#143c5a',10,B['line'])
        inner+=el_text(x+36,149,num,14,fill=B['cyan'],weight=700,family='mono',extra='text-anchor="middle"')
        inner+=el_text(x+15,185,title,17,weight=800)
        inner+=el_text(x+15,211,first,14,fill=B['muted'])
        inner+=el_text(x+15,232,second,13,fill=B['muted'])
    return svg_shell('Engineering capabilities',w,h,inner,delay=.54)


def stack_card():
    w,h=1200,262
    inner=rect(38,27,6,42,'url(#accent)',3)
    inner+=el_text(63,60,'THE STACK',29,weight=800)
    inner+=el_text(64,87,'Technologies I use to design, ship and maintain modern applications',15,fill=B['muted'])
    rows=[('FRONTEND',['React.js','Next.js','TypeScript','Tailwind','Framer Motion','GSAP','Three.js']),
          ('BACKEND',['Node.js','Express.js','REST APIs','Authentication','Electron.js']),
          ('DATA + WORKFLOW',['MySQL','PostgreSQL','MongoDB','Firebase','Git','GitHub','Figma'])]
    for i,(label,items) in enumerate(rows):
        y=113+i*45
        inner+=el_text(50,y+20,label,14,fill=B['cyan'],weight=750,family='mono')
        x=272
        for item in items:
            width=max(87,round(len(item)*8.7)+23)
            inner+=rect(x,y,width,31,'#172e49',9,B['line'])
            inner+=el_text(x+12,y+21,item,13,weight=650)
            x+=width+10
    return svg_shell('Technology stack',w,h,inner,delay=.70)


def focus_card():
    w,h=1200,248
    inner=rect(38,27,6,42,'url(#accent)',3)
    inner+=el_text(63,60,'CURRENTLY EXPLORING',29,weight=800)
    inner+=el_text(64,86,'Building on full-stack foundations with modern AI and interface engineering',15,fill=B['muted'])
    panels=[('AI ENGINEERING','LLMs, RAG and embeddings','Vector databases / MCP / agents'),
            ('INTERACTIVE UI','Three.js, GSAP and Framer Motion','Performance / motion / accessibility'),
            ('PRODUCT ENGINEERING','API architecture and integrations','Maintainability / scalability / SEO')]
    for i,(title,a,b) in enumerate(panels):
        x=38+i*390
        inner+=rect(x,109,370,110,'url(#cardfill)',15,B['line'])
        inner+=rect(x+15,127,4,66,'url(#accent)',2)
        inner+=el_text(x+33,143,title,18,weight=800)
        inner+=el_text(x+33,174,a,15,fill=B['muted'])
        inner+=el_text(x+33,199,b,13,fill=B['muted'])
    return svg_shell('Current engineering focus',w,h,inner,delay=2.60)


def project_card(item,i):
    w,h=580,216
    inner=rect(22,23,5,158,'url(#accent)',2)
    inner+=rect(42,23,44,30,'#163c58',9,B['line'])
    inner+=el_text(64,44,f'{i:02d}',14,fill=B['cyan'],weight=750,family='mono',extra='text-anchor="middle"')
    inner+=el_text(100,49,item['name'],23,weight=800)
    inner+=el_text(44,80,item['type'].upper(),11,fill=B['cyan'],weight=700,family='mono')
    for j,line_text in enumerate(wrap(item['description'],65,2)):
        inner+=el_text(44,109+j*21,line_text,14,fill=B['muted'])
    x=44
    for tag in item.get('tags',[])[:3]:
        width=max(80,min(150,18+len(tag)*8))
        inner+=rect(x,155,width,25,'#173550',9,B['line'])
        inner+=el_text(x+9,172,tag,11,weight=650)
        x+=width+9
    inner+=line(44,188,537,188,sw=1.1)
    inner+=el_text(46,207,'VIEW LIVE PROJECT',12,fill=B['cyan'],family='mono',weight=700)
    inner+=arrow_icon(536,194)
    return svg_shell(item['name']+' live project',w,h,inner,delay=1.80+i*.09,description=item['description'])


def footer_card():
    w,h=1200,181
    inner=rect(37,27,6,126,'url(#accent)',3)
    inner+=el_text(65,79,"LET'S BUILD SOMETHING USEFUL.",38,weight=800)
    inner+=el_text(67,116,'Full-stack engineering  /  Product collaboration  /  AI-powered applications',18,fill=B['muted'])
    inner+=el_text(68,149,'sohail.dev07@gmail.com',17,fill=B['cyan'],weight=700,family='mono')
    inner+=circle(1062,88,55,'none',f'stroke="{B["cyan"]}" stroke-width="2" opacity=".7" class="trace"')
    inner+=el_text(1062,98,'MS',34,weight=800,extra='text-anchor="middle"')
    return svg_shell('Contact Muhammad Sohail',w,h,inner,delay=3.05)


def main():
    global FONTS
    if DATA.get('username')!=CFG['username']:
        raise ValueError('Contribution JSON username does not match config.json')
    if len(CFG['links'])!=3:
        raise ValueError('Exactly three linked tiles are required')
    if len(CFG.get('other_projects',[]))!=10 or len(CFG['featured_repos'])!=5:
        raise ValueError('Expected 5 featured repositories and 10 additional projects')
    for c in B.values():
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',c):
            raise ValueError('Brand colours must be six-digit hex values')
    OUT.mkdir(exist_ok=True)
    FONTS=make_embedded_fonts()
    stats=stats_from_data()
    cards={'hero.svg':hero(), 'expertise.svg':expertise_card(), 'tech-stack.svg':stack_card(),
           'stats.svg':stats_card(stats), 'contribution-graph.svg':heatmap_card(stats),
           'focus.svg':focus_card(), 'footer.svg':footer_card()}
    for i,link in enumerate(CFG['links']):
        cards[f'tile-{link["key"]}.svg']=tile(link,.17+i*.14)
    for i,item in enumerate(CFG['featured_repos'],1):
        cards['repo-'+slug(item['repo'].split('/')[-1])+'.svg']=repo_card(item,i)
    for i,item in enumerate(CFG['other_projects'],1):
        cards['project-'+slug(item['name'])+'.svg']=project_card(item,i)
    for name,content in cards.items():
        (OUT/name).write_text(content,encoding='utf-8')
    print(f'Rendered {len(cards)} self-contained SVG cards into {OUT.relative_to(ROOT)}/ ({"STATIC" if STATIC else "animated"} mode).')
    if not stats:
        print('Contribution statistics pending: run GitHub Action to fetch verified data.')
    if CFG.get('portrait_path') and not (ROOT/CFG['portrait_path']).is_file():
        print('GitHub portrait pending: run GitHub Action to fetch and embed profile avatar.')


if __name__=='__main__':
    main()
