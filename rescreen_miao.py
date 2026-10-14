# -*- coding: utf-8 -*-
"""二次筛查(定稿): 先保留苗标记/苗语/苗歌手(含标题内出现), 剔除明确非苗; 干跑输出报告, 不修改文件."""
import json, re, collections

PATH = 'webui/ethnos_cache/e04_苗族.json'
d = json.load(open(PATH, encoding='utf-8'))
ts = d['tracks']

MIAO = re.compile(r'苗族|苗家|苗语|苗歌|苗岭飞歌|苗乡|Hmong|HMOOB|Mhong|Miao|飞歌|芦笙|芦苼|'
                  r'古歌|讨花带|游方|银饰|蝴蝶妈妈|岜沙|西江千户|雷公山|清水江|芒筒|'
                  r'嘎百福|锦鸡舞|苗寨|苗年|苗舞|苗绣|反排|方召|台江|雷山|丹寨|'
                  r'苗族芦笙|苗族飞歌|苗族古歌|苗岭|苗山|小卜少|卜少|酒歌|情歌\(苗|苗疆|'
                  r'满山的葡萄红艳艳|葡萄红艳艳')

# 苗语(白苗/青苗/红苗)罗马字 —— 去\b, 作为子串匹配(因常与中文相邻)
HMONG_ROM = re.compile(r'(Hmoob|Moob|Hmong|Txhiaj|Nkauj|Niam|Hlub|Siab|Nco|Tsuas|Nraug|'
                       r'Ntxhais|Tub\s*Siv|Thoj|Vaj|Xyooj|Moua|Txiv\s*Neej|Nplooj|Yawg|Poj|'
                       r'Koj|Kuv|Tus|Neej|Lub|Zoo|Tshaj|Mus|Ua|Tseg|Ntej|Tso|Xaiv|Khuv|Xim|'
                       r'Txiv|Niam|Nraug|Txoj|Yog|Mog|Lawm|Puas|Ces|Tim|Qhov|Kob|Sib|Ntshai|'
                       r'Nplooj|Vang|Xiong|Vue|Thao|Lor|Kia|Yang)', re.I)

OTHER_ETHNIC = re.compile(r'彝族|彝家|彝语|藏族|藏语|西藏|蒙古族|蒙古|维吾|维吾尔|哈萨克|'
                          r'朝鲜族|鲜族|哈尼|壮族|布依|侗族|侗语|侗寨|瑶族|白族|纳西|土家|'
                          r'傣族|佤族|景颇|傈僳|拉祜|高山族|回族|满族|撒尼|陕北民歌|'
                          r'青海花儿|信天游|爬山调|山西民歌|司岗里|LOX\s*RHAX|司岗')

OPERA = re.compile(r'京剧|越剧|黄梅戏|豫剧|川剧|秦腔|评剧|昆曲|二人转|河北梆子|晋剧|'
                   r'吕剧|沪剧|评话|大鼓|快板|莲花落|潮剧|粤剧|花鼓戏|采茶戏')

FAMOUS_NONMIAO = re.compile(r'小河淌水|弥渡|康定情歌|敖包相会|茉莉花|兰花花|沂蒙|走西口|'
                           r'龙船调|太阳出来喜洋洋|放马山歌|阿佤人民唱新歌|北京的金山上|'
                           r'三十里铺|绣金匾|山丹丹开花|赶牲灵|打酸枣|挂红灯|'
                           r'嘎达梅林|森吉德玛|黑骏马|美丽的草原|草原上升起|南泥湾|'
                           r'五哥放羊|想亲亲|桃花红杏花白|圪梁梁|亲圪蛋|乌苏里船歌|'
                           r'婚誓|月光下的凤尾竹|蝴蝶泉边|弥渡山歌|槐花几时开')

GAME_ANIME_DRAMA = re.compile(r'剑网|剑三|剑侠|原神|王者荣耀|和平精英|吃鸡|英雄联盟|'
                  r'指尖江湖|古剑|逆水寒|天涯明月刀|崩坏|明日方舟|第五人格|'
                  r'奥特曼|小猪佩奇|汪汪队|喜羊羊|熊出没|斗罗大陆|修仙|动漫|'
                  r'游戏BGM|游戏音乐|同人|MAD|AMV|cosplay|漫画|短剧|番外|插班生|'
                  r'漫画社|漫剧|寻龙诀|人物志|舞蹈团|舞蹈：|喜马拉雅|听书|汉人舞|早市儿|五仙')

VIDEO = re.compile(r'搞笑|实拍|现场拍摄|相亲|婆婆|媳妇|旺夫|婆媳|农村生活|vlog|VLOG|'
                   r'探店|带货|直播|第\d+集|的创作原声|lv_0_|studio_video|video_|'
                   r'\.mp4|\.mp3|1691|1661|高清HD|饭制|混剪|reaction|'
                   r'翻唱大赛|好声音|歌手202|中国好|披荆斩棘|声生不息|综艺|春晚|'
                   r'抖音|快手|小红书|网红|网红歌')

NOISE = re.compile(r'朗诵|诗朗诵|广播剧|有声书|有声小说|配音|相声|小品|儿童故事|'
                   r'儿歌|童谣|摇篮曲|佛教|道场|经咒|大悲咒|心经|往生|超度|'
                   r'ASMR|助眠|白噪音|新闻|讲座|演讲|党课|思政课|纪录片|宣传片|广告')

CYR = re.compile(r'[\u0400-\u04FF]')

