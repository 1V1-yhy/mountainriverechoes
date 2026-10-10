'''
苗族音乐播放器 —— 独立 EXE 启动入口
- 仅加载「苗族」民族歌单 (MRE_ONLY_GROUP=e04)
- 启动后弹出【内嵌原生窗口】(pywebview / 系统 WebView2), 不再调用系统浏览器
- 播放/搜索全部复用 mountainriverechoes 既有引擎
'''
import os
import sys
import time
import threading
import urllib.request
from pathlib import Path

# 必须在导入 mountainriverechoes 之前设置, 才会触发单民族过滤
os.environ['MRE_ONLY_GROUP'] = 'e04'

# 把脚本所在目录加入 path, 保证能 import 到同目录的 mountainriverechoes
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mountainriverechoes as m  # noqa: E402


# PyInstaller 单文件模式: 把模板目录指向打包内的 webui/templates
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _mre_webui = Path(sys._MEIPASS) / 'webui'
    m.app.template_folder = str(_mre_webui / 'templates')


def _wait_server():
    """等 Flask 本地服务起来, 最多等 60 秒"""
    for _ in range(60):
        try:
            urllib.request.urlopen(f'http://{m.HOST}:{m.PORT}/', timeout=1)
            return True
        except Exception:
            time.sleep(1)
    return False


def _start_window():
    import webview  # 延迟导入, 便于无 GUI 环境下排查
    ok = _wait_server()
    if not ok:
        # 服务没起来也要给个提示窗口, 而不是静默失败
        webview.create_window(
            '苗族音乐 - 启动失败',
            html='<h2 style="font-family:sans-serif;padding:24px">'
                 '本地服务启动失败，请确认端口 8766 未被占用后重试。</h2>',
            width=420, height=180,
        )
        webview.start(gui='edgechromium')
        return
    webview.create_window(
        '苗族音乐',
        f'http://{m.HOST}:{m.PORT}/',
        width=1180, height=760,
        resizable=True,
        min_size=(800, 600),
    )
    # 使用系统自带的 WebView2(edgechromium), 不打包 Chromium, 体积小
    webview.start(gui='edgechromium')


def main():
    # Flask 在后台子线程跑(提供 API / 播放解析), 主线程跑内嵌窗口
    threading.Thread(
        target=lambda: m.app.run(host=m.HOST, port=m.PORT, threaded=True),
        daemon=True,
    ).start()
    _start_window()


if __name__ == '__main__':
    main()
