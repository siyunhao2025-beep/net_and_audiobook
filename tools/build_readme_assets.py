#!/usr/bin/env python3
"""Rebuild the original, deterministic README SVG diagrams. No external assets/fonts."""
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/readme"
INK, PAPER, MINT, CORAL, MUTED = "#111f2c", "#fff9ec", "#8cdec3", "#ffa17e", "#adc1cb"
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Microsoft YaHei,PingFang SC,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Consolas,monospace"

def txt(x, y, s, size=24, fill=PAPER, weight=400, family=FONT, extra=""):
    return f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" {extra}>{escape(s)}</text>'

def rect(x, y, w, h, fill, rx=14, stroke=None, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"'+(f' stroke="{stroke}"' if stroke else '')+f' {extra}/>'

def svg(name, height, title, description, parts):
    OUT.mkdir(parents=True, exist_ok=True)
    data = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>', f'<desc id="desc">{escape(description)}</desc>', *parts, '</svg>']
    (OUT / name).write_text("\n".join(data) + "\n", encoding="utf-8")

def hero():
    p = [rect(0, 0, 1200, 442, INK, 24),
         '<path d="M790 0V442" stroke="#37515d" stroke-opacity=".55"/>',
         '<circle cx="1110" cy="54" r="2" fill="#8cdec3"/><circle cx="846" cy="390" r="2" fill="#fff9ec"/><path d="M1143 382h12m-6-6v12" stroke="#ffa17e"/>',
         txt(58, 62, "SPACE WEATHER  /  READ · LISTEN · LEARN", 20, MINT, 600, MONO),
         txt(58, 149, "net-and-audiobook", 58, PAPER, 700, MONO),
         txt(58, 222, "论文，换个打开方式。", 43, PAPER, 650),
         txt(58, 270, "分章节双语网页  +  慢速拼读有声书", 25, MUTED),
         '<path d="M58 311H731" stroke="#37515d"/>']
    for x, label in [(58, "来源可查"), (281, "逐节打卡"), (504, "暂停续做")]:
        p += [f'<circle cx="{x+7}" cy="353" r="5" fill="{MINT}"/>', txt(x+24, 362, label, 25, PAPER, 500)]
    p += [txt(58, 411, "A research note can become a learning companion.", 18, MUTED, 400, MONO),
          '<g id="source-pages" transform="translate(821 76) rotate(-8 100 140)">',
          rect(8, 0, 192, 253, "#47645e", 11), rect(0, 14, 192, 253, PAPER, 11),
          txt(20, 54, "PDF / PPT", 23, INK, 700, MONO),
          '<path d="M20 76h148M20 100h132M20 118h148M20 136h112" stroke="#879b91" stroke-width="5"/>',
          rect(20, 164, 146, 68, "#e7eee2", 6), txt(33, 206, "逐页核对", 25, "#284f47", 600), '</g>',
          '<g id="listening-output" transform="translate(944 136) rotate(5 100 120)">',
          rect(5, 7, 198, 244, "#07131c", 15), rect(0, 0, 198, 244, MINT, 15),
          txt(22, 43, "LEARNING", 21, INK, 700, MONO), txt(22, 72, "COMPANION", 21, INK, 700, MONO),
          '<path d="M23 111v12m12-23v34m12-48v61m12-72v83m12-60v36m12-24v13m12-30v47m12-62v78m12-49v19m12-34v50m12-37v24m12-20v17" stroke="#24594e" stroke-width="5" stroke-linecap="round"/>',
          '<circle cx="43" cy="197" r="22" fill="#111f2c"/><path d="M38 186l16 11-16 11Z" fill="#fff9ec"/>',
          txt(79, 191, "ZH · EN", 20, INK, 700, MONO), txt(79, 218, "A–Z", 20, INK, 700, MONO), '</g>']
    svg("hero.svg", 442, "net-and-audiobook：论文，换个打开方式", "将PDF和PPT经过来源核对，制作成分章节双语学习网页与慢速拼读有声书；支持打卡、追溯与暂停续做。", p)

def workflow():
    p = [rect(0, 0, 1200, 548, PAPER, 20), txt(54, 61, "一份材料，两条学习航线", 38, INK, 700),
         txt(54, 99, "先读懂、再编排；页面和音频共享同一份来源记录。", 23, "#526c70")]
    for x, number, title, sub, color in [(54, "01", "PDF / PPT", "论文与课程材料", "#eee9dc"), (340, "02", "来源核对", "原文、图表、定义", "#e2ece1"), (626, "03", "章节计划", "知识点与术语", "#e2ece1")]:
        p += [rect(x, 157, 234, 128, color, 13), txt(x+22, 190, number, 19, "#526c70", 600, MONO), txt(x+22, 231, title, 29, INK, 700), txt(x+22, 263, sub, 20, "#526c70")]
    p += ['<path d="M288 220h41m-9-7 9 7-9 7M574 220h41m-9-7 9 7-9 7" fill="none" stroke="#536e70" stroke-width="2.5"/>',
          '<path d="M860 221h42v-22h26m-9-7 9 7-9 7M902 221v190h26m-9-7 9 7-9 7" fill="none" stroke="#536e70" stroke-width="2.5"/>',
          rect(928, 157, 218, 128, INK, 13), txt(950, 198, "双语网页", 29, PAPER, 700), txt(950, 238, "读 · 查 · 打卡", 21, MINT),
          rect(928, 343, 218, 128, INK, 13), txt(950, 384, "名词有声书", 27, PAPER, 700), txt(950, 424, "听 · 拼 · 理解", 21, CORAL),
          '<path d="M54 343H860" stroke="#b8c9c3"/>',
          txt(54, 387, "代理负责逐页理解与编写教学内容。", 24, INK, 600),
          txt(54, 426, "脚本负责构建、合成、校验、打包与发布备份。", 23, "#526c70"),
          txt(54, 501, "SHARED SOURCE REFERENCES  /  同一来源，分别适配阅读与聆听", 19, "#526c70", 500, MONO)]
    svg("workflow.svg", 548, "从来源材料到网页与名词有声书的制作流程", "PDF和PPT经过来源核对及章节计划，分为双语网页与名词有声书两条输出。代理理解内容，脚本完成可重复的构建、校验与发布。", p)

def listening():
    p = [rect(0, 0, 1200, 350, INK, 20), txt(54, 61, "一个名词，听完整再出发。", 38, PAPER, 650),
         txt(54, 101, "英文慢读，字母完整；播放器建议保持 1×。", 24, MUTED)]
    items = [("01", "中文名词", "太阳风", "-8%"), ("02", "英文慢读", "Solar wind", "-30% ≈ 0.7×"), ("03", "完整拼写", "S, O, L, A, R.", "-20% ≈ 0.8×"), ("04", "标准解释", "准确的中文定义", "-3%"), ("05", "通俗地说", "听得懂的中文解释", "-3%")]
    for i, (num, title, example, rate) in enumerate(items):
        x = 54 + 223 * i
        p += [f'<path d="M{x} 141h190" stroke="{MINT if i<3 else CORAL}" stroke-width="3"/>', txt(x, 176, num, 20, MUTED, 600, MONO), txt(x, 218, title, 28, PAPER, 650), txt(x, 252 if i==2 else 257, example, 19 if i in (2,4) else 21, MUTED, 400, MONO if i in (1,2) else FONT), txt(x, 321, rate, 22, MINT if i<3 else CORAL, 600, MONO)]
        if i==2: p.append(txt(x, 278, "W, I, N, D.", 19, MUTED, 400, MONO))
    svg("listening.svg", 350, "每个名词的五段朗读顺序与原生语速", "中文名词、英文整词或短语、完整字母拼写、中文标准解释、通俗地说。以Solar wind的全部字母为例，英文约0.7倍速，拼写约0.8倍速。", p)

if __name__ == "__main__":
    hero(); workflow(); listening()
    print("Rebuilt 3 original README SVG assets in assets/readme/")
