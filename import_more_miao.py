# -*- coding: utf-8 -*-
"""补充导入新苗族音乐(清理后的库 v2)。append-only, 复用清理规则防噪声。"""
import os, re, sys, json, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ['MRE_ONLY_GROUP'] = 'e04'
sys.path.insert(0, str(ROOT / 'webui'))
import mountainriverechoes as m
from musicdl.modules import SongInfo

CACHE = ROOT / 'webui' / 'ethnos_cache' / 'e04_苗族.json'
REPORT = ROOT / 'import_more_miao_report.txt'

CYR = re.compile(r'[\u0400-\u04FF]')
THAI = re.compile(r'[\u0E00-\u0E7F]')
NON_MUSIC = ('演讲','教程','听书','有声','相声','评书','配音','朗读','新闻','广告','课程','讲座','百家讲坛','散文','小说','段子','脱口秀','公开课','微课','读书','播客','快板','贯口','朗诵')
MIAO_MARK = ('苗','芦笙','芦苼','飞歌','古歌','巴茅','雷山','西江','锦鸡','反排','苗年','牯藏','姊妹节','讨花带','游方','岜沙','台江','施洞','Hxak','阿卯','Hmong','Hmoob','Moob','Kwv','Nkauj','Niam','Hlub')
# 清理规则同 apply_filter
JUNK = re.compile(r'指尖江湖|剑网|剑三|剑侠|木桩|打桩|吃鸡|三角洲|倩女|cos|Cos|COS|舞团|整蛊|陀螺|小哥|小妹|旺夫|相亲|搞笑|实拍|第\d+集|的创作原声|lv_0_|studio_video|videoplayback|VTS_0|VID_20|合集|原版MV|高清修复|AI山歌|车载dj|串烧|DJ版|嗨曲|降调|Solid|Remix|remix|伴奏|纯音乐版')
EN_PAT = re.compile(r'[A-Za-z]{4,}')
CN_PAT = re.compile(r'[\u4e00-\u9fff]')

# 新检索词(与旧导入不重复)
KW_MIAO = ['苗族酒歌','苗族大歌','苗族舞曲','锦鸡舞','苗族敬酒歌','苗寨','苗家','苗族对唱','苗族儿歌','苗族笛子','Hmoob','nkauj hmoob','苗族古歌镇远','苗族唢呐','贵州苗族']
KW_SINGER = ['蝶长','央格里','叠贵','金竹乐队','杨胜文','古阿新','朵久央','阿音坊组合','欧桑','雷艳','阿蕾娥','阿朵','杨胜美','潘兴周']
KW_ALL = KW_MIAO + KW_SINGER

def has_dl(s):
    du = s.download_url
    return isinstance(du, str) and (du.startswith('http') or du.startswith('ytdlp:') or 'res.wx.qq.com' in du)

def hmongish(name):
    return any(k in name for k in ('Hmoob','Moob','Kwv','Nkauj','Niam','Hlub','Hmong','Hxak','Phooj','Kuv','Koj'))

def should_keep(kw, s):
    name = s.song_name or ''
    singers = str(s.singers or '')
    if CYR.search(name + singers) or THAI.search(name):
        return False
    if any(k in name for k in NON_MUSIC):
        return False
    if JUNK.search(name + ' ' + singers):
        return False
    if kw in KW_SINGER:
        # 歌手检索: 歌名需带苗标记, 或歌手名本身就是苗族组合(金竹乐队/古阿新/阿音坊/央格里/阿卯等)且歌名非纯英文噪声
        if not any(k in name for k in MIAO_MARK):
            PURE_MIAO_ARTIST = any(a in singers for a in ('金竹','古阿新','阿音坊','央格里','阿卯','蝶长','叠贵','朵久央','欧桑','阿蕾娥'))
            if not (PURE_MIAO_ARTIST and CN_PAT.search(name)):
                return False
    if EN_PAT.search(name) and not CN_PAT.search(name) and not hmongish(name):
        return False
    if not has_dl(s):
        return False
    return True

doc = json.loads(CACHE.read_text(encoding='utf-8'))
existing = set()
for t in (doc.get('tracks') or []):
    try:
        si = SongInfo.fromdict(t.get('_song') or {})
        if si.song_name:
            existing.add(m._dedup_key(si))
    except Exception:
        pass
print(f'[现有库] {len(existing)} 个去重键', flush=True)

client = m._ethnos_get_client()
accepted, seen_new = [], set()
stats = defaultdict(lambda: {'hit': 0, 'kept': 0})
t0 = time.time()
for kw in KW_ALL:
    try:
        res = m._search_ethnos_keyword(client, kw)
    except Exception as e:
        print(f'[{kw}] 检索失败 {e}', flush=True)
        continue
    print(f'[{kw}] 命中 {len(res)}', flush=True)
    for s in res:
        if not s.song_name:
            continue
        stats[kw]['hit'] += 1
        if not should_keep(kw, s):
            continue
        key = m._dedup_key(s)
        if key in existing or key in seen_new:
            continue
        seen_new.add(key)
        accepted.append((s, kw))
        stats[kw]['kept'] += 1

elapsed = round(time.time() - t0, 1)
print(f'\n[过滤后] 拟新增 {len(accepted)} 首 (耗时 {elapsed}s)', flush=True)

def real_source(s):
    real = (s.source or '').removesuffix('MusicClient')
    if isinstance(s.download_url, str) and s.download_url.startswith('ytdlp:'):
        real = 'Bilibili' if 'bilibili.com' in s.download_url else 'YouTube'
    elif isinstance(s.download_url, str) and 'res.wx.qq.com' in s.download_url:
        real = '光音·微信'
    return real

def make_track(s, idx):
    brief = m.song_brief(s, 'Ethnos', idx)
    real = real_source(s)
    brief['source'] = real or 'Ethnos'
    brief['source_cn'] = m.SOURCE_NAMES.get(real, real) if real else '民族音乐'
    if not brief['duration'] or ':' not in brief['duration']:
        brief['duration'] = ''
    return dict(brief, _song=m._slim_song(s.todict()))

old_count = len(doc['tracks'])
new_tracks = [make_track(s, i) for i, (s, _) in enumerate(accepted)]
doc['tracks'] = doc['tracks'] + new_tracks
doc['count'] = len(doc['tracks'])
doc['partial'] = False
m._atomic_write_json(CACHE, doc)
print(f'[入库] {old_count} -> {doc["count"]} (新增 {len(new_tracks)})', flush=True)

by_src = Counter(real_source(s) for s, _ in accepted)
lines = ['苗族库 · 补充导入报告', f'时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
         f'耗时: {elapsed}s  检索词 {len(KW_ALL)} 个',
         f'库: {old_count} -> {doc["count"]} (新增 {len(new_tracks)})', '',
         '== 各词 命中/保留 ==']
for kw in KW_ALL:
    st = stats[kw]
    lines.append(f'  {kw:<12} [{"词" if kw in KW_MIAO else "歌手"}] 命中 {st["hit"]:<4} 保留 {st["kept"]}')
lines += ['', '== 新增按音源 =='] + [f'  {s}: {n}' for s, n in by_src.most_common()]
lines += ['', '== 新增明细 =='] + [f'  - {s.song_name} / {s.singers} [{real_source(s)}] ({kw})' for s, kw in accepted]
REPORT.write_text('\n'.join(lines), encoding='utf-8')
print('报告:', REPORT)
