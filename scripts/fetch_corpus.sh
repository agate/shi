#!/usr/bin/env bash
# Download the source corpus (chinese-poetry/chinese-poetry, MIT) into data/raw/.
# Only the folders we use are checked out; the raw files are not committed.
set -euo pipefail
cd "$(dirname "$0")/.."
RAW=data/raw/chinese-poetry
if [ ! -d "$RAW/.git" ]; then
  git clone --depth 1 --filter=blob:none --sparse https://github.com/chinese-poetry/chinese-poetry.git "$RAW"
fi
git -C "$RAW" sparse-checkout set --no-cone \
  '/全唐诗/poet.tang.*.json' '/全唐诗/authors.tang.json' '/全唐诗/唐诗三百首.json' \
  '/宋词/ci.song.*.json' '/宋词/author.song.json' '/宋词/宋词三百首.json' \
  '/蒙学/tangshisanbaishou.json' '/蒙学/qianjiashi.json' \
  '/rank/poet/poet.tang.rank.*.json' '/rank/ci/ci.song.rank.*.json' '/rank/README.md' \
  '/LICENSE'
git -C "$RAW" rev-parse HEAD > data/raw/chinese-poetry.rev
echo "corpus at $(cat data/raw/chinese-poetry.rev)"
