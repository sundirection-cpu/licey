"""Сборка data.js: проверяет файлы на Wikimedia Commons и страницы Викитеки, подставляет прямые ссылки."""
import json, os, re, sys
from search import api
sys.path.insert(0, os.path.dirname(__file__))
from content_art import ART
from content_music import MUSIC
from content_lit import LIT
from content_extra import EXTRA

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache.json')
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

def strip_html(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()

def resolve_files(names, audio=False):
    todo = [n for n in names if n and ('F:'+n) not in cache]
    for i in range(0, len(todo), 40):
        chunk = todo[i:i+40]
        p = {'action':'query','titles':'|'.join('File:'+n for n in chunk),'redirects':1}
        if audio:
            p.update(prop='videoinfo', viprop='url|derivatives|extmetadata')
        else:
            p.update(prop='imageinfo', iiprop='url|extmetadata', iiurlwidth=1000)
        r = api(p)
        q = r['query']
        norm = {x['to']:x['from'] for x in q.get('normalized', [])}
        redir = {x['to']:x['from'] for x in q.get('redirects', [])}
        for page in q['pages'].values():
            t = page['title']
            orig = redir.get(t, t); orig = norm.get(orig, orig)
            name = orig[5:]
            info = (page.get('videoinfo') or page.get('imageinfo') or [None])[0]
            if not info:
                cache['F:'+name] = None; continue
            md = info.get('extmetadata', {})
            rec = {'page': info.get('descriptionurl'),
                   'lic': strip_html(md.get('LicenseShortName', {}).get('value')),
                   'by': strip_html(md.get('Artist', {}).get('value'))[:80]}
            if audio:
                src = info['url']
                ders = info.get('derivatives', [])
                mp3 = [d['src'] for d in ders if 'mpeg' in d.get('type','') or d['src'].endswith('.mp3')]
                oggv = [d['src'] for d in ders if 'vorbis' in d.get('type','')]
                rec['src'] = mp3[0] if mp3 else src
                rec['alt'] = src
            else:
                rec['src'] = info.get('thumburl') or info['url']
                rec['w'] = info.get('thumbwidth'); rec['h'] = info.get('thumbheight')
            cache['F:'+name] = rec
        json.dump(cache, open(CACHE,'w'), ensure_ascii=False, indent=0)

def resolve_ws(titles):
    todo = [t for t in titles if t and ('W:'+t) not in cache]
    for i in range(0, len(todo), 40):
        chunk = todo[i:i+40]
        r = api({'action':'query','titles':'|'.join(chunk),'redirects':1}, host='ru.wikisource.org')
        q = r['query']
        norm = {x['from']:x['to'] for x in q.get('normalized', [])}
        redir = {x['from']:x['to'] for x in q.get('redirects', [])}
        pages = {p['title']:p for p in q['pages'].values()}
        for t in chunk:
            tt = norm.get(t, t); tt = redir.get(tt, tt)
            p = pages.get(tt)
            cache['W:'+t] = tt if p and 'missing' not in p else None
        json.dump(cache, open(CACHE,'w'), ensure_ascii=False, indent=0)

missing = []
def _ef(e):
    out=[]
    for g in e.get('groups', []): out += [i['f'] for i in g['items'] if i.get('f')]
    out += [t['f'] for t in e.get('traits', []) if isinstance(t, dict) and t.get('f')]
    for x in e.get('figs', {}).values(): out += [x[k] for k in ('f','f2') if x.get(k)]
    return out
extra_files = [f for e in EXTRA.values() for f in _ef(e)]
resolve_files(extra_files)
resolve_files([w['f'] for ch in ART for w in ch['works']])
resolve_files([w.get('img') for ch in LIT for w in ch['works']])
resolve_files([w['f'] for ch in MUSIC for w in ch['works']], audio=True)
resolve_ws([w['ws'] for ch in LIT for w in ch['works']])

def media(name):
    r = cache.get('F:'+name) if name else None
    if name and not r: missing.append(name)
    return r

out = {'art':[], 'music':[], 'lit':[]}
for key, src, fld in (('art',ART,'f'),('music',MUSIC,'f'),('lit',LIT,'img')):
    for ch in src:
        ch = json.loads(json.dumps(ch))
        works = []
        for w in ch['works']:
            m = media(w.pop(fld, None))
            if key == 'art':
                if not m: continue
                w['img'] = m
            elif key == 'music':
                if not m: continue
                w['audio'] = m
            else:
                if m: w['img'] = m
                ws = cache.get('W:'+w['ws'])
                if not ws: missing.append('WS:'+w['ws'])
                w['ws'] = ws
            works.append(w)
        ch['works'] = works
        ex = EXTRA.get(ch['id'])
        if ex:
            for k in ('why', 'intro'):
                if k in ex: ch[k] = ex[k]
            if ex.get('groups'):
                ch['groups'] = [{'h': g['h'], 'p': g.get('p', ''), 'items': [dict({k: v for k, v in i.items() if k != 'f'}, img=media(i['f'])) for i in g['items'] if media(i.get('f'))]} for g in ex['groups']]
            if ex.get('figs'):
                ch['figs'] = {}
                for k, v in ex['figs'].items():
                    m = media(v['f'])
                    if not m: continue
                    fg = {'c': v.get('c', ''), 'img': m}
                    if v.get('f2') and media(v['f2']): fg.update(img2=media(v['f2']), c1=v.get('c1', ''), c2=v.get('c2', ''))
                    ch['figs'][str(k)] = fg
            for w in ch['works']:
                st = ex.get('stories', {}).get(w['t'])
                if st: w['story'] = st
        out[key].append(ch)

with open(os.path.join(HERE, '..', 'data.js'), 'w') as f:
    f.write('window.LICEY_DATA = ' + json.dumps(out, ensure_ascii=False) + ';\n')
print('missing:', *missing, sep='\n  ')
