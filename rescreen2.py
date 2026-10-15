# -*- coding: utf-8 -*-
"""第3轮高精度筛查: 剔除非苗族音乐。先 dry-run(默认)打印清单, --apply 才真删。
设计原则: 宁可漏删, 不可误删。苗族内容的 DJ/纯音乐/伴奏/舞曲/原声 一律保留,
只删" performer/内容本身非苗"的杂质。"""
import json, sys, re
from collections import defaultdict

CACHE = 'webui/ethnos_cache/e04_苗族.json'
DOC = json.loads(open(CACHE, encoding='utf-8').read())
TR = DOC['tracks']

# ——— 1) 明确非苗歌手/团体(整名匹配, 命中即删) ———
NONMIAO_ARTIST = [
    '降央卓玛','雷佳','王丽达','张也','张振富','耿莲凤','乌兰图雅','乌兰托娅','腾格尔',
    '德德玛','韩磊','刀郎','龚玥','黑鸭子','女子十二乐坊','凤凰传奇','玖月奇迹','阿宝',
    '王二妮','谭维维','韩红','斯琴格日乐','云飞','呼斯楞','阿尔法','王宏伟','刘和刚',
    '祖海','陈思思','吕继宏','汤非','额尔古纳','蓝野','哈琳','傲日其愣','阿吉太组合',
    '传奇乐坊','华夏民族乐团','新时代轻音乐团','新时代乐团','中国广播交响乐团','朱哲琴',
    '龚琳娜','慕容晓晓','庞龙',
    # 注: 宋祖英(苗族歌唱家) / 龙仙娥(苗族飞歌皇后) / 各类苗语Hmong歌 一律保留, 不在此列
]

# ——— 2) 非苗民族标记(多字, 避免单字误报: 藏/回/蒙) ———
ETHNIC = ['藏族','西藏','拉萨','青藏','蒙古','草原','内蒙古','彝族','傣族','佤族','侗族',
          '哈萨克','维吾尔','羌族','朝鲜族','回族','新疆']

# ——— 3) 垃圾/非音乐频道(儿歌早教/游戏动画短剧/抖音搬运/怪电子/日文字幕组) ———
JUNK_CHANNEL = [
    '启蒙儿歌乐园','向日葵儿歌','快乐虎儿歌','嘻嘻娃娃儿歌','儿童歌曲','白雪公主',
    '回形针','山上花','解毒哟','糖果短剧社','兰希身愉','追yr','喵地一聲响',
    'cookoocooky1','苗乡&★麒麟★ぃん','苏打君の山羊','云盏','美貌是第1生产力','梦到一方',
    # 青初霁 的2首为苗语原创歌, 予以保留(用户要加苗歌)
    # 保留(真苗内容): 名曲播放(苗族山歌)/泰歌精选(Hmong)/贵州旅游人(雷山苗年锦鸡舞)/
    #   TZ钢琴二重奏(苗族舞曲)/香香广场舞等(苗族舞曲)/自草新词...(Hmong收藏)/
    #   龙仙娥(苗族飞歌皇后)/苗岭飞歌创作的原声
]

# ——— 4) 非音乐/非苗题材类型 ———
TYPE_JUNK = ['游戏','动漫','二次元','短剧','漫剧','抖音','带货','直播','早教','宝宝','儿歌','动画']

# ——— 5) 日文假名(标题/上传者含日文 = 非苗强信号) ———
JP = re.compile(r'[\u3040-\u30FF\u31F0-\u31FF]')

# ——— 6) 电影插曲(老电影歌曲, 非苗folk) ———
MOVIE = re.compile(r'电影|插曲|片尾|片头|主题曲')

# 苗族白名单歌手(即便是消音/伴奏也保留真苗歌手)
MIAO_OK = ['宋祖英','阿幼朵','朵久央','蝶当久','叠贵','古阿新','欧桑','雷艳','阿音坊','三苗网',
           '苗老杨','阿旺','阿苗千千','杨昌','晏敏敏','熊照华','刘星','阿蕾娥','九黎苗音','歪苗哥',
           '魂器芦苼','其乐龙融','阿卯','蝶长','苗欧桑','保成','陶永华','柳如烟','叠贵与熹楚',
           '俊贤','杨胜文','杨文彪','吴廷翠','阿保本色','阿牛','欧化','潘美辰','杨秀丽','潘佩',
           '吴艳梅','阿诺','杨敏','吴雪','潘红','杨丽','龙梅','潘涛','杨兵','阿杰','吴勇','潘刚',
           'hmoob','nkauj hmoob','Lu Shui Ren','山上花']


# ——— 0) 歌名即苗族内容的强保护(不受上传者/团体名干扰) ———
# 例: "苗家衫木送远方/贵州黔南苗族侗族自治州歌舞队苗歌组" 是苗歌组(苗族歌队),
#     只因团体名带"侗族自治州"会被误伤; "苗族古歌/旧梦の事务所" 只因上传者含日文の;
#     "满山的葡萄红艳艳" 经典苗族民歌, 只因演唱者张振富在黑名单。
PROTECT_NAME = ['苗家', '苗歌组', '苗歌', '苗族古歌', '满山的葡萄红艳艳', '凯里我可爱的家乡']


def classify(t):
    name = t.get('song_name') or ''
    sng = (t.get('singers') or '').strip()
    blob = name + ' ' + sng
    # 0) 强保护: 歌名本身即苗族内容
    if any(p in name for p in PROTECT_NAME):
        return None
    # 6) 日文(歌名含苗则豁免)
    if JP.search(blob) and not any(p in name for p in PROTECT_NAME):
        return '日文上传者/标题'
    # 1) 非苗歌手
    for a in NONMIAO_ARTIST:
        if a in sng or a in name:
            return '非苗歌手:' + a
    # 2) 非苗民族
    for e in ETHNIC:
        if e in blob:
            return '非苗民族:' + e
    # 3) 垃圾频道
    for c in JUNK_CHANNEL:
        if c in sng:
            return '垃圾频道:' + c
    # 4) 非音乐类型
    for g in TYPE_JUNK:
        if g in blob:
            return '非音乐/题材:' + g
    # 5) 电影插曲(且非苗歌手)
    if MOVIE.search(blob):
        if not any(m in sng for m in MIAO_OK):
            return '电影插曲/非苗'
    return None


removals = defaultdict(list)
keep_count = 0
for i, t in enumerate(TR):
    r = classify(t)
    if r:
        removals[r.split(':')[0]].append((i, t.get('song_name', ''), t.get('singers', ''), r))
    else:
        keep_count += 1

print(f'库总曲目: {len(TR)}')
print(f'将保留: {keep_count}   将删除: {sum(len(v) for v in removals.values())}')
print('=' * 70)
for cat, items in removals.items():
    print(f'\n### 类别 [{cat}]  共 {len(items)} 首')
    for i, name, sng, r in items:
        print(f'  [{i}] {name}  /  {sng}   <{r}>')

if '--apply' not in sys.argv:
    print('\n[DRY-RUN] 未改动文件。确认无误后加 --apply 执行删除。')
else:
    idx_to_remove = sorted(set(i for items in removals.values() for i, *_ in items), reverse=True)
    for i in idx_to_remove:
        del TR[i]
    DOC['tracks'] = TR
    DOC['count'] = len(TR)
    DOC['partial'] = False
    json.dump(DOC, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'\n[APPLY] 删除 {len(idx_to_remove)} 首, 剩余 {len(TR)} 首。已写回 {CACHE}')
