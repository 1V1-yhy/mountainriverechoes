# -*- coding: utf-8 -*-
"""补充导入新苗族音乐(第3批, 针对库内缺口)。健壮+断点续跑:
- 每完成一个关键词即把候选写入 staging JSON(done_kws 标记), 崩溃可续跑
- 全部关键词跑完且仅在成功后才原子合并进库
- 复用 should_keep 防噪; 与现有库去重
"""
import os, re, sys, json, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ['MRE_ONLY_GROUP'] = 'e04'
sys.path.insert(0, str(ROOT / 'webui'))
import mountainriverechoes as m
from musicdl.modules import SongInfo

CACHE = ROOT / 'webui' / 'ethnos_cache' / 'e04_苗族.json'
STAGE = ROOT / 'import_more3_candidates.json'
REPORT = ROOT / 'import_more3_report.txt'

CYR = re.compile(r'[\u0400-\u04FF]')
THAI = re.compile(r'[\u0E00-\u0E7F]')
NON_MUSIC = ('演讲','教程','听书','有声','相声','评书','配音','朗读','新闻','广告','课程','讲座','百家讲坛','散文','小说','段子','脱口秀','公开课','微课','读书','播客','快板','贯口','朗诵')
MIAO_MARK = ('苗','芦笙','芦苼','飞歌','古歌','巴茅','雷山','西江','锦鸡','反排','苗年','牯藏','姊妹节','讨花带','游方','岜沙','台江','施洞','Hxak','阿卯','Hmong','Hmoob','Moob','Kwv','Nkauj','Niam','Hlub')
JUNK = re.compile(r'指尖江湖|剑网|剑三|剑侠|木桩|打桩|吃鸡|三角洲|倩女|cos|Cos|COS|舞团|整蛊|陀螺|小哥|小妹|旺夫|相亲|搞笑|实拍|第\d+集|的创作原声|lv_0_|studio_video|videoplayback|VTS_0|VID_20|合集|原版MV|高清修复|AI山歌|车载dj|串烧|DJ版|嗨曲|降调|Solid|Remix|remix|伴奏|纯音乐版|漫剧|短剧|二次元|动画|游戏|儿歌|早教|宝宝|抖音|广场舞')
EN_PAT = re.compile(r'[A-Za-z]{4,}')
CN_PAT = re.compile(r'[\u4e00-\u9fff]')

# 第3批检索词(地域/乐器/曲种/Hmong diaspora/未收录苗歌手, 与1/2批不重叠)
KW = [
 '台江苗族','剑河苗族','丹寨苗族','黄平苗族','松桃苗族','花垣苗族','融水苗族','隆林苗族',
 '海南苗族','文山苗族','金平苗族','越南苗族','老挝苗族','泰国苗族','美国Hmong',
 '莽筒','夜箫','古瓢琴','苗笛','姊妹箫','木叶独奏','铜鼓苗',
 '苗族古歌','苗族叙事歌','苗族婚俗歌','苗族祭祀歌','苗年歌','姊妹节','四月八苗族',
 '爬坡节','吃新节','游方歌','讨花带','苗歌对唱','苗语流行','苗语歌曲',
 'Hmong music','Hmong song','Kwv Txhiaj','Nkauj Hmoob','Hmoob Tshiab',
 'Hmong New Year','Hmong Qeej','Hmong USA','Hmong dance',
 '阿朵苗族','何继光苗族','杨光斌苗族','潘兴周苗族','龙智祥苗族','吴廷贵苗族','罗秀英苗族','杨祖桃苗族',
]

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
    if EN_PAT.search(name) and not CN_PAT.search(name) and not hmongish(name):
        return False
    if not has_dl(s):
        return False
    return True

# —— 现有库去重键 ——
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

# —— staging 续跑 ——
stage = {'done_kws': [], 'candidates': []}
if STAGE.exists():
    try:
        stage = json.loads(STAGE.read_text(encoding='utf-8'))
        print(f'[续跑] 已有 {len(stage["candidates"])} 候选, 已完成 {len(stage["done_kws"])} 词', flush=True)
    except Exception:
        pass
done = set(stage['done_kws'])
seen_new = set()
for c in stage['candidates']:
    seen_new.add(c['_key'])

def real_source(s):
    real = (s.source or '').removesuffix('MusicClient')
    if isinstance(s.download_url, str) and s.download_url.startswith('ytdlp:'):
        real = 'Bilibili' if 'bilibili.com' in s.download_url else 'YouTube'
    elif isinstance(s.download_url, str) and 'res.wx.qq.com' in s.download_url:
        real = '光音·微信'
    return real

client = m._ethnos_get_client()
accepted_total = len(stage['candidates'])
stats = defaultdict(lambda: {'hit': 0, 'kept': 0})
t0 = time.time()

for kw in KW:
    if kw in done:
        continue
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
        brief = m.song_brief(s, 'Ethnos', 0)
        real = real_source(s)
        brief['source'] = real or 'Ethnos'
        brief['source_cn'] = m.SOURCE_NAMES.get(real, real) if real else '民族音乐'
        if not brief['duration'] or ':' not in brief['duration']:
            brief['duration'] = ''
        cand = dict(brief, _song=m._slim_song(s.todict()), _key=key, _kw=kw)
        stage['candidates'].append(cand)
        stats[kw]['kept'] += 1
    done.add(kw)
    stage['done_kws'] = list(done)
    # 增量落盘(断点续跑)
    STAGE.write_text(json.dumps(stage, ensure_ascii=False), encoding='utf-8')
    print(f'  -> 累计候选 {len(stage["candidates"])}', flush=True)

elapsed = round(time.time() - t0, 1)
new_tracks = stage['candidates']
old_count = len(doc['tracks'])
doc['tracks'] = doc['tracks'] + new_tracks
doc['count'] = len(doc['tracks'])
doc['partial'] = False
m._atomic_write_json(CACHE, doc)
print(f'[入库] {old_count} -> {doc["count"]} (新增 {len(new_tracks)})', flush=True)

by_src = Counter(c.get('source') for c in new_tracks)
lines = ['苗族库 · 补充导入报告(第3批)', f'时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
         f'耗时: {elapsed}s  检索词 {len(KW)} 个',
         f'库: {old_count} -> {doc["count"]} (新增 {len(new_tracks)})', '',
         '== 各词 命中/保留 ==']
for kw in KW:
    st = stats[kw]
    lines.append(f'  {kw:<14} 命中 {st["hit"]:<4} 保留 {st["kept"]}')
lines += ['', '== 新增按音源 =='] + [f'  {s}: {n}' for s, n in by_src.most_common()]
lines += ['', '== 新增明细 =='] + [f'  - {c.get("song_name")} / {c.get("singers")} [{c.get("source")}] ({c.get("_kw")})' for c in new_tracks]
REPORT.write_text('\n'.join(lines), encoding='utf-8')
print('报告:', REPORT)
