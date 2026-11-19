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
    w,h = 1200,306
    inner = rect(44,43,5,212,'url(#accent)',2)
    inner += rect(69,41,207,33,'#183451',16)
    inner += el_text(88,63,'ENGINEERING PORTFOLIO',14,fill=B['cyan'],weight=700,family='mono')
    inner += el_text(70,139,CFG['name'],62,weight=800)
    inner += el_text(73,179,CFG['role'],23,fill=B['cyan'],weight=600)
    inner += el_text(73,218,CFG['tagline'],19,fill=B['muted'])
    inner += line(73,246,720,246,sw=1.5)
    for i, item in enumerate(CFG.get('focus',[])[:4]):
        x=73+i*163
        inner += rect(x,261,155,29,'#182943',12,B['line'])
        inner += el_text(x+10,280,item,12,fill=B['text'],weight=600)
    portrait = CFG.get('portrait_path')
    if portrait:
        file = (ROOT / portrait).resolve()
        if not file.is_file() or not str(file).startswith(str(ROOT.resolve())):
            raise ValueError('portrait_path must be an existing file inside the repository')
        if file.stat().st_size > 1024*1024:
            raise ValueError('Portrait exceeds 1 MB; compress it first')
        mime = mimetypes.guess_type(file.name)[0]
        if mime not in ('image/png','image/jpeg','image/webp'):
            raise ValueError('Portrait must be PNG, JPEG, or WebP')
        encoded = base64.b64encode(file.read_bytes()).decode('ascii')
        inner += '<defs><clipPath id="portraitClip"><circle cx="994" cy="150" r="96"/></clipPath></defs>'
        inner += f'<image href="data:{mime};base64,{encoded}" x="898" y="54" width="192" height="192" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>'
        inner += circle(994,150,97,'none',f'stroke="{B["cyan"]}" stroke-width="3"')
    else:
        inner += rect(842,48,291,211,'#102440',23,'#2a5981',1.5)
        inner += rect(861,67,253,30,'#172f4b',9)
        for cx,color in [(881,'#ff6b79'),(901,'#ffd27d'),(921,'#72e2bd')]:
            inner += circle(cx,82,4,color)
        inner += el_text(869,124,'const developer = {',18,fill=B['cyan'],family='mono')
        inner += el_text(884,155,'focus: "reliability",',16,fill=B['text'],family='mono')
        inner += el_text(884,185,'stack: "full-stack",',16,fill=B['text'],family='mono')
        inner += el_text(869,217,'};',18,fill=B['cyan'],family='mono')
        inner += circle(1107,246,20,B['cyan'],'opacity=".13" class="glow"')
        if not STATIC:
            inner += f'<circle class="smil-only" cx="1107" cy="246" r="9" fill="{B["cyan"]}" opacity=".55"><animate attributeName="opacity" values="0.45;0.95;0.45" dur="3.6s" repeatCount="indefinite"/></circle>'
        else:
            inner += circle(1107,246,9,B['cyan'],'opacity=".7"')
    return svg_shell('Muhammad Sohail profile hero',w,h,inner,description=CFG['tagline'])


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
    w,h=1200,189
    repo=item['repo']
    meta=DATA.get('repos',{}).get(repo,{})
    inner=rect(34,30,7,127,'url(#accent)',3)
    inner+=rect(58,30,65,39,'#153756',12,B['line'])
    inner+=el_text(91,56,f'{i:02d}',19,fill=B['cyan'],weight=700,family='mono',extra='text-anchor="middle"')
    inner+=el_text(145,60,item['name'],29,weight=800)
    inner+=el_text(145,89,'PUBLIC REPOSITORY  /  FEATURED WORK',12,fill=B['cyan'],family='mono',weight=600)
    for j,text in enumerate(wrap(item['description'],82,2)):
        inner+=el_text(145,118+j*23,text,17,fill=B['muted'])
    x=145
    for tag in item.get('tags',[])[:4]:
        width=max(88, min(180,18+len(tag)*8))
        inner+=rect(x,157,width,25,'#193550',10,B['line'])
        inner+=el_text(x+10,174,tag,12,fill=B['text'],weight=600)
        x+=width+10
    inner+=rect(960,39,198,112,'#112841',17,'#275176')
    if meta:
        inner+=el_text(978,71,'★  '+str(meta['stars'])+'  STARS',17,fill=B['cyan'],weight=700)
        inner+=el_text(978,99,'LANGUAGE',11,fill=B['muted'],family='mono')
        inner+=el_text(978,123,meta.get('language') or 'Not specified',18,weight=600)
    else:
        inner+=el_text(978,74,'VIEW SOURCE',19,fill=B['cyan'],weight=700)
        inner+=el_text(978,102,'Open on GitHub',14,fill=B['muted'])
        inner+=arrow_icon(1122,119)
    return svg_shell(item['name']+' featured repository',w,h,inner,delay=1.05+i*.13,description=item['description'])


def main():
    global FONTS
    if DATA.get('username')!=CFG['username']:
        raise ValueError('Contribution JSON username does not match config.json')
    if len(CFG['links'])!=3:
        raise ValueError('Exactly three linked tiles are required')
    for c in B.values():
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',c):
            raise ValueError('Brand colours must be six-digit hex values')
    OUT.mkdir(exist_ok=True)
    FONTS=make_embedded_fonts()
    stats=stats_from_data()
    cards={'hero.svg':hero(), 'stats.svg':stats_card(stats), 'contribution-graph.svg':heatmap_card(stats)}
    for i,link in enumerate(CFG['links']):
        cards[f'tile-{link["key"]}.svg']=tile(link,.16+i*.16)
    for i,item in enumerate(CFG['featured_repos'],1):
        cards['repo-'+slug(item['repo'].split('/')[-1])+'.svg']=repo_card(item,i)
    for name,content in cards.items():
        (OUT/name).write_text(content,encoding='utf-8')
    print(f'Rendered {len(cards)} self-contained SVG cards into {OUT.relative_to(ROOT)}/ ({"STATIC" if STATIC else "animated"} mode).')
    if not stats:
        print('No real GitHub contribution data yet; statistics explicitly display pending, not fabricated values.')


if __name__=='__main__':
    main()
