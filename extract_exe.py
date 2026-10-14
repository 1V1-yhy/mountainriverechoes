'''从打包好的 EXE 中抽取被冻结的数据文件(模板 + 苗族歌单 JSON), 验证打包内容。'''
import os, sys, json

EXE = os.path.join(os.path.dirname(__file__), 'dist', 'miao_player.exe')
OUT = os.path.join(os.path.dirname(__file__), 'extracted_exe')
os.makedirs(OUT, exist_ok=True)

from PyInstaller.archive.readers import CArchiveReader

targets = [
    'webui\\templates\\mountainriverechoes.html',
    'webui\\ethnos_cache\\e04_苗族.json',
]

found = {}
ar = CArchiveReader(EXE)
try:
    names = list(ar.toc.keys())
    print('archive entries:', len(names))
    for t in targets:
        if t not in ar.toc:
            print('MISSING in EXE:', t)
            continue
        data = ar.extract(t)
        outp = os.path.join(OUT, os.path.basename(t))
        with open(outp, 'wb') as f:
            f.write(data)
        found[t] = outp
        print('EXTRACTED', t, '->', outp, 'bytes=', len(data))
finally:
    ar.close()

# 校验 JSON 曲目数
if found.get('webui/ethnos_cache/e04_苗族.json'):
    d = json.load(open(found['webui/ethnos_cache/e04_苗族.json'], encoding='utf-8'))
    print('BUNDLED_JSON tracks =', len(d.get('tracks', [])))
    print('BUNDLED_JSON count  =', d.get('count'))

# 校验模板首页板块
if found.get('webui/templates/mountainriverechoes.html'):
    html = open(found['webui/templates/mountainriverechoes.html'], encoding='utf-8', errors='ignore').read()
    for mk in ['苗族曲库', '为你精选', '热门歌手', '猜你喜欢', 'miao-picks', 'skin-miao']:
        print('BUNDLED_HTML', mk, '=', mk in html)
