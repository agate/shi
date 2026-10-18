"""Build data/build/corpus.sqlite from the raw chinese-poetry corpus.

Every Tang shi (全唐诗) and every Song ci (全宋词) goes in, converted to Simplified
Chinese, with its search-engine hit counts and the anthologies / textbooks it
appears in. Run scripts/fetch_corpus.sh first.
"""

import glob
import hashlib
import json
import os
import re
import sqlite3
from collections import defaultdict

import opencc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data/raw/chinese-poetry")
OUT = os.path.join(ROOT, "data/build/corpus.sqlite")
ENGINES = ("baidu", "so360", "bing", "bing_en", "google")

t2s = opencc.OpenCC("t2s")
PUNCT = re.compile(r"[\s，。、；：？！“”‘’「」『』（）()《》〈〉·．.,;:?!\-—…□]")


def norm(s):
    """Text with punctuation and spaces removed, for matching."""
    return PUNCT.sub("", s or "")


def load(path):
    with open(os.path.join(RAW, path), encoding="utf-8") as f:
        return json.load(f)


def file_key(path):
    """Shard suffix of a corpus file: '1000' in ci.song.1000.json, '2019y' for the extra shard."""
    return re.search(r"\.(\w+)\.json$", path).group(1)


def shard_order(path):
    k = file_key(path)
    return (0, int(k)) if k.isdigit() else (1, 0)


def aligned_ranks(poems, ranks, key):
    """Pair each poem with its rank row. The rank files were made from an older
    corpus, so rows are matched by key in order instead of by position."""
    queue = defaultdict(list)
    for r in ranks:
        queue[key(r)].append(r)
    return [queue[key(p)].pop(0) if queue[key(p)] else None for p in poems]


def schema(db):
    db.executescript(
        """
        DROP TABLE IF EXISTS poems;
        DROP TABLE IF EXISTS authors;
        DROP TABLE IF EXISTS lists;
        DROP TABLE IF EXISTS poems_fts;
        CREATE TABLE poems (
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,          -- 'shi' (Tang poem) or 'ci' (Song lyric)
          dynasty TEXT NOT NULL,       -- 'tang' or 'song'
          author TEXT NOT NULL,
          title TEXT NOT NULL,         -- poem title, or the tune name (词牌) for ci
          text TEXT NOT NULL,          -- Simplified, one sentence per line
          text_trad TEXT,              -- original Traditional text (Tang only)
          chars INTEGER NOT NULL,
          baidu INTEGER, so360 INTEGER, bing INTEGER, bing_en INTEGER, google INTEGER
        );
        CREATE TABLE authors (
          name TEXT NOT NULL,
          dynasty TEXT NOT NULL,
          description TEXT,
          PRIMARY KEY (name, dynasty)
        );
        CREATE TABLE lists (           -- membership in an anthology or textbook list
          list TEXT NOT NULL,          -- tang300, song300, qianjiashi, textbook, famous
          poem_id TEXT NOT NULL REFERENCES poems(id),
          PRIMARY KEY (list, poem_id)
        );
        CREATE INDEX poems_author ON poems(author);
        CREATE VIRTUAL TABLE poems_fts USING fts5(title, author, text, content='poems', tokenize='trigram');
        """
    )


def insert_tang(db):
    rows = []
    for path in sorted(glob.glob(os.path.join(RAW, "全唐诗/poet.tang.*.json")), key=shard_order):
        poems = load(path)
        ranks = load(f"rank/poet/poet.tang.rank.{file_key(path)}.json")
        for p, r in zip(poems, aligned_ranks(poems, ranks, lambda x: (x["author"], x["title"]))):
            text = "\n".join(t2s.convert(s) for s in p["paragraphs"])
            rows.append(
                (p["id"], "shi", "tang", t2s.convert(p["author"]), t2s.convert(p["title"]), text,
                 "\n".join(p["paragraphs"]), len(norm(text)), *[(r or {}).get(e) for e in ENGINES])
            )
    db.executemany("INSERT INTO poems VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def ci_id(p):
    return "ci-" + hashlib.sha1((p["author"] + p["rhythmic"] + "".join(p["paragraphs"])).encode()).hexdigest()[:12]


def insert_ci(db):
    rows, seen = [], set()
    for path in sorted(glob.glob(os.path.join(RAW, "宋词/ci.song.*.json")), key=shard_order):
        poems = load(path)
        rank_path = f"rank/ci/ci.song.rank.{file_key(path)}.json"
        ranks = load(rank_path) if os.path.exists(os.path.join(RAW, rank_path)) else []
        for p, r in zip(poems, aligned_ranks(poems, ranks, lambda x: (x["author"], x["rhythmic"]))):
            pid = ci_id(p)
            if pid in seen:
                continue
            seen.add(pid)
            text = "\n".join(t2s.convert(s) for s in p["paragraphs"])
            rows.append(
                (pid, "ci", "song", t2s.convert(p["author"]), t2s.convert(p["rhythmic"]), text, None,
                 len(norm(text)), *[(r or {}).get(e) for e in ENGINES])
            )
    db.executemany("INSERT INTO poems VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def insert_supplements(db):
    with open(os.path.join(ROOT, "data/curation/supplements.json"), encoding="utf-8") as f:
        sup = json.load(f)["poems"]
    db.executemany("INSERT INTO poems VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   [(p["id"], p["kind"], p["dynasty"], p["author"], p["title"], p["text"], None,
                     len(norm(p["text"])), *[None] * len(ENGINES)) for p in sup])
    return len(sup)


