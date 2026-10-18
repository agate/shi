"""Split the selected 200 poems into batches for close-reading generation.

Each batch file holds, per poem, the corpus text and a machine pinyin baseline
with every polyphonic character flagged, so the writer only has to confirm or
correct readings. Writes data/build/batches/batch-NN.json.
"""

import json
import os
import re
import sqlite3

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
    with open(RANKING, encoding="utf-8") as f:
        ranking = json.load(f)
    db = sqlite3.connect(DB)
    poems = []
    for kind in ("shi", "ci"):
        for s in ranking[kind]:
            if not s["selected"]:
                continue
            title, author, text = db.execute(
                "SELECT title, author, text FROM poems WHERE id=?", (s["id"],)).fetchone()
            poems.append({
                "id": s["id"], "kind": kind, "rank": s["rank"], "author": author,
                "corpus_title": title, "corpus_text": text, "lists": s["lists"],
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
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    for i, b in enumerate(batches, 1):
        with open(os.path.join(OUT, f"batch-{i:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(b["poems"], f, ensure_ascii=False, indent=1)
        print(f"batch-{i:02d}: {len(b['poems']):3} poems, {b['chars']:4} chars")


if __name__ == "__main__":
    main()
