'''
苗族真曲筛选 + 批量入库
================================
背景: find_missing_miao.py 产出的 1690 候选只存了歌名/歌手/来源, 没有下载链接和歌曲 ID, 无法直接入库。
本脚本重新检索(复用项目自带逐源并行搜索), 在抓取阶段就保留完整可播放 SongInfo, 然后:

  1. 分层过滤"真正的苗族音乐":
     - 关键词检索(苗族飞歌/苗语/芦笙/苗岭/苗乡/苗族古歌/苗歌/苗族山歌/苗族情歌/苗族民歌/苗族歌曲):
       本身就是苗族主题, 直接保留(只需排除西里尔字母 / 非音乐内容)。
     - 歌手检索(刘媛媛/宋祖英/杨一方/龙仙娥/蝶当久/阿幼朵):
       这些歌手的全部作品鱼龙混杂(演讲/有声书/流行歌/俄语Remix), 只保留歌名带苗族标记的。
  2. 排除: 西里尔字母(俄语等)、明显非音乐(演讲/听书/教程/有声/相声/评书...)、无可用下载链接。
  3. 与现有 890 首去重(归一化歌名+首位歌手), 避免重复。
  4. 复用 _ethnos_payload 的落盘 schema (song_brief + todict + 源标签还原), 仅追加不重建。

产物: 更新 webui/ethnos_cache/e04_苗族.json, 并写 import_genuine_miao_report.txt
'''
import os, re, sys, json, time, threading
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ['MRE_ONLY_GROUP'] = 'e04'
sys.path.insert(0, str(ROOT / 'webui'))
import mountainriverechoes as m
from musicdl.modules import SongInfo

CACHE = ROOT / 'webui' / 'ethnos_cache' / 'e04_苗族.json'
REPORT = ROOT / 'import_genuine_miao_report.txt'


# ---------- 过滤规则 ----------
CYR = re.compile(r'[\u0400-\u04FF]')  # 西里尔字母(俄语等)
NON_MUSIC = (
    '演讲', '教程', '听书', '有声', '相声', '评书', '配音', '朗读', '新闻', '广告',
    '课程', '讲座', '百家讲坛', '故事', '散文', '小说', '段子', '脱口秀', '公开课',
    '微课', '读书', '播客', '快板', '贯口', '朗诵',
)
# 苗族专属标记(用于歌手检索的二次把关)
MIAO_MARK = (
    '苗', '芦笙', '飞歌', '苗语', '苗岭', '苗乡', '苗家', '苗寨', '古歌', '巴茅',
    '雷山', '西江', '锦鸡', '反排', '苗年', '牯藏', '姊妹节', '苗歌',
)

# 检索词: 前 11 个是苗族主题关键词(高纯度), 后 6 个是苗族歌手(需二次把关)
KW_MIAO = [
    '苗族飞歌', '苗族山歌', '苗语歌曲', '苗歌', '芦笙', '苗岭', '苗族情歌', '苗乡',
    '苗族古歌', '苗族民歌', '苗族歌曲',
]
KW_SINGER = ['宋祖英', '阿幼朵', '蝶当久', '龙仙娥', '杨一方', '刘媛媛']
KW_ALL = KW_MIAO + KW_SINGER


def is_cyrillic(s):
    return bool(CYR.search(s or ''))


def is_nonmusic(name):
    return any(k in (name or '') for k in NON_MUSIC)


def has_miao_mark(name):
    return any(k in (name or '') for k in MIAO_MARK)


def has_dl(s):
    du = s.download_url
    if not isinstance(du, str):
        return False
    if du.startswith('http'):
        return True
    if du.startswith('ytdlp:'):
        return True
    if 'res.wx.qq.com' in du:
        return True
    return False


def should_keep(kw, s):
    name = s.song_name or ''
    singers = s.singers or ''
    if is_cyrillic(name + singers):
        return False
    if is_nonmusic(name):
        return False
    if kw in KW_SINGER and not has_miao_mark(name):
        return False  # 歌手检索: 只留歌名带苗族标记的
    if not has_dl(s):
        return False
    return True


# ---------- 已有库去重键 ----------
def existing_state():
    doc = json.loads(CACHE.read_text(encoding='utf-8'))
    keys = set()
    for t in (doc.get('tracks') or []):
        try:
            si = SongInfo.fromdict(t.get('_song') or {})
            if si.song_name:
                keys.add(m._dedup_key(si))
        except Exception:
            pass
    return doc, keys