def insert_authors(db):
    for a in load("全唐诗/authors.tang.json"):
        db.execute("INSERT OR IGNORE INTO authors VALUES (?,?,?)",
                   (t2s.convert(a["name"]), "tang", t2s.convert(a.get("desc") or "")))
    for a in load("宋词/author.song.json"):
        db.execute("INSERT OR IGNORE INTO authors VALUES (?,?,?)", (a["name"], "song", a.get("description") or ""))


class Matcher:
    """Finds a corpus poem from author + title and/or first line."""

    def __init__(self, db, kind):
        self.by_author = defaultdict(list)
        for pid, author, title, text in db.execute("SELECT id, author, title, text FROM poems WHERE kind=?", (kind,)):
            self.by_author[author].append((pid, norm(title), norm(text)))

    def find(self, author, title=None, first=None):
        """Best match by first line (allowing a character or two of variant text),
        then by exact first line under any author. Falls back to title only when
        no first line is given, because tune names and generic titles repeat."""
        t, f = norm(title), norm(first)
        if f:
            def score(c):
                # A matching title lets a more divergent variant text through.
                return similar(f, c[2]) + (0.2 if t and (t in c[1] or c[1] in t) else 0)

            best = max(((score(c), c) for c in self.by_author.get(author, [])), default=(0, None),
                       key=lambda x: x[0])
            if best[0] >= 0.75:
                return best[1][0]
            if len(f) >= 5:
                hits = [c for cs in self.by_author.values() for c in cs if c[2].startswith(f)]
                if len(hits) == 1:
                    return hits[0][0]
            return None
        hits = [c for c in self.by_author.get(author, []) if c[1] == t] or \
               [c for c in self.by_author.get(author, []) if c[1].startswith(t)]
        return hits[0][0] if hits else None


def similar(first, text):
    """Share of positions where the first line and the start of the text agree."""
    head = text[: len(first)]
    return sum(a == b for a, b in zip(first, head)) / len(first)


def add_list(db, name, ids):
    db.executemany("INSERT OR IGNORE INTO lists VALUES (?,?)", [(name, i) for i in ids if i])


def insert_lists(db):
    report = {}
    tang, ci = Matcher(db, "shi"), Matcher(db, "ci")
    known = {r[0] for r in db.execute("SELECT id FROM poems WHERE kind='shi'")}

    t300 = load("全唐诗/唐诗三百首.json")
    ids = [p["id"] if p["id"] in known else
           tang.find(t2s.convert(p["author"]), t2s.convert(p["title"]), t2s.convert(p["paragraphs"][0]))
           for p in t300]
    add_list(db, "tang300", ids)
    report["tang300"] = (len(t300), sum(1 for i in ids if i))

    s300 = load("宋词/宋词三百首.json")
    ids = [ci.find(p["author"], p["rhythmic"], p["paragraphs"][0]) for p in s300]
    add_list(db, "song300", ids)
    report["song300"] = (len(s300), sum(1 for i in ids if i))

    qjs = []
    for sec in load("蒙学/qianjiashi.json")["content"]:
        for p in sec["content"]:
            if "（唐）" not in p["author"]:
                continue
            # Multi-part poems nest each part (其一, 其二) as {"subchapter", "paragraphs"}.
            parts = p["paragraphs"] if isinstance(p["paragraphs"][0], dict) else [p]
            qjs += [{**p, "paragraphs": part["paragraphs"]} for part in parts]
    ids = [tang.find(t2s.convert(p["author"].replace("（唐）", "")), t2s.convert(p["chapter"]),
                     t2s.convert(p["paragraphs"][0])) for p in qjs]
    add_list(db, "qianjiashi", ids)
    report["qianjiashi"] = (len(qjs), sum(1 for i in ids if i))

    for name in ("textbook", "famous"):
        with open(os.path.join(ROOT, f"data/curation/{name}.json"), encoding="utf-8") as f:
            cur = json.load(f)
        misses = []
        for kind, matcher in (("tang", tang), ("song_ci", ci)):
            for author, title, first in cur[kind]:
                pid = matcher.find(author, title, first)
                if pid:
                    add_list(db, name, [pid])
                else:
                    misses.append(f"{author}《{title}》{first}")
        total = len(cur["tang"]) + len(cur["song_ci"])
        report[name] = (total, total - len(misses))
        report[name + "_misses"] = misses
    return report


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)
    db = sqlite3.connect(OUT)
    schema(db)
    n_tang, n_ci = insert_tang(db), insert_ci(db)
    n_sup = insert_supplements(db)
    insert_authors(db)
    report = insert_lists(db)
    db.execute("INSERT INTO poems_fts(poems_fts) VALUES ('rebuild')")
    db.commit()
    print(f"tang shi: {n_tang}  song ci: {n_ci}  supplements: {n_sup}")
    for k, v in report.items():
        print(k, v)


if __name__ == "__main__":
    main()
