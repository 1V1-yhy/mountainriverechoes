'''
苗族库缺漏检索: 找出"民族库里还没录入的苗族音乐"
做法:
  1. 读 webui/ethnos_cache/e04_苗族.json, 用与 mountainriverechoes 完全一致的去重键
     (归一化歌名 + 首位歌手) 建"已录入"集合。
  2. 用项目自带的逐源并行搜索(7 个音源), 对一批苗族专属关键词 + 更多苗族歌手广搜。
  3. 命中里过滤掉已录入的, 剩下的即为"库里没有的苗族音乐"候选。
产物:
  missing_miao_candidates.json  —— 候选明细(歌名/歌手/音源/关键词来源/可下载)
  missing_miao_report.txt       —— 可读报告(各关键词命中/已录入/新增)
用法:
  PYTHONPATH=./webui python find_missing_miao.py
'''
import os, re, sys, json, time, threading
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ['MRE_ONLY_GROUP'] = 'e04'
sys.path.insert(0, str(ROOT / 'webui'))
import mountainriverechoes as m

CACHE = ROOT / 'webui' / 'ethnos_cache' / 'e04_苗族.json'
OUT_JSON = ROOT / 'missing_miao_candidates.json'
OUT_TXT = ROOT / 'missing_miao_report.txt'


# ---- 与 mountainriverechoes 一致的归一化/去重键 ----
def norm_str(s):
    return re.sub(r'[\s\-—·,，.。\'"()（）【】\[\]~～!！?？:：;；&+]', '', str(s or '').lower())

def core_name(name):
    raw = str(name or '')
    n = re.sub(r'[（(\[【][^)）\]】]*[)）\]】]', '', raw)
    n = re.sub(r'(现场版?|live版?|伴奏版?|纯音乐版?|翻唱版?|remix|dj版?|cover版?|卡拉ok版?)$', '', n.strip().lower())
    n = norm_str(n)
    parts = sorted(p for p in (norm_str(x) for x in re.split(r'[-—]', raw)) if p)
    if len(parts) >= 2 and n == ''.join(parts):
        n = ''.join(sorted(parts))
    return n or norm_str(raw)

def first_singer(singers):
    return norm_str(str(singers or '').split('/')[0].split(',')[0].split('、')[0])

def dedup_key(song_name, singers):
    return core_name(song_name) + '|' + first_singer(singers)


# ---- 1. 已录入集合 ----
def existing_keys():
    doc = json.loads(CACHE.read_text(encoding='utf-8'))
    keys = set()
    for t in (doc.get('tracks') or []):
        keys.add(dedup_key(t.get('song_name'), t.get('singers')))
    return keys, doc.get('count')

existing, existing_count = existing_keys()
print(f'[已有库] {existing_count} 首, 去重键 {len(existing)} 个')


# ---- 2. 检索关键词: 苗族专属词 + 更多苗族歌手 ----
KW = [
    # 苗族专属体裁/语言(原构建未用)
    '苗族飞歌', '苗族山歌', '苗语歌曲', '苗歌', '芦笙', '苗岭', '苗族情歌', '苗乡', '苗族古歌',
    # 重新跑原构建用过的词/歌手(抓漏网 + 音源新上架)
    '苗族民歌', '苗族歌曲', '宋祖英', '阿幼朵', '蝶当久',
    # 更多苗族歌手
    '龙仙娥', '杨一方', '刘媛媛',
]

client = m._ethnos_get_client()


# ---- 3. 逐词搜索 + 差集 ----
candidates = {}        # key -> record
stats = defaultdict(lambda: {'hit': 0, 'new': 0})
t_start = time.time()

for kw in KW:
    res = m._search_ethnos_keyword(client, kw)
    print(f'[{kw}] 命中 {len(res)}', flush=True)
    for s in res:
        if not s.song_name:
            continue
        key = dedup_key(s.song_name, s.singers)
        stats[kw]['hit'] += 1
        if key in existing:
            continue
        if key in candidates:
            continue
        du = s.download_url
        has_dl = isinstance(du, str) and du.startswith('http')
        candidates[key] = {
            'song_name': s.song_name,
            'singers': s.singers,
            'source': (s.source or '').removesuffix('MusicClient'),
            'from_kw': kw,
            'duration': getattr(s, 'duration', '') or '',
            'has_download': has_dl,
        }
        stats[kw]['new'] += 1

elapsed = round(time.time() - t_start, 1)

# ---- 4. 输出 ----
records = sorted(candidates.values(), key=lambda r: (r['from_kw'], r['song_name']))
OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')

lines = []
lines.append('苗族民族库 · 未录入候选报告')
lines.append(f'生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
lines.append(f'现有库: {existing_count} 首 (去重键 {len(existing)} 个)')
lines.append(f'检索耗时: {elapsed}s  检索词 {len(KW)} 个  候选 {len(records)} 首')
lines.append('')
lines.append('== 各检索词命中 / 新增 ==')
for kw in KW:
    st = stats[kw]
    lines.append(f'  {kw:<10} 命中 {st["hit"]:<4} 新增 {st["new"]}')
lines.append('')
lines.append('== 候选清单(去重后) ==')
by_kw = defaultdict(list)
for r in records:
    by_kw[r['from_kw']].append(r)
for kw in KW:
    rs = by_kw.get(kw)
    if not rs:
        continue
    lines.append(f'# {kw} ({len(rs)} 首)')
    for r in rs:
        dl = '可下' if r['has_download'] else '不可下'
        lines.append(f'  - {r["song_name"]}  /  {r["singers"]}  [{r["source"]}] {dl}')
    lines.append('')
OUT_TXT.write_text('\n'.join(lines), encoding='utf-8')

print('\n=== 完成 ===')
print(f'候选总数: {len(records)}  (其中可下载 {sum(1 for r in records if r["has_download"])} 首)')
print(f'明细: {OUT_JSON}')
print(f'报告: {OUT_TXT}')
