# -*- coding: utf-8 -*-
"""抽取真实模板的 <style> + 模拟苗族首页, 生成 preview.html 供无头截图验证纹样/银饰美化。"""
import re, json
from pathlib import Path
TPL = Path('webui/templates/mountainriverechoes.html')
css = ''.join(re.findall(r'<style[^>]*>(.*?)</style>', TPL.read_text(encoding='utf-8'), re.S))

# 取真实库里几首做卡片示例
lib = json.loads(Path('webui/ethnos_cache/e04_苗族.json').read_text(encoding='utf-8'))['tracks']
picks = lib[:6]
artists = {}
for t in lib:
    s = (t.get('singers') or '').strip()
    if s and s not in ('未知歌手','佚名','网络歌手','华语群星','群星','hmoob','nkauj hmoob'):
        artists.setdefault(s, 0); artists[s]+=1
top_artists = sorted(artists.items(), key=lambda x:-x[1])[:10]

def cov_card(t, idx):
    nm = t.get('song_name',''); sub = t.get('singers','') or '苗族民歌'
    cover = t.get('cover_url','')
    if cover:
        inner = f'<img src="{cover}" style="width:100%;height:100%;object-fit:cover;border-radius:14px" onerror="this.style.display=\'none\'">'
    else:
        inner = f'<div class="miao-ph"><b>{nm[0]}</b><div class="ph-bf"></div><div class="pick-embroider"></div></div>'
    return f'''<div class="pick-card" style="flex:0 0 160px;cursor:pointer">
      <div class="cov" style="position:relative;aspect-ratio:1;border-radius:14px;overflow:hidden">{inner}
        <div class="pick-go">立即聆听 ›</div></div>
      <div class="nm" style="margin-top:9px;font-size:13.5px;font-weight:700;color:#1f2126">{nm[:14]}</div>
      <div class="sub" style="font-size:11.5px;color:#9aa0ab">{sub[:12]}</div></div>'''

art_cards = ''.join(
    f'<div class="artist-card"><div class="av">{a[0][0]}</div><div class="nm">{a[0][:6]}</div><div class="ct">{a[1]}首</div></div>'
    for a in top_artists)

html = f'''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<style>{css}</style></head>
<body style="margin:0;background:#eceef2">
<div id="app" style="display:flex;min-height:100vh">
  <aside id="sidebar" style="width:200px;background:linear-gradient(180deg,#101740,#0d1230);padding:18px;box-sizing:border-box">
    <div class="logo"><div class="logo-icon" style="width:40px;height:40px;border-radius:10px;display:grid;place-items:center;color:#fff">♪</div>
      <div><b style="color:#fff">苗族曲库</b><small style="color:#a9b3d6;display:block">听见苗乡的声音</small></div></div>
  </aside>
  <main id="main" style="flex:1"><header id="topbar" style="height:60px;background:#fff"></header>
  <section id="content" style="padding:22px">
    <div id="miao-home">
      <div class="kg-banner" style="position:relative;height:200px;border-radius:18px;overflow:hidden;background:linear-gradient(115deg,#2a3b8f,#1c2a66 45%,#0e4d5e)">
        <div class="kg-txt" style="padding:0 40px"><div class="kg-tag">苗族 · 飞歌之乡</div>
          <h2>听见苗乡的声音</h2><p>深靛蓝 × 苗银 × 朱红 × 蝴蝶妈妈 × 苗绣纹样</p></div>
        <div class="kg-embroider"></div></div>
      <div class="miao-embroider-band" style="margin:8px 2px 2px"></div>
      <div class="miao-sec"><b>为你精选</b><span>苗族音乐 · 精心整理</span><i class="miao-seal">苗</i></div>
      <div class="pl-grid miao-picks" style="display:flex;gap:14px;flex-wrap:wrap">{''.join(cov_card(t,i) for i,t in enumerate(picks))}</div>
      <div class="miao-sec"><b>热门歌手</b><span>苗族代表性歌唱者</span><i class="miao-seal">苗</i></div>
      <div class="miao-artists" style="display:flex;gap:16px;overflow-x:auto">{art_cards}</div>
      <div class="miao-sec"><b>猜你喜欢</b><span>根据你的曲库推荐</span><i class="miao-seal">苗</i></div>
      <div class="pl-grid miao-guess" style="display:flex;gap:14px;flex-wrap:wrap">{''.join(cov_card(t,i) for i,t in enumerate(lib[10:16]))}</div>
    </div></section></main></div>
</body></html>'''
Path('preview_beautify.html').write_text(html, encoding='utf-8')
print('preview_beautify.html 已生成, 卡片示例:', len(picks), ' 歌手:', len(top_artists))
