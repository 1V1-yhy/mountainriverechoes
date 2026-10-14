# -*- coding: utf-8 -*-
"""干跑分析：把 e04 苗族库分成 确定苗族 / 确定非苗族 / 存疑 三类"""
import json, re, collections, sys

PATH = 'webui/ethnos_cache/e04_苗族.json'
d = json.load(open(PATH, encoding='utf-8'))
ts = d['tracks']

# ---------- 规则 ----------
# 苗族标记（歌名/歌手/专辑任一命中即"确定苗族"）
MIAO_PAT = re.compile(r'苗|Hmong|HMOOB|Mhong|Miao|飞歌|芦笙|芦苼|古歌|讨花带|游方|银饰|蝴蝶妈妈|岜沙|西江|雷公山|清水江|芒筒|嘎百福')
# 明确其他民族 / 非苗标记
OTHER_PAT = re.compile(r'彝族|彝语|藏族|藏语|西藏|侗族|侗语|侗寨|傣族|蒙古|维吾|朝鲜|哈尼|壮族|布依|瑶族|白族|纳西|左脚舞|陕北|秦腔|河南豫剧|京剧|越剧|黄梅戏|二人转')
# 噪声/外语（拉丁字母长串、非 Hmong 的英文等）——稍后单独判定
CYR_PAT = re.compile(r'[\u0400-\u04FF]')
# 知名主流流行歌手（歌名无苗标记时直接视为非苗）
POP_SINGERS = set('''周深 汪苏泷 欢子 徐暐翔 邓紫棋 薛之谦 李荣浩 毛不易 张杰 林俊杰 陈奕迅 周杰伦 王力宏 张碧晨 杨宗纬 黄品源 任贤齐 郑源 六哲 冷漠 龙梅子 秋裤大叔 大哲 王琪 海来阿木 云飞 降央卓玛 乌兰图雅 凤凰传奇 筷子兄弟 庄妮 阿吉太组合 莫西子诗'''.split())
# 歌名像视频标题（长、含口语句式）
VIDEO_PAT = re.compile(r'(小哥|小妹|漂亮|帅|旺夫|相亲|婆婆|媳妇|搞笑|实拍|现场拍摄|第\d+集|合集|原声 |的创作原声|网友|大家|快来|关注|点赞|收藏|转发|直播)')
# 歌名里出现非苗的英文噪声（无苗标记且含英文长词）
EN_PAT = re.compile(r'[A-Za-z]{4,}')

def miao_hit(t):
    blob = ' '.join(str(t.get(k) or '') for k in ('song_name', 'singers', 'album'))
    m = MIAO_PAT.search(blob)
    return m

def classify(t):
    name = str(t.get('song_name') or '')
    artist = str(t.get('singers') or '')
    blob = name + ' ' + artist
    if miao_hit(t):
        return 'miao', ''
    # 无苗标记
    if OTHER_PAT.search(blob):
        return 'other', '其他民族/戏曲标记: ' + OTHER_PAT.search(blob).group(0)
    if CYR_PAT.search(blob):
        return 'other', '西里尔字母'
    if artist in POP_SINGERS:
        return 'other', '主流流行歌手: ' + artist
    if VIDEO_PAT.search(name) or len(name) > 40:
        return 'other', '视频标题噪声'
    if EN_PAT.search(name) and not re.search(r'Hmong|HMOOB|Miao', name, re.I):
        # 英文歌名且歌手也无苗标记
        if not re.search(r'[\u4e00-\u9fff]', name):
            return 'other', '纯英文歌名'
    return 'doubt', ''

res = collections.defaultdict(list)
for i, t in enumerate(ts):
    cat, why = classify(t)
    res[cat].append((i, t, why))

print('=== 统计 ===')
for k in ('miao', 'doubt', 'other'):
    print(k, len(res[k]))

print('\n=== 确定移除(other) 抽样 40 ===')
for i, t, why in res['other'][:40]:
    print('-', str(t.get('song_name'))[:45], '|', str(t.get('singers'))[:20], '|', why)

print('\n=== 存疑(doubt) 全部 ===')
for i, t, why in res['doubt']:
    print('-', str(t.get('song_name'))[:45], '|', str(t.get('singers'))[:20], '|', t.get('source'))

print('\n=== 保留(miao) 抽样 15 ===')
for i, t, why in res['miao'][:15]:
    print('-', str(t.get('song_name'))[:45], '|', str(t.get('singers'))[:20])
