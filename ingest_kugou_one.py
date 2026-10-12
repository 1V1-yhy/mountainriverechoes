"""将单个酷狗分享链接(chain 单曲)入苗族(e04)民族库 —— append-only 安全版。

关键纪律(踩坑后): 绝不整份重建(会丢 fromdict 失败的曲目), 只读现有 JSON,
只在 tracks 上 append 新 track, 更新 count 后原子写回。
若当前库被损坏(<889), 自动从 versions/ 恢复最新完整基线再 append。
"""
import sys, os, json, threading, shutil, time
sys.path.insert(0, 'webui')
import requests
from musicdl.modules import SongInfo
import mountainriverechoes as m
from mountainriverechoes import (
    _atomic_write_json, _cache_path, ETHNIC_BY_KEY,
    _same_recording, song_brief, _slim_song,
)

GROUP = 'e04'
HASH  = 'f5c53b5490765789bc0faabc8ee958bc'   # 已从 chain 页面解析得到
proxies = {k: v for k, v in os.environ.items() if k.upper() in ('HTTP_PROXY', 'HTTPS_PROXY')}


def main():
    path = _cache_path(GROUP)
    info = ETHNIC_BY_KEY[GROUP]
    print('目标民族库:', info['name'], '(', GROUP, ')')
    ver_dir = path.parent / 'versions'

    # 1) 损坏自愈: 当前曲目少于 889 则从 versions 恢复最新完整基线
    if path.exists():
        cur = json.loads(path.read_text(encoding='utf-8'))
        if len(cur.get('tracks', [])) < 889:
            backs = sorted(ver_dir.glob(f'{path.stem}.*{path.suffix}'),
                           key=lambda x: x.stat().st_mtime, reverse=True)
            for b in backs:
                bd = json.loads(b.read_text(encoding='utf-8'))
                if len(bd.get('tracks', [])) >= 889:
                    shutil.copy2(b, path)
                    print('已从备份恢复基线:', b.name, '| tracks=', len(bd.get('tracks', [])))
                    break

    # 2) 解析元数据 + 真实直链
    d = requests.get('https://m.kugou.com/app/i/getSongInfo.php',
                     params={'cmd': 'playInfo', 'hash': HASH}, proxies=proxies, timeout=15).json()
    name   = d.get('songName') or '苗族飞歌'
    singer = d.get('author_name') or d.get('singerName') or '华南师范大学合唱团'
    url    = d.get('url') or (d.get('backup_url') or [''])[0]
    img    = d.get('imgUrl') or d.get('album_img') or ''
    tl     = d.get('timeLength') or 0
    print('元数据: 歌名=%s | 歌手=%s | 直链http=%s' % (name, singer, str(url).startswith('http')))
    if not str(url).startswith('http'):
        raise SystemExit('未拿到可播直链, 终止入库')

    # 3) 查重(仅比对, 不动现有曲目)
    payload = json.loads(path.read_text(encoding='utf-8'))
    tracks = payload['tracks']
    base_n = len(tracks)
    for t in tracks:
        s = SongInfo.fromdict(t.get('_song') or {})
        if _same_recording(name, singer, s.song_name, s.singers):
            print('已在库内(同一首):', s.song_name, '|', s.singers)
            print('SKIP: 该曲已存在于%s库, 不重复入库' % info['name'])
            return

    # 4) append-only 追加
    si = SongInfo(source='KugouMusicClient', song_name=name, singers=singer, album='',
                  ext='mp3', identifier=HASH, download_url=url, cover_url=img,
                  duration=str(tl) if tl else '', protocol='HTTP')
    brief = song_brief(si, 'Ethnos', len(tracks))
    track = dict(brief, _song=_slim_song(si.todict()))
    tracks.append(track)
    payload['tracks'] = tracks
    payload['count'] = len(tracks)
    payload['built_at'] = time.time()
    with threading.Lock():
        _atomic_write_json(path, payload)
    print('入库完成: 库内总计 %d (基线 %d + 新增 1)' % (len(tracks), base_n))
    print('直链(带签名, 播放侧可续签):', str(url)[:110], '...')


if __name__ == '__main__':
    main()
