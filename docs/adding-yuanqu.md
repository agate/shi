# Adding Yuan qu (元曲) later

Version 1 covers Tang shi and Song ci only. This is how Yuan qu would join without changing
what already works.

## What Yuan qu are

Yuan qu are songs of the Yuan dynasty (1271–1368). Version 1 would take only **散曲**: short songs
sung on their own, not the plays (杂剧). A 散曲 is either a single **小令** (one short song) or a
**套数** (several songs in one key, sung in a row). Each one is written to a named tune (曲牌),
like a ci to its 词牌, and often names a mode (宫调) too, e.g. 【越调】天净沙·秋思.

## 1. Data

- **Source.** The chinese-poetry corpus already has `元曲/yuanqu.json`: 11,057 entries of the form
  `{dynasty, author, title, paragraphs}`, already in Simplified Chinese. Add `'/元曲/yuanqu.json'`
  to the sparse checkout in `scripts/fetch_corpus.sh`. It has no search-rank file, so the `search`
  dimension is empty for qu.
- **Split the title.** Titles pack mode, tune and subject together: `越调・天净沙秋思` is mode 越调,
  tune 天净沙, subject 秋思. Parse them into `mode`, `title` (the tune) and `subtitle`, using a list
  of known 曲牌 names to find where the tune ends.
- **Drop the plays.** Some entries are songs cut out of plays, e.g. `诈妮子调风月・仙吕/点绛唇`
  (play name, then mode/tune). Skip titles of that shape so only 散曲 remain.
- **Schema.** Add `'qu'` to `poems.kind` and `'yuan'` to `poems.dynasty` in `scripts/build_db.py`.
  Store the tune in `title` (as ci do), and keep the mode, if any, in a new `mode` column. Give
  ids the form `qu-<sha1[:12]>`, as `ci_id` does.

## 2. Picking the best known

`scripts/select_top.py` already scores by dimensions. For qu:

- **anthology:** add a `yuanqu300` list. There is no single standard *Yuan Qu 300*. Use
  《元曲三百首》 (任讷 / 卢前), and record which edition in a `data/curation/yuanqu300.json` note.
- **textbook:** add the qu taught in school to `data/curation/textbook.json` under a new `"yuan_qu"`
  key: 马致远《天净沙·秋思》, 张养浩《山坡羊·潼关怀古》, 关汉卿《四块玉·别情》,
  白朴《天净沙·秋》, 张可久《卖花声·怀古》 and others.
- **famous:** add a `"yuan_qu"` key to `data/curation/famous.json` as well.
- **weights:** add a `"qu"` row to `WEIGHTS`, like `"ci"` but with `search` at 0.
- Start with the top 50: there are far fewer famous qu than Tang shi or Song ci.

## 3. Close readings

`docs/poem-schema.md` already fits qu, with three additions:

- `kind: "qu"`, `dynasty: "yuan"`, and title `"曲牌·题目"`, e.g. `"天净沙·秋思"`. Put the mode in
  `form`, e.g. `{"zh": "越调·小令", "en": "short song, Yue mode"}`.
- **衬字 (padding words).** Qu add extra syllables outside the tune's fixed pattern. Mark them so the
  page can show them lighter: add `"padding": [[line, pos], ...]` to the schema and to
  `scripts/validate_poems.py`.
- **套数.** Use `stanza_breaks` for the boundary between songs, and add `"songs": [{"line": 0,
  "tune": "..."}]` to name each song's tune.

Qu are full of Yuan-era spoken words (e.g. 兀的, 则索, 恁). The writer prompt should ask for a gloss
on every one.

## 4. Site

- `scripts/build_site.py`: add `"yuan": ("Yuan", "元")` to `DYNASTY`, a third tab "元曲 / Yuan
  songs" on the home page, and `"qu"` to the kinds the pager walks. Search already covers
  every kind in the catalog.
- `site-src/app.js`: in search results, show 曲 for `k === 'qu'`.
- Daily poem: no change; qu carry the same tags.

## Size of the work

Data and site changes: about half a day. Close readings for 50 qu: about 5 writer batches,
run the same way as the Tang and Song batches.
