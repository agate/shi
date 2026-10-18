"""Score every poem in the corpus on how well known it is, and pick the top 100
Tang shi and top 100 Song ci.

Dimensions (each 0..1):
  textbook    taught in mainland school textbooks (data/curation/textbook.json)
  anthology   in 唐诗三百首 (shi) or 宋词三百首 (ci)
  qianjiashi  in 千家诗 (shi only)
  famous      widely quoted outside textbooks (data/curation/famous.json)
  search      search-engine hit counts for "author + title", as a percentile within
              the kind, averaged over engines. For ci the query was "author + tune
              name", so every 浣溪沙 by one author shares a count; it gets less weight.
  author      how often the author appears in the anthologies and textbooks
Manual adjustments live in data/curation/overrides.json, each with a reason.

Writes data/catalog/ranking.json (top 300 of each kind with every dimension).
"""

import json
import math
import os
import re
import sqlite3
from bisect import bisect_left
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data/build/corpus.sqlite")
OUT = os.path.join(ROOT, "data/catalog/ranking.json")
ENGINES = ("baidu", "so360", "bing", "bing_en", "google")
WEIGHTS = {
    "shi": {"textbook": 0.35, "anthology": 0.15, "qianjiashi": 0.05, "famous": 0.20, "search": 0.20, "author": 0.05},
    "ci": {"textbook": 0.40, "anthology": 0.15, "qianjiashi": 0.00, "famous": 0.25, "search": 0.10, "author": 0.10},
}
ANTHOLOGY = {"shi": "tang300", "ci": "song300"}
KEEP = 300
PICK = 100


def percentiles(values):
    """Map each value to the share of values below it (0..1)."""
    ranked = sorted(values)
    n = max(len(ranked) - 1, 1)
    return lambda v: bisect_left(ranked, v) / n


def dedupe(scored):
    """The corpus holds some poems twice (e.g. 将进酒 and 鼓吹曲辞 将进酒). Keep the
    best-scoring copy of each author + opening, merging the lists both appear in."""
    seen, out = {}, []
    for s in scored:
        key = (s["author"], norm(s["first_line"])[:8])
        if key in seen:
            seen[key]["lists"] = sorted(set(seen[key]["lists"]) | set(s["lists"]))
            continue
        seen[key] = s
        out.append(s)
    return out


def norm(s):
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


def rank_kind(db, kind, overrides):
    rows = db.execute(
        f"SELECT id, author, title, text, {', '.join(ENGINES)} FROM poems WHERE kind=?", (kind,)
    ).fetchall()
    lists = {}
    for name, pid in db.execute("SELECT list, poem_id FROM lists"):
        lists.setdefault(pid, set()).add(name)

    pct = {}
    for i, e in enumerate(ENGINES):
        vals = [math.log1p(r[4 + i]) for r in rows if r[4 + i]]
        pct[e] = percentiles(vals)

    author_hits = Counter()
    for r in rows:
        author_hits[r[1]] += len(lists.get(r[0], set()) & {"textbook", ANTHOLOGY[kind], "qianjiashi", "famous"})
    author_pct = percentiles([v for v in author_hits.values() if v])

    w = WEIGHTS[kind]
    scored = []
    for r in rows:
        pid, author, title, text = r[:4]
        member = lists.get(pid, set())
        engine_scores = [pct[e](math.log1p(r[4 + i])) for i, e in enumerate(ENGINES) if r[4 + i]]
        dims = {
            "textbook": 1.0 if "textbook" in member else 0.0,
            "anthology": 1.0 if ANTHOLOGY[kind] in member else 0.0,
            "qianjiashi": 1.0 if "qianjiashi" in member else 0.0,
            "famous": 1.0 if "famous" in member else 0.0,
            "search": sum(engine_scores) / len(engine_scores) if engine_scores else 0.0,
            "author": author_pct(author_hits[author]) if author_hits[author] else 0.0,
        }
        score = sum(w[k] * v for k, v in dims.items())
        adj = overrides.get(pid)
        if adj:
            score += adj["boost"]
        scored.append({
            "id": pid, "kind": kind, "author": author, "title": title,
            "first_line": text.split("\n")[0], "score": round(score, 4),
            "dims": {k: round(v, 3) for k, v in dims.items()},
            "lists": sorted(member), **({"override": adj["reason"]} if adj else {}),
        })
    scored.sort(key=lambda x: -x["score"])
    scored = dedupe(scored)
    for i, s in enumerate(scored[:KEEP]):
        s["rank"] = i + 1
        s["selected"] = i < PICK
    return scored[:KEEP]


def main():
    path = os.path.join(ROOT, "data/curation/overrides.json")
    overrides = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            overrides = {o["id"]: o for o in json.load(f)["overrides"]}
    db = sqlite3.connect(DB)
    out = {"weights": WEIGHTS, "shi": rank_kind(db, "shi", overrides), "ci": rank_kind(db, "ci", overrides)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for kind in ("shi", "ci"):
        print(f"== {kind}")
        for s in out[kind][:130]:
            print(f'{s["rank"]:3} {s["score"]:.3f} {s["author"]}《{s["title"]}》{s["first_line"][:12]}  {",".join(s["lists"])} s={s["dims"]["search"]:.2f}')


if __name__ == "__main__":
    main()
