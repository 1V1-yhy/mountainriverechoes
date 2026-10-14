'''
苗族音乐播放器 —— PyInstaller 打包脚本
用法:
    python build_miao_exe.py
产物: dist/苗族曲库.exe  (双击即弹出内嵌原生窗口应用, 不调用系统浏览器)
'''
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / 'venv' / 'Scripts' / 'python.exe'
ENTRY = ROOT / 'webui' / 'miao_entry.py'

# 打包时只带入「苗族」歌单, 实现真正的"只有苗族"
MIAO_JSON = ROOT / 'webui' / 'ethnos_cache' / 'e04_苗族.json'
TEMPLATES = ROOT / 'webui' / 'templates'

ICON = ROOT / 'icon_work' / 'miao_icon.ico'

PYINSTALLER = [
    str(VENV_PY), '-m', 'PyInstaller',
    '--noconfirm', '--clean',
    '--onefile',
    '--name', '苗族曲库',
    '--icon', str(ICON),
    '--windowed',                 # 无控制台黑窗
    '--paths', str(ROOT),         # 让 PyInstaller 找到 musicdl(仓库根)
    '--paths', str(ROOT / 'webui'),
    '--add-data', f'{MIAO_JSON};webui/ethnos_cache',
    '--add-data', f'{TEMPLATES};webui/templates',
    '--collect-submodules', 'musicdl',
    '--collect-submodules', 'yt_dlp',
    '--collect-submodules', 'webview',
    '--hidden-import', 'orjson',
    '--hidden-import', 'json_repair',
    '--hidden-import', 'musicdl',
    '--hidden-import', 'webview',
    str(ENTRY),
]


def main():
    if not VENV_PY.exists():
        print('找不到 venv, 请先按部署文档创建 venv 并装好依赖', file=sys.stderr)
        sys.exit(1)
    if not MIAO_JSON.exists():
        print('找不到苗族歌单文件:', MIAO_JSON, file=sys.stderr)
        sys.exit(1)
    # 确保 PyInstaller 已装
    try:
        subprocess.run([str(VENV_PY), '-m', 'PyInstaller', '--version'],
                       check=True, capture_output=True)
    except Exception:
        print('正在安装 PyInstaller ...')
        subprocess.run([str(VENV_PY), '-m', 'pip', 'install', 'pyinstaller'], check=True)
    print('开始打包(单文件, 仅苗族歌单), 请稍候 ...')
    # 在 ROOT 下执行, 保证相对路径正确
    subprocess.run(PYINSTALLER, cwd=str(ROOT), check=True)
    out = ROOT / 'dist' / '苗族曲库.exe'
    print('完成! 可执行文件:', out if out.exists() else '(未生成, 请检查上方报错)')


if __name__ == '__main__':
    main()
