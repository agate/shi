# 诗 · shi

Close readings of the best-known Tang poems and Song lyrics, for readers of any age, phone first.
Every character has its pinyin; every hard word has a note; each poem has a line-by-line translation,
its background, a note on the poet and a note on its mood (意境). Everything is in English and Chinese.

唐诗宋词精读，适合所有年龄的人，优先照顾手机。每个字有拼音，每个难词有注释，每首诗有逐句翻译、创作背景、
作者介绍和意境赏析，中英文都有。

Lives at https://honghao.me/shi/ (a GitHub Pages project page under honghao.me).

## How it is made

```
scripts/fetch_corpus.sh      download the chinese-poetry corpus (MIT) into data/raw/   (not committed)
scripts/build_db.py          every Tang shi and Song ci -> data/build/corpus.sqlite    (not committed)
scripts/select_top.py        score fame, pick the top 100 of each -> data/catalog/ranking.json
scripts/prepare_batches.py   split the 200 into writing batches with a pinyin baseline
  (writers)                  one close reading per poem -> data/poems/<id>.json, see docs/poem-schema.md
scripts/validate_poems.py    check every close reading against the schema
scripts/build_calendar.py    solar terms, festivals, lunar months 2026–2036 -> site/data/calendar.json
scripts/build_site.py        the static site -> site/, and docs/pending.md
```

For poems not yet written, `scripts/prepare_batches.py --rest` makes writing batches;
`docs/writer-prompt.md` is the brief each writer follows.

Run it all:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
scripts/fetch_corpus.sh
.venv/bin/python scripts/build_db.py
.venv/bin/python scripts/select_top.py
.venv/bin/python scripts/build_calendar.py
.venv/bin/python scripts/validate_poems.py
.venv/bin/python scripts/build_site.py
```

`site/` is committed; pushing it to `main` deploys it (`.github/workflows/site.yml`).

### Picking the best known

`scripts/select_top.py` scores all 78,000 poems on six dimensions: taught in school textbooks, in
《唐诗三百首》 or 《宋词三百首》, in 《千家诗》, widely quoted, search-engine hit counts, and how well
known the poet is. The textbook and widely-quoted lists (`data/curation/`) were compiled by Claude
from general knowledge and should be reviewed. Manual adjustments are in
`data/curation/overrides.json`, each with its reason.

### Close readings

Written by Claude from the corpus text and a machine pinyin baseline, following
`docs/poem-schema.md`: the commonly taught text and readings, plain words, nothing invented. A
reading with any open question goes in its `uncertain` list and stays off the site until someone
settles it; `docs/pending.md` lists them.

Titles and poet names have no close reading, so their pinyin (URLs, sorting, search) comes from
pypinyin. Its wrong guesses on polyphonic characters, such as 鹿柴 (zhài) or 刘长卿 (cháng), are fixed
in `data/curation/pinyin.json`, each with its reason.

### Fonts

The poem text can be shown in nine fonts (reader's choice, default 汇文明朝体), served from jsDelivr
via the 中文网字计划 packages (`@chinese-fonts/*`, MIT packaging) and `@xiao-xue-seng/tw-kai-aligned`
(OFL-1.1). Each font's own license is listed at https://chinese-font.netlify.app; check it before
any commercial use.

## Later

- Images and short films for each poem (paused for version 1).
- Yuan qu: see `docs/adding-yuanqu.md`.
- More poems beyond the 743-poem catalog (the database already holds all 78,000).
