"""Build the static site into site/ from the close readings and the catalog.

Inputs:  data/poems/*.json (close readings), data/catalog/ranking.json,
         data/build/corpus.sqlite, site/data/calendar.json, site-src/*
Outputs: site/index.html, site/p/<slug>/index.html, site/data/{search,daily}.json,
         site/assets/*, site/404.html, docs/pending.md

A close reading is published only when it passes scripts/validate_poems.py and
its "uncertain" list is empty; the rest are listed in docs/pending.md.
"""

import glob
import html
import json
import os
import re
import shutil
import sqlite3
import sys
import unicodedata
from collections import defaultdict

from pypinyin import Style, lazy_pinyin, pinyin
from pypinyin.pinyin_dict import pinyin_dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_poems import check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def toneless(syllable):
    """'lǚ' -> 'lü': drop the tone mark, keep the umlaut."""
    return unicodedata.normalize("NFC", re.sub("[\\u0300\\u0301\\u0304\\u030c]", "", unicodedata.normalize("NFD", syllable)))


# Readings pypinyin gets wrong in titles and poet names, toned, longest phrase first.
with open(os.path.join(ROOT, "data/curation/pinyin.json"), encoding="utf-8") as f:
    NAME_FIXES = {x["phrase"]: x["pinyin"].split() for x in json.load(f)["phrases"]}
NAME_FIX_RE = re.compile("(" + "|".join(sorted(map(re.escape, NAME_FIXES), key=len, reverse=True)) + ")")
SITE = os.path.join(ROOT, "site")
SRC = os.path.join(ROOT, "site-src")
DB = os.path.join(ROOT, "data/build/corpus.sqlite")
REPO = "https://github.com/agate/shi"
CATALOG_LISTS = ("tang300", "song300", "textbook", "famous")

CDN = "https://cdn.jsdelivr.net/npm/"
# The poem fonts a reader can choose; the first is the default.
FONTS = [
    ("hwmc", "Huiwen-mincho", "汇文明朝体", "Huiwen Mincho", "@chinese-fonts/hwmct@3.0.0/dist/汇文明朝体/result.css"),
    ("jxzk", "jiangxizhuokai", "江西拙楷", "Jiangxi Zhuokai", "@chinese-fonts/jxzk@3.0.0/dist/江西拙楷/result.css"),
    ("crgk", "chengrongguangke", "程荣光刻楷", "Cheng Rongguang Kekai",
     "@chinese-fonts/crgkk@2.0.0/dist/程荣光刻楷/result.css"),
    ("kx", "nzgrKangxi", "康熙字典体", "Kangxi Dictionary", "@chinese-fonts/rzjkxzdmh@3.0.0/dist/nzgrKangxi/result.css"),
    ("twk", "TW-Kai-Aligned", "全字库正楷体", "TW-Kai", "@xiao-xue-seng/tw-kai-aligned@1.0.3/index.css"),
    ("zmxs", "Zhi Mang Xing", "志莽行书", "Zhi Mang Xing", "@chinese-fonts/zqzmxs@3.0.0/dist/钟齐志莽行书/result.css"),
    ("lc", "Long Cang", "龙藏体", "Long Cang", "@chinese-fonts/yzklct@3.0.0/dist/有字库龙藏体/result.css"),
    ("hlxs", "hongleixingshu", "鸿雷行书", "Honglei Xingshu", "@chinese-fonts/hlxsjt@3.0.0/dist/鸿雷行书简体/result.css"),
    ("qtbf", "qiantubifengshouxieti", "千图笔锋手写体", "Qiantu Bifeng",
     "@chinese-fonts/qtbfsxt@3.0.0/dist/千图笔锋手写体/result.css"),
]
DYNASTY = {"tang": ("Tang", "唐"), "song": ("Song", "宋")}
TITLE_PREFIX = re.compile(r"^(相和歌辞|杂曲歌辞|横吹曲辞|鼓吹曲辞|琴曲歌辞|清商曲辞|舞曲歌辞|近代曲辞|新乐府|辋川集|金陵五题)\s+")
HAN = re.compile(r"[㐀-鿿]")

e = html.escape


def font_list():
    from urllib.parse import quote
    return [{"key": k, "family": fam, "zh": zh, "en": en, "css": CDN + quote(path, safe="/@.")}
            for k, fam, zh, en, path in FONTS]


