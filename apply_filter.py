# -*- coding: utf-8 -*-
"""正式清理：备份 -> 过滤非苗族音乐 -> 去重 -> 原子写回"""
import json, re, shutil, time, os, collections

PATH = 'webui/ethnos_cache/e04_苗族.json'
d = json.load(open(PATH, encoding='utf-8'))
ts = d['tracks']
print('清理前:', len(ts))

# ---- 备份 ----
os.makedirs('webui/ethnos_cache/versions', exist_ok=True)
bak = 'webui/ethnos_cache/versions/e04_苗族.%d.json' % int(time.time())
shutil.copyfile(PATH, bak)
print('备份 ->', bak)

MIAO_PAT = re.compile(r'苗|Hmong|HMOOB|Mhong|Miao|飞歌|芦笙|芦苼|古歌|讨花带|游方|银饰|蝴蝶妈妈|岜沙|西江|雷公山|清水江|芒筒|嘎百福|反排|方召|巫溜|巫交|台江|施洞|舟溪|Hxak|阿卯|Phooj|Kuv|Koj|央格里|蝶长|满山的葡萄|金竹根', re.I)
HMONG_PAT = MIAO_PAT
OTHER_PAT = re.compile(r'彝族|彝家|彝语|藏族|藏语|西藏|侗族|侗语|侗寨|傣族|傣乡|蒙古|维吾|朝鲜|哈尼|壮族|布依|瑶族|白族|纳西|左脚舞|云南山歌|豫剧|京剧|越剧|黄梅戏|二人转|秦腔|弥渡|小河淌水|太阳出来喜洋洋|放马山歌|龙船调|唱支山歌给党听|康定情歌|敖包相会|乌苏里|茉莉花|紫竹调|金蛇狂舞|山歌好比春江水|客家山歌|浏阳河|映山红|十送红军|洪湖水|爱我中华|好日子|辣妹子|小背篓|长大后我就成了你|九九艳阳天|珊瑚颂|绣红旗|说句心里话|美丽的草原|敕勒歌|草原骑兵|凤尾竹|竹楼情歌|有一个美丽的地方|金孔雀|梁祝|宋祖英|腾格尔|李谷一|刀郎|蒋大为')
GAME_PAT = re.compile(r'指尖江湖|剑网|剑三|剑侠|木桩|打桩|紫武|输出手法|吃鸡|大赏|面板|手法|秒伤|数值|萌翻|游戏玩家|动漫党|三角洲|倩女|cos|Cos|COS|舞团|整蛊|陀螺')
VIDEO_PAT = re.compile(r'(小哥|小妹|旺夫|相亲|婆婆|媳妇|搞笑|实拍|现场拍摄|第\d+集|的创作原声|lv_0_|studio_video|video_2|videoplayback|VTS_0|- \d{10,}|\.mp4|\.mp3|VID_20|1691|1661|合集|MV【高清】|原版MV|高清修复|AI山歌|太厉害|带动现场|车载dj|串烧|DJ版|嗨曲|降调)')
CYR_PAT = re.compile(r'[\u0400-\u04FF]')
THAI_PAT = re.compile(r'[\u0E00-\u0E7F]')
POP_SINGERS = set('周深 汪苏泷 欢子 徐暐翔 邓紫棋 薛之谦 李荣浩 毛不易 张杰 林俊杰 陈奕迅 周杰伦 王力宏 张碧晨 杨宗纬 任贤齐 郑源 六哲 冷漠 龙梅子 大哲 王琪 海来阿木 云飞 降央卓玛 乌兰图雅 凤凰传奇 龚玥 环球音乐中国 梁静茹 苏打绿 伍佰 动力火车 侧田 莫文蔚 林志炫 孙露 陈珊妮 草东没有派对 高安 邱小宝 五月天 腾格尔 刘紫玲 郁钧剑 刀郎 朱哲琴 陈小涛 索朗顿珠 谭维维 吴碧霞 希林娜依高 王丽达 黄霄 徐子尧 群星 佚名 未知歌手'.split())
MIAO_ARTISTS = ['阿幼朵','蝶当久','朵久央','杨一方','阿音坊','古阿新','杨胜文','金竹乐队','雷艳','龙仙娥','欧桑','阿蕾娥','杨春念','杨昌耀','王合飞','三苗网','杨胜美','吴文梅','潘成增','杨召江','潘兴周','杨渌','刘星','叠贵','央格里','蝶长','阿卯','邰秀武']
# 歌名本身就能确认是苗族题材的白名单（无苗字的）
KEEP_NAMES = re.compile(r'银白色的山歌|对门看见金竹根|满山的葡萄红艳艳|呀啰嘿|深山水腔')

def classify(t):
    name = str(t.get('song_name') or ''); artist = str(t.get('singers') or ''); album = str(t.get('album') or '')
    blob = name + ' ' + artist + ' ' + album
    if GAME_PAT.search(blob): return False, '游戏视频噪声'
    if VIDEO_PAT.search(blob): return False, '视频/DJ噪声'
    if MIAO_PAT.search(blob) or KEEP_NAMES.search(name): return True, ''
    if OTHER_PAT.search(blob): return False, '非苗民族/民歌'
    if CYR_PAT.search(blob) or THAI_PAT.search(blob): return False, '外文'
    if artist in POP_SINGERS: return False, '流行歌手'
    if any(a in artist for a in MIAO_ARTISTS): return True, '白名单歌手'
    if re.search(r'[A-Za-z]{4,}', name) and not re.search(r'[\u4e00-\u9fff]', name): return False, '纯外文歌名'
    if len(name) > 45: return False, '视频标题'
    return False, '存疑清除'

kept, removed = [], []
for t in ts:
    ok, why = classify(t)
    (kept if ok else removed).append((t, why))

# ---- 去重(歌名+歌手归一) ----
def dkey(t):
    import re as _re
    n = _re.sub(r'[\s（\(【\[].*?$', '', str(t.get('song_name') or '')).strip().lower()
    a = _re.sub(r'[\s&,，、].*$', '', str(t.get('singers') or '')).strip().lower()
    return n + '::' + a

seen, uniq_kept, dup = set(), [], 0
for t, _ in kept:
    k = dkey(t)
    if k in seen:
        dup += 1; continue
    seen.add(k); uniq_kept.append(t)

print('保留:', len(uniq_kept), '| 清除:', len(removed), '| 重复去重:', dup)
print('\n清除原因分布:', collections.Counter(w for _, w in removed))

# ---- 原子写回 ----
d['tracks'] = uniq_kept
d['count'] = len(uniq_kept)
tmp = PATH + '.tmp'
json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
os.replace(tmp, PATH)
print('\n已写回，新曲库总数 =', len(uniq_kept))
