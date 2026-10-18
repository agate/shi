"""Check data/poems/*.json against docs/poem-schema.md.

Usage: validate_poems.py [file ...]   (default: every file in data/poems)
Prints one line per problem and exits non-zero if any file fails.
"""

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POEMS = os.path.join(ROOT, "data/poems")

HAN = re.compile(r"^[㐀-鿿\U00020000-\U0002ffff]$")
TONE = "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü"
SYLLABLE = re.compile(rf"^[a-z{TONE}]+$")
CJK = re.compile(r"[㐀-鿿]")
SEASONS = {"spring", "summer", "autumn", "winter"}
FESTIVALS = {"spring-festival", "lantern", "qingming", "duanwu", "qixi", "midautumn", "chongyang",
             "new-year-eve", "hanshi"}
TERMS = set("lichun yushui jingzhe chunfen qingming guyu lixia xiaoman mangzhong xiazhi xiaoshu dashu "
            "liqiu chushu bailu qiufen hanlu shuangjiang lidong xiaoxue daxue dongzhi xiaohan dahan".split())


def bilingual(errs, where, v, need=True):
    if v is None and not need:
        return
    if not isinstance(v, dict) or not isinstance(v.get("zh"), str) or not isinstance(v.get("en"), str):
        errs.append(f"{where}: needs {{zh, en}} strings")
        return
    if not v["zh"].strip() or not v["en"].strip():
        errs.append(f"{where}: empty text")
    if CJK.search(v["en"]):
        errs.append(f"{where}.en: contains Chinese characters")


def check(path):
    errs = []
    try:
        with open(path, encoding="utf-8") as f:
            p = json.load(f)
    except Exception as e:
        return [f"invalid JSON: {e}"]
    if p.get("id") != os.path.basename(path)[:-5]:
        errs.append("id does not match file name")
    if p.get("kind") not in ("shi", "ci"):
        errs.append("kind must be shi or ci")
    if p.get("dynasty") not in ("tang", "song"):
        errs.append("dynasty must be tang or song")
    for k in ("title", "title_en", "author", "author_en"):
        if not isinstance(p.get(k), str) or not p[k].strip():
            errs.append(f"{k}: missing")
    if CJK.search(p.get("title_en", "") + p.get("author_en", "")):
        errs.append("title_en/author_en: contains Chinese characters")
    bilingual(errs, "form", p.get("form"))

    lines = p.get("lines")
    if not isinstance(lines, list) or not lines:
        return errs + ["lines: missing"]
    for i, line in enumerate(lines):
        if not isinstance(line, list) or not line:
            errs.append(f"lines[{i}]: empty")
            continue
        for j, cell in enumerate(line):
            if not (isinstance(cell, list) and len(cell) == 2 and HAN.match(str(cell[0]))
                    and SYLLABLE.match(str(cell[1]))):
                errs.append(f"lines[{i}][{j}]: bad cell {cell!r}")

    def in_line(i, j=None, k=None):
        if not isinstance(i, int) or not 0 <= i < len(lines):
            return False
        n = len(lines[i])
        if j is None:
            return True
        if k is None:
            return isinstance(j, int) and 0 <= j < n
        return isinstance(j, int) and isinstance(k, int) and 0 <= j < k <= n

    for b in p.get("stanza_breaks", []):
        if not in_line(b) or b == 0:
            errs.append(f"stanza_breaks: bad index {b}")
    bilingual(errs, "text_note", p.get("text_note"), need=False)
    for n, r in enumerate(p.get("readings", [])):
        if not in_line(r.get("line"), r.get("pos")):
            errs.append(f"readings[{n}]: bad position")
        elif lines[r["line"]][r["pos"]][0] != r.get("char"):
            errs.append(f"readings[{n}]: char {r.get('char')} is not at that position")
        elif lines[r["line"]][r["pos"]][1] != r.get("pinyin"):
            errs.append(f"readings[{n}]: pinyin differs from lines")
        bilingual(errs, f"readings[{n}]", {"zh": r.get("zh"), "en": r.get("en")})
    for n, g in enumerate(p.get("glosses", [])):
        if not in_line(g.get("line"), g.get("start"), g.get("end")):
            errs.append(f"glosses[{n}]: bad range")
        bilingual(errs, f"glosses[{n}]", {"zh": g.get("zh"), "en": g.get("en")})
    tr = p.get("translation")
    if not isinstance(tr, list) or len(tr) != len(lines):
        errs.append(f"translation: needs {len(lines)} entries, has {len(tr) if isinstance(tr, list) else 0}")
    else:
        for n, t in enumerate(tr):
            bilingual(errs, f"translation[{n}]", t)
    for k in ("background", "author_note", "appreciation"):
        bilingual(errs, k, p.get(k))
    for i in p.get("famous_lines", []):
        if not in_line(i):
            errs.append(f"famous_lines: bad index {i}")
    tags = p.get("tags") or {}
    for k, allowed in (("seasons", SEASONS), ("festivals", FESTIVALS), ("solar_terms", TERMS)):
        bad = [t for t in tags.get(k, []) if t not in allowed]
        if bad:
            errs.append(f"tags.{k}: unknown {bad}")
    if not isinstance(tags.get("themes", []), list):
        errs.append("tags.themes: must be a list")
    for n, u in enumerate(p.get("uncertain", [])):
        bilingual(errs, f"uncertain[{n}]", {"zh": u.get("zh"), "en": u.get("en")})
    return errs


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(POEMS, "*.json")))
    bad = 0
    for path in files:
        errs = check(path)
        if errs:
            bad += 1
            for e in errs[:20]:
                print(f"{os.path.basename(path)}: {e}")
    print(f"{len(files) - bad}/{len(files)} files valid")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