def head(title, description, base, extra=""):
    fonts = json.dumps(font_list(), ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en" data-lang="en" data-base="{base}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <title>{e(title)}</title>
    <meta name="description" content="{e(description)}" />
    <meta name="theme-color" content="#fafafa" />
    <link rel="icon" type="image/svg+xml" href="{base}assets/scroll.svg" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500&family=JetBrains+Mono&display=swap" />
    <!-- Chinese UI text: LXGW WenKai from jsDelivr. Google Fonts only has the Traditional (TC) build, whose punctuation sits mid-line. -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/lxgw-wenkai-webfont@1.7.0/lxgwwenkai-regular.css" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/lxgw-wenkai-webfont@1.7.0/lxgwwenkai-bold.css" />
    <script>
      window.SHI_FONTS = {fonts};
      // Same language mechanism as honghao.me: ?lang= wins, then the saved choice (shared across honghao.me),
      // then the browser. The saved poem font and pinyin setting are applied here too, before first paint.
      (function () {{
        var d = document.documentElement, get = function (k) {{ try {{ return localStorage.getItem(k); }} catch (e) {{ return null; }} }};
        var lang = new URLSearchParams(location.search).get('lang');
        if (lang !== 'en' && lang !== 'zh') lang = get('lang');
        if (lang !== 'en' && lang !== 'zh') lang = /^zh/i.test(navigator.language || '') ? 'zh' : 'en';
        d.dataset.lang = lang;
        d.lang = lang === 'zh' ? 'zh-CN' : 'en';
        var py = new URLSearchParams(location.search).get('pinyin');
        if (py === '1' || (py !== '0' && get('shi.pinyin') === '1')) d.classList.add('py-all');
        var key = get('shi.font'), f = window.SHI_FONTS[0];
        window.SHI_FONTS.forEach(function (x) {{ if (x.key === key) f = x; }});
        document.write('<link id="font-' + f.key + '" rel="stylesheet" href="' + f.css + '">');
        d.style.setProperty('--poem', "'" + f.family + "', 'LXGW WenKai', 'Songti SC', serif");
        d.dataset.font = f.key;
      }})();
    </script>
    <link rel="stylesheet" href="{base}assets/style.css" />{extra}
  </head>"""


def nav(base):
    return f"""
    <header class="wrap">
      <nav class="mono">
        <a href="{base}" class="home"><span lang="en">Shi · Tang &amp; Song poems</span><span lang="zh">诗 · 唐诗宋词精读</span></a>
        <div class="links">
          <a href="{base}#search"><span lang="en">Search</span><span lang="zh">搜索</span></a>
          <span class="toggle" role="group" aria-label="Language">
            <button type="button" data-set-lang="en">EN</button>
            <button type="button" data-set-lang="zh">中</button>
          </span>
        </div>
      </nav>
    </header>"""


def footer(base):
    return f"""
    <footer class="wrap mono">
      <!-- Home link is relative ("/") so it follows the main domain if it ever changes; the label shows the live host. -->
      <div class="foot">
        <a href="/">← <span data-host>honghao.me</span></a> ·
        <span lang="en">Made by <a href="/">Hong, Hao</a> · notes written with AI, reviewed against sources · poem texts from the chinese-poetry corpus (MIT)</span>
        <span lang="zh"><a href="/">Hong, Hao</a> 制作 · 精读由 AI 撰写并按资料核对 · 诗词原文来自 chinese-poetry 数据集（MIT 许可）</span>
        · <a href="{REPO}">github.com/agate/shi</a>
      </div>
    </footer>
    <script src="{base}assets/app.js"></script>
  </body>
</html>
"""


def bi(en, zh, tag="span", cls=""):
    c = f' class="{cls}"' if cls else ""
    return f'<{tag} lang="en"{c}>{e(en)}</{tag}><{tag} lang="zh"{c}>{e(zh)}</{tag}>'


def paras(text, lang):
    return "".join(f'<p lang="{lang}">{e(p.strip())}</p>' for p in re.split(r"\n+", text) if p.strip())


def name_pinyin(s):
    """Toneless pinyin of a title or poet name, with the fixes in data/curation/pinyin.json.
    Only names use them: the read-aloud swap below must see pypinyin's own readings."""
    out = []
    for part in NAME_FIX_RE.split(s) if NAME_FIXES else [s]:
        out += [toneless(x) for x in NAME_FIXES[part]] if part in NAME_FIXES else lazy_pinyin(part)
    return out


def slugify(title, author, taken):
    base = "-".join(s for s in ("".join(name_pinyin(re.sub(r"[^㐀-鿿·]", "", t))) for t in title.split("·")) if s)
    base = re.sub(r"[^a-z0-9-]", "", base.replace("ü", "v")) or "poem"
    for cand in (base, base + "-" + "".join(name_pinyin(author)), None):
        if cand and cand not in taken:
            taken.add(cand)
            return cand
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    taken.add(f"{base}-{n}")
    return f"{base}-{n}"


def initials(s):
    return "".join(p[0] for p in name_pinyin(s) if p and p[0].isalpha())


def plain(s):
    return "".join(name_pinyin(s)).replace("ü", "v")


# --- Read-aloud text: swap characters the browser voice would misread for a homophone ---

def homophones():
    """Single-reading common characters by toned syllable, e.g. 'xiá' -> '霞'."""
    by_sound = {}
    for cp, readings in sorted(pinyin_dict.items()):
        if "," in readings:
            continue
        ch = chr(cp)
        try:
            b = ch.encode("gb2312")
        except UnicodeEncodeError:
            continue
        if 0xB0 <= b[0] <= 0xD7:  # GB2312 level 1: the 3,755 most common characters
            by_sound.setdefault(readings, ch)
    return by_sound


SOUNDS = homophones()


def speak_line(cells):
    text = "".join(c[0] for c in cells)
    default = [r[0] for r in pinyin(text, style=Style.TONE)]
    out = []
    for (ch, want), got in zip(cells, default):
        out.append(SOUNDS.get(want, ch) if want != got else ch)
    return "".join(out)


def speak_name(s):
    """speak_line for a title or poet name: the readings to say are pypinyin's, with the name fixes."""
    def run(m):
        text = m.group(0)
        want = [r[0] for r in pinyin(text, style=Style.TONE)]
        for f in NAME_FIX_RE.finditer(text) if NAME_FIXES else []:
            want[f.start():f.end()] = NAME_FIXES[f.group(0)]
        return speak_line(list(zip(text, want)))
    return re.sub(r"[㐀-鿿]+", run, s)


# --- Tone change (变调) of 一 and 不 ---
# Writers marked these inconsistently, so the build applies one rule: show the tone
# actually spoken, as primary-school textbooks do. Notes that only explained this
# tone change are dropped; the tap hint on every page explains it once.

TONE_OF = {c: t for t, cs in enumerate(("āēīōūǖ", "áéíóúǘ", "ǎěǐǒǔǚ", "àèìòùǜ"), 1) for c in cs}


def tone(syllable):
    for ch in syllable:
        if ch in TONE_OF:
            return TONE_OF[ch]
    return 0


def sandhi(p):
    changed = set()
    for i, line in enumerate(p["lines"]):
        for j, cell in enumerate(line):
            ch, py = cell
            nxt = line[j + 1][1] if j + 1 < len(line) else None
            if ch == "不" and py in ("bù", "bú"):
                cell[1] = "bú" if nxt and tone(nxt) == 4 else "bù"
            elif ch == "一" and py in ("yī", "yí", "yì"):
                prev = line[j - 1][0] if j else ""
                if not nxt or prev in "第初十" or line[j + 1][0] in "一二三四五六七八九十":
                    cell[1] = "yī"
                else:
                    cell[1] = "yí" if tone(nxt) == 4 else "yì"
            else:
                continue
            changed.add((i, j))
    p["readings"] = [r for r in p.get("readings", []) if (r["line"], r["pos"]) not in changed]


# --- Pages ---

def poem_page(p, nav_prev, nav_next, base):
    lines = p["lines"]
    longest = max(len(l) for l in lines)
    size = max(18, min(30, int(330 / (longest * 1.32))))
    gl = {(g["line"], i) for g in p.get("glosses", []) for i in range(g["start"], g["end"])}
    rd = {(r["line"], r["pos"]) for r in p.get("readings", [])}
    breaks = set(p.get("stanza_breaks", []))
    rows = []
    for i, line in enumerate(lines):
        cls = "ln" + (" brk" if i in breaks else "")
        cells = "".join(
            f'<span class="c{" gl" if (i, j) in gl else ""}{" rd" if (i, j) in rd else ""}" data-l="{i}" data-p="{j}">'
            f"<i>{e(py)}</i><b>{e(ch)}</b></span>"
            for j, (ch, py) in enumerate(line))
        rows.append(f'<p class="{cls}">{cells}</p>')
    dyn_en, dyn_zh = DYNASTY[p["dynasty"]]
    note = ""
    if p.get("text_note"):
        note = f'<div class="note">{bi(p["text_note"]["en"], p["text_note"]["zh"], "p")}</div>'

    sections = []

    def sec(en, zh, body):
        n = len(sections) + 1
        sections.append(f"""
      <section class="sec">
        <div class="num mono">{n:02d}</div>
        <div>
          <h2>{bi(en, zh)}</h2>
          {body}
        </div>
      </section>""")

    tr = "".join(
        f'<li{" class=\"brk\"" if i in breaks else ""}><span class="o">{e("".join(c[0] for c in lines[i]))}</span>'
        f'{bi(t["en"], t["zh"])}</li>' for i, t in enumerate(p["translation"]))
    sec("Line by line", "逐句翻译", f'<ol class="tr">{tr}</ol>')
    if p.get("glosses"):
        items = []
        for g in p["glosses"]:
            cells = lines[g["line"]][g["start"]:g["end"]]
            word, py = "".join(c[0] for c in cells), " ".join(c[1] for c in cells)
            items.append(f'<div><dt>{e(word)}<span class="mono">{e(py)}</span></dt><dd>{bi(g["en"], g["zh"])}</dd></div>')
        sec("Words", "字词注释", f'<dl class="gloss">{"".join(items)}</dl>')
    if p.get("readings"):
        items = "".join(
            f'<div><dt>{e(r["char"])}<span class="mono">{e(r["pinyin"])}</span></dt><dd>{bi(r["en"], r["zh"])}</dd></div>'
            for r in p["readings"])
        sec("How to read it", "读音", f'<dl class="gloss">{items}</dl>')
    sec("Background", "创作背景", f'<div class="prose">{paras(p["background"]["en"], "en")}{paras(p["background"]["zh"], "zh")}</div>')
    sec("The poet", "作者", f'<div class="prose">{paras(p["author_note"]["en"], "en")}{paras(p["author_note"]["zh"], "zh")}</div>')
    sec("The mood", "意境", f'<div class="prose">{paras(p["appreciation"]["en"], "en")}{paras(p["appreciation"]["zh"], "zh")}</div>')

    def pager_link(target, en, zh):
        if not target:
            return "<span></span>"
        return f'<a href="{base}p/{target["slug"]}/"><span class="mono">{bi(en, zh)}</span><b>{e(target["title"])}</b></a>'

    kind_en, kind_zh = ("Tang poem", "唐诗") if p["kind"] == "shi" else ("Song lyric", "宋词")
    data = {
        "lines": lines,
        "glosses": p.get("glosses", []),
        "readings": p.get("readings", []),
        "speak": [speak_line(l) for l in lines],
        "speakTitle": speak_name(p["title"].replace("·", "，") + "。" + p["author"] + "。"),
        "sample": "".join(c[0] for c in lines[0])[:7],
    }
    desc = f'{p["title"]} · {p["author"]} — {p["title_en"]} by {p["author_en"]}: pinyin, notes, translation and background.'
    return (head(f'{p["title"]} · {p["author"]} — 诗', desc, base) + f"""
  <body class="has-bar">{nav(base)}
    <main class="wrap">
      <article class="poem" style="--size:{size}px">
        <p class="mono">{bi(f"No. {p['rank']} · {kind_en} · {p['form']['en']}", f"第 {p['rank']} 首 · {kind_zh} · {p['form']['zh']}") if p['rank'] else bi(f"{kind_en} · {p['form']['en']}", f"{kind_zh} · {p['form']['zh']}")}</p>
        <h1>{e(p["title"])}</h1>
        <p class="by">{e(p["author"])}<span class="mono">{bi(f"{p['author_en']} · {dyn_en}", dyn_zh)}</span></p>
        <p class="en-title mono" lang="en">{e(p["title_en"])}</p>
        <p class="en-title mono" lang="zh">&nbsp;</p>
        <div class="lines">{"".join(rows)}</div>
        <p class="tap-hint mono">{bi("Tap a character for its pinyin. Underlined words have notes. 一 and 不 are marked with the tone you actually say.", "点一个字看拼音。字下有虚线的，点开有注释。“一”“不”标的是实际读出来的变调。")}</p>
        {note}
      </article>{"".join(sections)}
      <div class="pager">{pager_link(nav_prev, "← Previous", "← 上一首")}{pager_link(nav_next, "Next →", "下一首 →")}</div>
    </main>
    <div class="bar" role="toolbar" aria-label="Reading tools">
      <div class="in">
        <button type="button" id="btn-pinyin" aria-pressed="false">{bi("Pinyin", "拼音")}<span class="mono">{bi("show all", "全部显示")}</span></button>
        <button type="button" id="btn-font">{bi("Font", "字体")}<span class="mono">{bi("change", "换字体")}</span></button>
        <button type="button" id="btn-speak" aria-pressed="false">{bi("Listen", "朗读")}<span class="mono">{bi("read aloud", "读给我听")}</span></button>
      </div>
    </div>
    <div class="sheet" id="sheet" aria-hidden="true" role="dialog" aria-modal="true">
      <div class="shade"></div>
      <div class="panel"><div class="in">
        <div class="top"><span class="label mono"></span><button type="button" class="close" aria-label="Close">×</button></div>
        <div class="body"></div>
      </div></div>
    </div>
    <script type="application/json" id="poem-data">{json.dumps(data, ensure_ascii=False).replace("</", "<\\/")}</script>""" + footer(base))


def stub_page(c, base):
    dyn_en, dyn_zh = DYNASTY[c["dynasty"]]
    # Same rule as close readings: one sentence per line, no punctuation.
    sents = ["".join(HAN.findall(x)) for x in re.split(r"[，。？！；：\n]", c["text"])]
    lines = "".join(f"<p>{e(x)}</p>" for x in sents if x)
    return (head(f'{c["title"]} · {c["author"]} — 诗', f'{c["title"]} · {c["author"]}', base) + f"""
  <body>{nav(base)}
    <main class="wrap">
      <article class="poem">
        <p class="mono">{bi("Close reading not written yet", "精读制作中")}</p>
        <h1>{e(c["title"])}</h1>
        <p class="by">{e(c["author"])}<span class="mono">{bi(dyn_en, dyn_zh)}</span></p>
        <div class="prose" style="font-family:var(--poem);font-size:20px;line-height:2;margin-top:18px">{lines}</div>
        <div class="note">{bi("This poem is in the catalog, but its close reading (pinyin, notes, translation) is not written yet. The text is shown as it appears in the source corpus.", "这首诗已经收进目录，但精读（拼音、注释、翻译）还没做好。这里先显示原始资料里的文字。", "p")}</div>
      </article>
    </main>""" + footer(base))


def home_page(published, catalog, stats, base):
    def items(kind):
        rows = []
        for p in sorted((x for x in published if x["kind"] == kind and x["rank"]), key=lambda x: x["rank"]):
            first = "".join(c[0] for c in p["lines"][0])
            rows.append(f'<li><a href="{base}p/{p["slug"]}/"><span class="rk mono">{p["rank"]:03d}</span>'
                        f'<span class="tt">{e(p["title"])}<small>{e(p["author"])}</small></span>'
                        f'<span class="fl">{e(first)}</span></a></li>')
        return "".join(rows)

    done, total = stats["published"], stats["catalog"]
    pct = 100 * done / total if total else 0
    return (head("诗 · Tang & Song poems, read closely", "Close readings of the best-known Tang poems and Song lyrics: pinyin on every character, notes, translation, background and mood, in Chinese and English.", base) + f"""
  <body>{nav(base)}
    <main class="wrap">
      <section class="hero">
        <div class="mono">{bi("Tang poems · Song lyrics · pinyin, notes, translation", "唐诗 · 宋词 · 拼音、注释、翻译")}</div>
        <h1>{bi("Read a classical poem, one character at a time.", "一字一字，读懂一首古诗。", "span")}</h1>
        <p class="lede" lang="en">Every character has its pinyin. Every hard word has a note. Each poem comes with a line-by-line translation, the story behind it, and the scene it paints. For readers of any age.</p>
        <p class="lede" lang="zh">每个字都有拼音，每个难词都有注释。每首诗配逐句翻译、创作背景和意境赏析。适合所有年龄的人。</p>
      </section>

      <div class="search" id="search">
        <label>
          <input id="q" type="search" enterkeyhint="search" autocomplete="off" autocapitalize="off" spellcheck="false"
            aria-label="Search poems" data-ph-en="Title, poet, line or pinyin" data-ph-zh="标题、作者、诗句或拼音" />
          <button type="button" class="clear" aria-label="Clear" hidden>×</button>
        </label>
        <p class="hint mono">{bi(f"Searches all {total} poems in the catalog: titles, poets, lines, pinyin (jingyesi) or initials (jys).", f"在目录的 {total} 首诗里搜：标题、作者、诗句、全拼（jingyesi）或首字母（jys）。")}</p>
      </div>
      <div class="results" id="results" hidden></div>

      <div id="browse">
        <section class="sec">
          <div class="num mono">01</div>
          <div>
            <h2>{bi("Today's poem", "今日一首")}</h2>
            <div id="daily"><p class="mono">{bi("Picking a poem for today…", "正在为今天挑一首诗……")}</p></div>
          </div>
        </section>

        <section class="sec">
          <div class="num mono">02</div>
          <div>
            <h2>{bi("The best-known 100 of each", "最出名的各 100 首")}</h2>
            <div class="tabs" role="tablist">
              <button type="button" role="tab" aria-selected="true" aria-controls="tab-shi">{bi("Tang poems", "唐诗")}</button>
              <button type="button" role="tab" aria-selected="false" aria-controls="tab-ci">{bi("Song lyrics", "宋词")}</button>
            </div>
            <ul class="list" id="tab-shi" role="tabpanel">{items("shi")}</ul>
            <ul class="list" id="tab-ci" role="tabpanel" hidden>{items("ci")}</ul>
          </div>
        </section>

        <section class="sec">
          <div class="num mono">03</div>
          <div>
            <h2>{bi("Progress", "完成进度")}</h2>
            <p class="mono">{bi(f"{done} of {total} poems in the catalog have a close reading", f"目录里 {total} 首诗，已完成精读 {done} 首")}</p>
            <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="{total}" aria-valuenow="{done}"><span style="width:{pct:.1f}%"></span></div>
            <div class="stats">
              <div><b>{stats["tang"]:,}</b><span class="mono">{bi("Tang poems in the database", "数据库里的唐诗")}</span></div>
              <div><b>{stats["song"]:,}</b><span class="mono">{bi("Song lyrics in the database", "数据库里的宋词")}</span></div>
              <div><b>{total}</b><span class="mono">{bi("in the catalog", "收进目录")}</span></div>
            </div>
            <div class="prose" style="margin-top:16px">
              <p lang="en">The database holds every Tang poem and Song lyric in the open chinese-poetry corpus. The catalog is the part worth reading first: 300 Tang Poems, 300 Song Lyrics, the poems taught in school, and other widely quoted ones. The top 100 of each are ranked by school textbooks, the two anthologies, search-engine counts and how widely they are quoted.</p>
              <p lang="zh">数据库收了开源 chinese-poetry 数据集里的全部唐诗和宋词。目录是最值得先读的那一部分：《唐诗三百首》《宋词三百首》、课本里的诗词，以及其他广为传诵的名篇。各 100 首按这几个维度排名：是否进课本、是否收进两部选集、搜索引擎热度、是否广为传诵。</p>
            </div>
          </div>
        </section>
      </div>
    </main>""" + footer(base))


def not_found(base):
    return (head("Not found — 诗", "Page not found", base) + f"""
  <body>{nav(base)}
    <main class="wrap">
      <h1>{bi("This page is not here.", "这一页不存在。")}</h1>
      <p class="lede"><a href="{base}">{bi("Back to all poems →", "回到全部诗词 →")}</a></p>
    </main>""" + footer(base))


# --- Data ---

def load_ranks():
    """Rank of each of the top 100 Tang shi and top 100 Song ci."""
    with open(os.path.join(ROOT, "data/catalog/ranking.json"), encoding="utf-8") as f:
        ranking = json.load(f)
    return {s["id"]: s["rank"] for k in ("shi", "ci") for s in ranking[k] if s["selected"]}


def load_published(catalog, rank):
    """Close readings of catalog poems that pass validation and have no open question."""
    in_catalog = {c["id"] for c in catalog}
    published, pending = [], []
    for path in sorted(glob.glob(os.path.join(ROOT, "data/poems/*.json"))):
        with open(path, encoding="utf-8") as f:
            p = json.load(f)
        if p["id"] not in in_catalog:
            continue  # an excluded duplicate (data/curation/catalog-exclude.json)
        errs = check(path)
        if errs or p.get("uncertain"):
            pending.append((p, errs))
            continue
        p["rank"] = rank.get(p["id"])
        sandhi(p)
        published.append(p)
    missing = [f'{c["author"]}《{c["title"]}》 (`{c["id"]}`)' for c in catalog
               if not os.path.exists(os.path.join(ROOT, f'data/poems/{c["id"]}.json'))]
    return published, pending, missing


def load_catalog(db, prefer):
    """Every poem in the anthologies and curated lists, one copy each. When the corpus holds
    a poem twice, the copy in `prefer` (the top 200) wins."""
    rows = db.execute(
        f"""SELECT p.id, p.kind, p.dynasty, p.author, p.title, p.text FROM poems p
            WHERE p.id IN (SELECT poem_id FROM lists WHERE list IN ({','.join('?' * len(CATALOG_LISTS))}))
               OR p.id LIKE 'sup-%'
               OR p.id IN ({','.join('?' * len(prefer))})""", (*CATALOG_LISTS, *prefer)).fetchall()
    def written(pid):
        return os.path.exists(os.path.join(ROOT, f"data/poems/{pid}.json"))

    # Prefer the top-200 copy, then a copy that already has a close reading.
    rows.sort(key=lambda r: (r[0] not in prefer, not written(r[0]), r[0]))
    with open(os.path.join(ROOT, "data/curation/catalog-exclude.json"), encoding="utf-8") as f:
        excluded = {x["id"] for x in json.load(f)["exclude"]}
    kept, out = defaultdict(list), []
    for pid, kind, dyn, author, title, text in rows:
        if pid in excluded:
            continue
        opening = "".join(HAN.findall(text))[:14]
        # Variant copies differ by a character or two, so compare openings loosely.
        if any(same_opening(opening, o) for o in kept[author]):
            continue
        kept[author].append(opening)
        out.append({"id": pid, "kind": kind, "dynasty": dyn, "author": author,
                    "title": TITLE_PREFIX.sub("", title).strip(), "text": text})
    return out


def drop_twins(published, pending, rank):
    """Corpus copies of one poem can differ enough to pass load_catalog, but their close
    readings use the same taught text. Keep one per opening: a top-200 copy first, then one
    with no open question. Returns (kept, dropped)."""
    def opening(p):
        return "".join(c[0] for l in p["lines"] for c in l)[:14]

    candidates = [(p, True) for p in published] + [(p, False) for p, errs in pending if not errs]
    candidates.sort(key=lambda x: (x[0]["id"] not in rank, not x[1], x[0]["id"]))
    kept_openings, dropped = [], []
    keep_ids = set()
    for p, ok in candidates:
        o = opening(p)
        if any(same_opening(o, k) for k in kept_openings):
            dropped.append(p)
            continue
        kept_openings.append(o)
        keep_ids.add(p["id"])
    pending[:] = [(p, errs) for p, errs in pending if errs or p["id"] in keep_ids]
    return [p for p in published if p["id"] in keep_ids], dropped


def same_opening(a, b):
    n = min(len(a), len(b))
    return n > 0 and sum(x == y for x, y in zip(a, b)) / n >= 0.7


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    db = sqlite3.connect(DB)
    rank = load_ranks()
    catalog = load_catalog(db, set(rank))
    write(os.path.join(ROOT, "data/catalog/catalog.json"), json.dumps(
        [{k: c[k] for k in ("id", "kind", "author", "title")} for c in catalog], ensure_ascii=False, indent=1))
    published, pending, missing = load_published(catalog, rank)
    published, dropped = drop_twins(published, pending, rank)
    dropped_ids = {p["id"] for p in dropped}
    catalog = [c for c in catalog if c["id"] not in dropped_ids]
    write(os.path.join(ROOT, "data/catalog/catalog.json"), json.dumps(
        [{k: c[k] for k in ("id", "kind", "author", "title")} for c in catalog], ensure_ascii=False, indent=1))
    by_id = {p["id"]: p for p in published}

    for d in ("p", "assets"):
        shutil.rmtree(os.path.join(SITE, d), ignore_errors=True)
    os.makedirs(os.path.join(SITE, "assets"))
    for name in ("style.css", "app.js", "scroll.svg"):
        shutil.copy(os.path.join(SRC, name), os.path.join(SITE, "assets", name))

    taken = set()
    def order(p):
        return (p["kind"] != "shi", p["rank"] is None, p["rank"] or 0, p["id"])

    for p in sorted(published, key=order):
        p["slug"] = slugify(p["title"], p["author"], taken)
    for c in catalog:
        c["slug"] = by_id[c["id"]]["slug"] if c["id"] in by_id else slugify(c["title"], c["author"], taken)

    for kind in ("shi", "ci"):
        seq = sorted((p for p in published if p["kind"] == kind), key=order)
        for i, p in enumerate(seq):
            write(os.path.join(SITE, "p", p["slug"], "index.html"),
                  poem_page(p, seq[i - 1] if i else None, seq[i + 1] if i + 1 < len(seq) else None, "../../"))
    for c in catalog:
        if c["id"] not in by_id:
            write(os.path.join(SITE, "p", c["slug"], "index.html"), stub_page(c, "../../"))

    search = []
    for c in catalog:
        p = by_id.get(c["id"])
        title = p["title"] if p else c["title"]
        text = " ".join("".join(x[0] for x in l) for l in p["lines"]) if p else " ".join(
            "".join(HAN.findall(s)) for s in re.split(r"[，。？！；：\n]", c["text"]) if HAN.search(s))
        search.append({"s": c["slug"], "t": title, "a": c["author"], "k": c["kind"], "r": (p["rank"] or 0) if p else 0,
                       "d": 1 if p else 0, "x": text, "tp": plain(title.replace("·", "")),
                       "ti": initials(title), "ap": plain(c["author"]), "ai": initials(c["author"])})
    write(os.path.join(SITE, "data/search.json"), json.dumps(search, ensure_ascii=False, separators=(",", ":")))

    daily = []
    for p in published:
        idx = p.get("famous_lines") or [0, 1]
        idx = sorted(idx)[:2] if len(idx) >= 2 else [idx[0], min(idx[0] + 1, len(p["lines"]) - 1)]
        idx = sorted(set(idx))
        tags = p.get("tags", {})
        daily.append({"s": p["slug"], "t": p["title"], "a": p["author"],
                      "l": ["".join(c[0] for c in p["lines"][i]) for i in idx],
                      "g": {k: tags.get(k, []) for k in ("seasons", "festivals", "solar_terms")}})
    write(os.path.join(SITE, "data/daily.json"), json.dumps(daily, ensure_ascii=False, separators=(",", ":")))

    stats = {"published": len(published), "catalog": len(catalog),
             "tang": db.execute("SELECT count(*) FROM poems WHERE kind='shi'").fetchone()[0],
             "song": db.execute("SELECT count(*) FROM poems WHERE kind='ci'").fetchone()[0]}
    write(os.path.join(SITE, "index.html"), home_page(published, catalog, stats, "./"))
    write(os.path.join(SITE, "404.html"), not_found("/shi/"))

    lines = ["# Pending close readings", "",
             "Generated by `scripts/build_site.py`. These poems are not on the site yet: their close reading",
             "has an open question (`uncertain`), fails validation, or has not been written.", ""]
    for p, errs in pending:
        lines.append(f"## {p.get('title', p['id'])} · {p.get('author', '')}  (`{p['id']}`)")
        for u in p.get("uncertain", []):
            lines.append(f"- **{u.get('field', '?')}**: {u.get('zh', '')} / {u.get('en', '')}")
        for err in errs[:5]:
            lines.append(f"- validation: {err}")
        lines.append("")
    if dropped:
        lines += ["## Dropped as duplicates", "",
                  "Second copies of a poem already on the site (the corpus holds them under another title or author).", ""]
        lines += [f'- {p["author"]}《{p["title"]}》 (`{p["id"]}`)' for p in dropped] + [""]
    if missing:
        lines += ["## Not written yet", ""] + [f"- {m}" for m in missing] + [""]
    write(os.path.join(ROOT, "docs/pending.md"), "\n".join(lines))
    print(f"published {len(published)}, pending {len(pending)}, missing {len(missing)}, catalog {len(catalog)}")


if __name__ == "__main__":
    main()
