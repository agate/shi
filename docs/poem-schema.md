# Close-reading file format (`data/poems/<id>.json`)

One JSON file per poem, named by the corpus id. `scripts/validate_poems.py` checks every rule
below; the site build refuses files that fail it.

```jsonc
{
  "id": "…",                      // corpus id, same as the file name
  "kind": "shi",                  // "shi" (Tang poem) or "ci" (Song lyric)
  "title": "静夜思",               // the commonly taught title. Ci: "词牌·题目或首句", e.g. "水调歌头·明月几时有"
  "title_en": "Quiet Night Thoughts",
  "author": "李白",
  "author_en": "Li Bai",
  "dynasty": "tang",              // "tang" or "song"
  "form": {"zh": "五言绝句", "en": "five-character quatrain"},

  // The commonly taught text (统编版 textbooks / 通行本), one sentence (句) per line,
  // no punctuation. Every character is [char, pinyin with tone mark].
  "lines": [[["床", "chuáng"], ["前", "qián"], ["明", "míng"], ["月", "yuè"], ["光", "guāng"]], …],
  "stanza_breaks": [],            // ci: index of the first line of each later stanza (下阕), e.g. [4]

  // When the taught text differs from the corpus text (data/build/corpus.sqlite).
  "text_note": {"zh": "…", "en": "…"},          // or null

  // Characters whose reading here is not their most common one, or is debated.
  "readings": [
    {"line": 0, "pos": 6, "char": "斜", "pinyin": "xié",
     "zh": "现在课本读 xié。古音读 xiá，和“家、花”押韵。", "en": "…"}
  ],

  // Words worth explaining. line/start/end index into "lines" (end exclusive).
  "glosses": [
    {"line": 1, "start": 0, "end": 2, "zh": "疑是：好像是。", "en": "疑是: seemed to be."}
  ],

  // Plain modern rendering, one entry per line of "lines".
  "translation": [{"zh": "…", "en": "…"}, …],

  "background": {"zh": "…", "en": "…"},     // when, where and why it was written
  "author_note": {"zh": "…", "en": "…"},    // who the poet was, as it bears on this poem
  "appreciation": {"zh": "…", "en": "…"},   // the mood (意境): what to picture and feel
  "famous_lines": [2, 3],                  // indexes of the best-known lines, may be empty

  // For the daily poem. Use only values from these lists.
  "tags": {
    "seasons": ["autumn"],                 // spring summer autumn winter
    "festivals": [],                       // spring-festival lantern qingming duanwu qixi midautumn chongyang new-year-eve hanshi
    "solar_terms": [],                     // lichun yushui jingzhe chunfen qingming guyu lixia xiaoman mangzhong xiazhi xiaoshu dashu liqiu chushu bailu qiufen hanlu shuangjiang lidong xiaoxue daxue dongzhi xiaohan dahan
    "themes": ["homesick", "moon"]          // free, lowercase English words
  },

  // Anything you are not sure is true. A non-empty list keeps the poem out of the site.
  "uncertain": [{"field": "background", "zh": "…", "en": "…"}]
}
```

## Writing rules

- **Readers:** anyone from a ten-year-old to a grown-up. Short sentences, everyday words. Explain
  what a thing is before naming it. Facts must stay right.
- **Both languages say the same thing.** Never mix languages in one string. English strings use
  pinyin for names (Li Bai, Chang'an) and may add the Chinese in no other way.
- **Lengths:** background 80–200 Chinese characters, author_note 60–150, appreciation 120–300;
  English roughly the same content. Long poems may run longer.
- **Pinyin:** standard Mandarin as taught in current mainland textbooks, tone marks (ā á ǎ à, ü),
  lowercase. Put old rhyme readings (叶音) and other debated readings in `readings`, with the
  taught reading in `lines`.
- **Truth:** do not invent dates, places, people or stories. If sources disagree or you do not
  know, say so in the text ("一说……") or put it in `uncertain`. Attribution disputes go in
  `background` and, if they matter, in `uncertain`.