# 非苗歌手(无苗标记时其曲目多半是流行/影视, 直接剔除)
NONMIAO_SINGERS = set('格格 苗佳 周深 汪苏泷 欢子 徐暐翔 邓紫棋 薛之谦 李荣浩 毛不易 张杰 林俊杰 '
                     '陈奕迅 周杰伦 王力宏 张碧晨 杨宗纬 任贤齐 郑源 六哲 冷漠 龙梅子 大哲 王琪 '
                     '海来阿木 云飞 降央卓玛 乌兰图雅 凤凰传奇 龚玥 张也 谭晶 宋祖英 祖海 汤灿 '
                     '张燕 王丽达 雷佳 吕继宏 刘和刚 王宏伟 阎维文 郁钧剑 蔡国庆 Beyond 周华健 '
                     '张学友 刘德华 陈慧琳 孙楠 韩红 那英 孙悦 林志炫 胡夏 李健 毛阿敏 韦唯 '
                     '杭天琪 谢霆锋 张韶涵'.split())

MIAO_ARTISTS = ['阿幼朵','蝶当久','朵久央','杨一方','阿音坊','古阿新','杨胜文','金竹','雷艳',
                '龙仙娥','欧桑','阿蕾娥','杨春念','杨昌耀','王合飞','三苗网','杨胜美','吴文梅',
                '潘成增','杨召江','潘兴周','杨渌','阿朵','央格里','叠贵','吴廷翠','阿保本色',
                '杨光才','杨昌树','李怀秀','李怀福','吴学源','杨方','阿牛','苗岭之声','欧化',
                '杨文彪','潘美辰','吴庭福','王仕权','潘晓丽','阿丽','吴文英','杨光锦',
                '龙通珍','杨艳萍','阿苗','杨秀丽','潘佩','吴艳梅','阿旺','潘家','阿卯','阿诺',
                '杨敏','吴雪','潘红','杨丽','龙梅','潘涛','杨兵','阿杰','吴勇','潘刚','阿幼朵组合',
                '蝶长','刘星','陶永华','罗娜依','邹兴秀','邰秀武','韩特立','笑笑','少数π','阿卯',
                '茶艾南','项定秀','熊连妹','杨西音子','龙明月','古阿新','李家霖','穆维平','胡鑫玥',
                '杨春念','吴文英','潘晓丽','阿丽','阿苗']

def has_miao_artist(text):
    return any(a in text for a in MIAO_ARTISTS)

def classify(t):
    name = str(t.get('song_name') or '')
    artist = str(t.get('singers') or '')
    album = str(t.get('album') or '')
    blob = name + ' ' + artist + ' ' + album

    # —— 先保留 ——
    if HMONG_ROM.search(blob):
        return 'miao', '苗语罗马字'
    if MIAO.search(blob):
        return 'miao', '苗标记'
    if has_miao_artist(name) or has_miao_artist(artist):
        return 'miao', '苗族歌手'

    # —— 再剔除明确非苗 ——
    if GAME_ANIME_DRAMA.search(blob):
        return 'other', '漫画/短剧/动画/游戏/有声书'
    if OPERA.search(blob):
        return 'other', '戏曲/曲艺: ' + OPERA.search(blob).group(0)
    if OTHER_ETHNIC.search(blob):
        return 'other', '其他民族: ' + OTHER_ETHNIC.search(blob).group(0)
    if FAMOUS_NONMIAO.search(blob):
        return 'other', '著名非苗民歌: ' + FAMOUS_NONMIAO.search(blob).group(0)
    if VIDEO.search(blob):
        return 'other', '视频/自媒体标题'
    if NOISE.search(blob):
        return 'other', '噪声类: ' + NOISE.search(blob).group(0)
    if CYR.search(blob):
        return 'other', '西里尔(俄语等)'
    if any(s in artist for s in NONMIAO_SINGERS):
        return 'other', '非苗歌手(无苗标记)'
    if re.search(r'[A-Za-z]{4,}', name) and not re.search(r'[\u4e00-\u9fff]', name):
        return 'other', '纯外文歌名'
    if len(name) > 45:
        return 'other', '标题过长(疑似视频)'
    return 'doubt', ''

res = collections.defaultdict(list)
for i, t in enumerate(ts):
    c, w = classify(t)
    res[c].append((i, t, w))

print('=== 总 %d: miao=%d doubt=%d other=%d ===' % (len(ts), len(res['miao']), len(res['doubt']), len(res['other'])))

with open('rescreen_report.txt', 'w', encoding='utf-8') as f:
    f.write('二次筛查报告  总=%d  miao=%d  doubt=%d  other=%d\n' % (len(ts), len(res['miao']), len(res['doubt']), len(res['other'])))
    f.write('\n##### OTHER(拟删除) 全部 %d 条 #####\n' % len(res['other']))
    for i, t, w in res['other']:
        f.write('- [%s] %s | %s | %s\n' % (w, str(t.get('song_name'))[:50], str(t.get('singers'))[:22], t.get('source')))
    f.write('\n##### DOUBT(待确认) 全部 %d 条 #####\n' % len(res['doubt']))
    for i, t, w in res['doubt']:
        f.write('- %s | %s | %s\n' % (str(t.get('song_name'))[:50], str(t.get('singers'))[:22], t.get('source')))

print('报告已写 rescreen_report.txt')
print('\n=== OTHER 全部 %d ===' % len(res['other']))
for i, t, w in res['other']:
    print('- [%s] %s | %s' % (w, str(t.get('song_name'))[:44], str(t.get('singers'))[:18]))
print('\n=== DOUBT 全部 %d ===' % len(res['doubt']))
for i, t, w in res['doubt']:
    print('- %s | %s' % (str(t.get('song_name'))[:44], str(t.get('singers'))[:18]))
