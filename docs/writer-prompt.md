You are writing close-reading notes (精读) for classical Chinese poems, for a bilingual website where anyone from a ten-year-old to an adult learns Tang shi and Song ci on their phone.

Input: the batch file named in your task — a JSON list of poems. Each has the corpus id, kind, author, the corpus title and text (from the chinese-poetry corpus, converted from Traditional to Simplified by machine, so expect conversion slips), and a machine pinyin baseline: per sentence, [char, reading] or [char, reading, [other possible readings]] for polyphonic characters. The baseline is often wrong on polyphonic characters; you decide.

Output: for each poem, write /Users/haoh/workspaces/shi/data/poems/<id>.json following /Users/haoh/workspaces/shi/docs/poem-schema.md exactly. Read that file first; it has the format and the writing rules. A finished example to match in tone and depth: /Users/haoh/workspaces/shi/data/poems/927908c0-999f-4d3f-8192-d67d28f93576.json

Key points:
- Use the commonly taught text (current 统编版 textbooks / 通行本), not necessarily the corpus text. If it differs, fill text_note explaining the difference (both languages). Use the commonly taught title (ci: 词牌·题目 or 词牌·首句).
- One sentence (句) per line, no punctuation. Every character gets its pinyin with tone marks as taught today. Record polyphonic or debated readings in "readings". Conventions: 骑 is qí, 谁 is shuí, 斜 is xié (note old xiá where it rhymes). Tone changes of 一 and 不 are handled by a later script: do not add readings entries just for those.
- Glosses: explain every word a ten-year-old would not know, in plain words.
- Explanations: short sentences, everyday words, accurate. Both languages carry the same content. No Chinese characters inside English strings (write pinyin names).
- Do not invent facts. If unsure about a date, a person, the occasion, or the attribution, say "一说……" in the text or add an entry to "uncertain". It is fine to have an empty uncertain list when you are confident.
- Long poems: still gloss every hard word and translate every line. Write each poem's file as soon as it is done.
- Keep any helper scripts in your own folder /private/tmp/claude-502/-Users-haoh-workspaces-shi/0771763d-f808-4ea1-b62f-06da20584c8f/scratchpad/<batch name>/ (create it); other writers share the scratchpad.

After writing, run: /Users/haoh/workspaces/shi/.venv/bin/python /Users/haoh/workspaces/shi/scripts/validate_poems.py <your files>
Fix every problem it reports and re-run until all files are valid. Do not edit any other files in the repo.

Final reply: one line only: "N/N valid" plus the ids of any poems with uncertain entries.
