# Third-party components

## python-chess / chess 1.11.2

The application uses the unmodified `chess` Python package by Niklas Fiekas
and contributors for legal chess moves, FEN handling and notation.

- Project: https://github.com/niklasf/python-chess
- Documentation: https://python-chess.readthedocs.io/
- Version: 1.11.2
- License: GNU General Public License version 3 or later; see
  `python-chess-LICENSE.txt`.
- Corresponding source: [chess-1.11.2.tar.gz](chess-1.11.2.tar.gz).
  The application source is in this repository.

## Chess puzzle positions

The legacy chess catalog retained for regression tests is a curated and independently verified subset of
the Lichess puzzle database, released under CC0-1.0:
https://database.lichess.org/#puzzles . Each record in
`raetselkalender/data/chess_positions.json` retains its original puzzle ID,
source link, rating and attribution. The source data must be interpreted after
applying the first move of the database record; that setup move is not the
player's answer.

## Stockfish

This port bundles the unmodified Stockfish 19 Lite, single-thread WebAssembly
build from the [stockfish 19.0.1 npm package](https://www.npmjs.com/package/stockfish/v/19.0.1).
It is released under the [GNU General Public License version 3](Stockfish-GPL-3.0.txt).

- Complete corresponding source and build instructions: [Stockfish.js v19.0.1](https://github.com/nmrugg/stockfish.js/tree/8d9ca57043594a8fa6ae0b73fb685d9105bf51df).
- Build command in that source checkout: `npm run build-single-lite`.
- Original engine project: [Stockfish](https://github.com/official-stockfish/Stockfish).

The former catalog preparation tool `tools/prepare_chess_catalog.py` remains
available in the desktop repository for reproducing the legacy regression data. New tasks do not select
from that catalog.

## Chess piece artwork

The twelve bundled PNG piece images are rendered from the SVGs supplied by
python-chess 1.11.2, originally by Colin M. L. Burnett. Those piece images
are triple licensed under the GFDL, BSD and GPL; they are included here under
the GPL alongside python-chess. The original SVG source is in `chess/svg.py`
in the included chess source distribution, and the conversion recipe is
`tools/render_chess_pieces.py` in the desktop repository. Documentation and attribution:
https://python-chess.readthedocs.io/en/latest/svg.html .


## Pyodide

The unmodified browser runtime files in `runtime/pyodide/` are from
[Pyodide 0.27.7](https://github.com/pyodide/pyodide/tree/0.27.7), distributed under the
[Mozilla Public License 2.0](pyodide-LICENSE.txt). The standard library bundles
[Python 3.12.7](https://github.com/python/cpython/tree/v3.12.7) under the
[Python Software Foundation License](CPython-LICENSE.txt).

## German word puzzles

The German game vocabulary in `raetselkalender/data/german_words.json` and
the bundled copy in the browser archive are adapted from the following
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) sources.

- **OdeNet**, by Melanie Siegel, Francis Bond and contributors. The build
  extracts German lemmas from the lexical entries. [Pinned source and attribution](https://github.com/hdaSprachtechnologie/odenet/tree/8ba741223048c28f67d4c38560ea4c0ee89568bb)
- **FrequencyWords**, by Hermit Dave, based on OpenSubtitles 2018. The build
  uses the German frequency list to keep attested single words. [Pinned German list](https://github.com/hermitdave/FrequencyWords/blob/525f9b560de45753a5ea01069454e72e9aa541c6/content/2018/de/de_50k.txt) · [Attribution and data license](https://github.com/hermitdave/FrequencyWords/blob/525f9b560de45753a5ea01069454e72e9aa541c6/README.md)

The derived data, including the editorial category selections for this project,
are shared under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
The build intersects the source vocabularies, normalizes case and Unicode,
filters by German letter set and length, and adds curated category words.
To reproduce the dataset, download the pinned
[OdeNet XML](https://raw.githubusercontent.com/hdaSprachtechnologie/odenet/8ba741223048c28f67d4c38560ea4c0ee89568bb/odenet_oneline.xml)
and [German frequency data](https://raw.githubusercontent.com/hermitdave/FrequencyWords/525f9b560de45753a5ea01069454e72e9aa541c6/content/2018/de/de_50k.txt),
then run `python tools/build_word_data.py odenet_oneline.xml de_50k.txt`.
