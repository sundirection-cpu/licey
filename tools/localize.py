"""Скачивает картины и музыку с Wikimedia к себе (media/), сжимает и переписывает ссылки в data.js.
Запускать после build.py. Уже скачанное повторно не качается."""
import json, os, re, subprocess, time, hashlib, urllib.request, io
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
UA = {'User-Agent': 'LiceyBuilder/1.0 (https://github.com/sundirection-cpu/licey; educational app)'}
DATA = os.path.join(ROOT, 'data.js')
raw = open(DATA).read()
d = json.loads(raw[raw.index('=')+1:].strip().rstrip(';'))

def fetch(url):
    for i in range(10):
        try:
            time.sleep(3.0)
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        except Exception as e:
            print('  retry', i, e); time.sleep(30*(i+1))
    raise RuntimeError(url)

def slug(s):
    return hashlib.md5(s.encode()).hexdigest()[:10]

def image(m, maxside, q):
    if not m or m['src'].startswith('media/'): return
    name = f"media/img/{slug(m['page'])}-{maxside}.webp"
    path = os.path.join(ROOT, name)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im = Image.open(io.BytesIO(fetch(m['src']))).convert('RGB')
        im.thumbnail((maxside, maxside), Image.LANCZOS)
        im.save(path, 'WEBP', quality=q, method=6)
        print('img', name, os.path.getsize(path)//1024, 'KB')
    m['remote'] = m['src']; m['src'] = name

def audio(m):
    if m['src'].startswith('media/'): return
    name = f"media/audio/{slug(m['page'])}.mp3"
    path = os.path.join(ROOT, name)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.src'
        open(tmp, 'wb').write(fetch(m['src']))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-vn', '-ac', '2', '-ar', '44100', '-b:a', '96k', path], check=True)
        os.remove(tmp)
        print('aud', name, os.path.getsize(path)//1024, 'KB')
    m['remote'] = m['src']; m['src'] = name; m.pop('alt', None)

for key in ('art', 'music', 'lit'):
    for ch in d[key]:
        for t in ch.get('traits', []):
            if isinstance(t, dict) and t.get('img'): image(t['img'], 1000, 80)
        for f in ch.get('figs', {}).values(): image(f['img'], 1200, 80)
for ch in d['art']:
    for w in ch['works']: image(w['img'], 1000, 80)
for ch in d['lit']:
    for w in ch['works']: image(w.get('img'), 360, 82)
for ch in d['music']:
    for w in ch['works']: audio(w['audio'])
open(DATA, 'w').write('window.LICEY_DATA = ' + json.dumps(d, ensure_ascii=False) + ';\n')
print('done')
