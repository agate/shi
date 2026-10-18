"""Split poems into batches for close-reading generation.

Default: the selected top 200. With --rest: every catalog poem
(data/catalog/catalog.json, written by build_site.py) that has no close reading yet.

Each batch file holds, per poem, the corpus text and a machine pinyin baseline
with every polyphonic character flagged, so the writer only has to confirm or
correct readings. Writes data/build/batches/batch-NN.json (batch-rNN.json with --rest).
"""

import json
import os
import re
import sqlite3
import sys

from pypinyin import Style, pinyin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data/build/corpus.sqlite")
RANKING = os.path.join(ROOT, "data/catalog/ranking.json")
OUT = os.path.join(ROOT, "data/build/batches")
BATCH_CHARS = 900  # poem characters per batch; long poems get a batch to themselves
BATCH_POEMS = 10  # short poems still need full notes, so cap the count too

HAN = re.compile(r"[㐀-鿿\U00020000-\U0002ffff]")


def baseline(text):
    """[[char, reading, [other readings]], ...] per sentence, punctuation dropped."""
    out = []
    for sent in re.split(r"[，。？！；：\n]", text):
        chars = [c for c in sent if HAN.match(c)]
        if not chars:
            continue
        joined = "".join(chars)
        readings = [r[0] for r in pinyin(joined, style=Style.TONE)]
        line = []
        for c, r in zip(chars, readings):
            alts = [x for x in pinyin(c, style=Style.TONE, heteronym=True)[0] if x != r]
            line.append([c, r, alts] if alts else [c, r])
        out.append(line)
    return out


def main():
    rest = "--rest" in sys.argv
    db = sqlite3.connect(DB)
    lists = {}
    for name, pid in db.execute("SELECT list, poem_id FROM lists"):
        lists.setdefault(pid, []).append(name)
    if rest:
        with open(os.path.join(ROOT, "data/catalog/catalog.json"), encoding="utf-8") as f:
            todo = [(c["id"], c["kind"], None) for c in json.load(f)
                    if not os.path.exists(os.path.join(ROOT, f'data/poems/{c["id"]}.json'))]
    else:
        with open(RANKING, encoding="utf-8") as f:
            ranking = json.load(f)
        todo = [(s["id"], kind, s["rank"]) for kind in ("shi", "ci") for s in ranking[kind] if s["selected"]]
    poems = []
    for pid, kind, rank in todo:
        title, author, text = db.execute("SELECT title, author, text FROM poems WHERE id=?", (pid,)).fetchone()
        poems.append({
            "id": pid, "kind": kind, "rank": rank, "author": author,
            "corpus_title": title, "corpus_text": text, "lists": sorted(lists.get(pid, [])),
            "baseline_pinyin": baseline(text),
        })
    # Pack poems into batches by size, longest first.
    poems.sort(key=lambda p: -len(p["corpus_text"]))
    batches = []
    for p in poems:
        size = len(p["corpus_text"])
        for b in batches:
            if b["chars"] + size <= BATCH_CHARS and len(b["poems"]) < BATCH_POEMS:
                b["poems"].append(p)
                b["chars"] += size
                break
        else:
            batches.append({"chars": size, "poems": [p]})
    os.makedirs(OUT, exist_ok=True)
    prefix = "batch-r" if rest else "batch-"
    for f in os.listdir(OUT):
        if f.startswith(prefix) and (rest or not f.startswith("batch-r")):
            os.remove(os.path.join(OUT, f))
    for i, b in enumerate(batches, 1):
        with open(os.path.join(OUT, f"{prefix}{i:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(b["poems"], f, ensure_ascii=False, indent=1)
        print(f"{prefix}{i:02d}: {len(b['poems']):3} poems, {b['chars']:4} chars")


if __name__ == "__main__":
    main()
