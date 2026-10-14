'''验证苗族 EXE 所打包的同款代码 + 歌单数据是否正确(绕过 webview 窗口, 仅测 Flask/API/首页)。'''
import os, sys, threading, time, json, urllib.request

os.environ['MRE_ONLY_GROUP'] = 'e04'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webui'))

import mountainriverechoes as m

HOST, PORT = m.HOST, m.PORT

def _run():
    m.app.run(host=HOST, port=PORT, threaded=True)

threading.Thread(target=_run, daemon=True).start()

# 等本地服务起来
up = False
for _ in range(40):
    try:
        urllib.request.urlopen(f'http://{HOST}:{PORT}/', timeout=1)
        up = True
        break
    except Exception:
        time.sleep(1)

if not up:
    print('SERVER_FAIL')
    sys.exit(2)

print('SERVER_UP')

# 1) ethnos 接口: 仅苗族 + 曲库名 + 曲目数
eth = json.load(urllib.request.urlopen(f'http://{HOST}:{PORT}/api/ethnos', timeout=5))
print('ETHNOS only_name =', eth.get('only_name'))
print('ETHNOS name      =', eth.get('name'))
print('ETHNOS count     =', eth.get('count'))

# 2) 首页 HTML 是否含新板块/新皮肤
html = urllib.request.urlopen(f'http://{HOST}:{PORT}/', timeout=5).read().decode('utf-8', 'ignore')
markers = ['苗族曲库', '听见苗族的音乐', '为你精选', '热门歌手', '猜你喜欢',
           'miao-picks', 'miao-artists', 'miao-guess', 'skin-miao', 'i-bf', 'miao-seal']
for mk in markers:
    print(f'HTML[{mk}] =', mk in html)

# 3) 抽查一首歌能正常返回(搜索接口)
try:
    q = urllib.request.urlopen(f'http://{HOST}:{PORT}/api/index/search?q=%E8%8B%97%E6%97%8F', timeout=5).read().decode('utf-8', 'ignore')
    print('SEARCH_苗族 len =', len(q))
except Exception as e:
    print('SEARCH_ERR', e)