doc, existing_keys = existing_state()
print(f'[现有库] {doc.get("count")} 首, 去重键 {len(existing_keys)} 个')


# ---------- 重新检索 + 过滤 ----------
client = m._ethnos_get_client()
accepted = []          # [(SongInfo, kw)]
seen_new = set()       # 新歌内部去重键
stats = defaultdict(lambda: {'hit': 0, 'kept': 0})

t_start = time.time()
for kw in KW_ALL:
    res = m._search_ethnos_keyword(client, kw)
    print(f'[{kw}] 命中 {len(res)}', flush=True)
    for s in res:
        if not s.song_name:
            continue
        stats[kw]['hit'] += 1
        if not should_keep(kw, s):
            continue
        key = m._dedup_key(s)
        if key in existing_keys or key in seen_new:
            continue
        seen_new.add(key)
        accepted.append((s, kw))
        stats[kw]['kept'] += 1

elapsed = round(time.time() - t_start, 1)
print(f'\n[过滤后] 拟新增 {len(accepted)} 首 (耗时 {elapsed}s)', flush=True)


# ---------- 仅追加式入库(复用 _ethnos_payload 的 schema) ----------
def make_track(s, idx):
    brief = m.song_brief(s, 'Ethnos', idx)
    real = (s.source or '').removesuffix('MusicClient')
    if isinstance(s.download_url, str) and s.download_url.startswith('ytdlp:'):
        real = 'Bilibili' if 'bilibili.com' in s.download_url else 'YouTube'
    elif isinstance(s.download_url, str) and 'res.wx.qq.com' in s.download_url:
        real = '光音·微信'
    brief['source'] = real or 'Ethnos'
    brief['source_cn'] = m.SOURCE_NAMES.get(real, real) if real else '民族音乐'
    if not brief['duration'] or ':' not in brief['duration']:
        brief['duration'] = ''
    return dict(brief, _song=m._slim_song(s.todict()))


new_tracks = [make_track(s, i) for i, (s, _) in enumerate(accepted)]
old_count = len(doc['tracks'])
doc['tracks'] = doc['tracks'] + new_tracks
doc['count'] = len(doc['tracks'])
doc['partial'] = False
m._atomic_write_json(CACHE, doc)

print(f'[入库] 旧 {old_count} -> 新 {doc["count"]} (新增 {len(new_tracks)})', flush=True)


# ---------- 报告 ----------
by_src = Counter(t['source'] for t in new_tracks)
by_kw = Counter(kw for _, kw in accepted)
lines = []
lines.append('苗族库 · 真实苗族音乐批量导入报告')
lines.append(f'生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
lines.append(f'检索耗时: {elapsed}s   检索词 {len(KW_ALL)} 个')
lines.append(f'现有库: {old_count} 首  ->  导入后: {doc["count"]} 首  (新增 {len(new_tracks)} 首)')
lines.append('')
lines.append('== 各检索词 命中 / 保留(已去重) ==')
for kw in KW_ALL:
    st = stats[kw]
    tag = '关键词' if kw in KW_MIAO else '歌手(二次把关)'
    lines.append(f'  {kw:<10} [{tag}] 命中 {st["hit"]:<4} 保留 {st["kept"]}')
lines.append('')
lines.append('== 新增按音源分布 ==')
for src, n in by_src.most_common():
    lines.append(f'  {src}: {n}')
lines.append('')
lines.append('== 新增明细(歌名 / 歌手 [音源] from:关键词) ==')
for s, kw in accepted:
    real = (s.source or '').removesuffix('MusicClient')
    if isinstance(s.download_url, str) and s.download_url.startswith('ytdlp:'):
        real = 'Bilibili' if 'bilibili.com' in s.download_url else 'YouTube'
    elif isinstance(s.download_url, str) and 'res.wx.qq.com' in s.download_url:
        real = '光音·微信'
    lines.append(f'  - {s.song_name}  /  {s.singers}  [{real}]  (来自:{kw})')
REPORT.write_text('\n'.join(lines), encoding='utf-8')

print('\n=== 完成 ===')
print(f'报告: {REPORT}')
