# Archiving The Dictionary of Lahu

This folder contains code and data that 
converts James A. Matisoff's *The Dictionary of Lahu* (1988)
from its original WordStar/CP-M source files (custom 8-bit phonetic
font, single-byte encoding, bare-CR line endings) into:

* modern Unicode plain text files;
* a marked-down version, using Unicode, in "Lexware format";
* two XML files which contain all the dictionary entries, one in an ad hoc XML
  schema and one using the TEI Lex-0 schema.

The first two sets of files retain the original organization of the
dictionary in 135 files. There are also 4 files which combine the
135 segments into single, concatenated files in
proper dictionary order.

Lexware is an early markdown format developed by Bob Hsu. It pre-dates
the Shoebox/MDF-style markdown, which closely resembles Lexware.

The original files were rescued in the early 90's by John B. Lowe, who
copied the 5.25" floppy disks used by the Osborne "luggable" which
supported this early machine-readable dictionary project.

The most recent use of these files was to create a derivative work, the
English-Lahu Lexicon (Matisoff 2006).

But the utility of having a complete, modern version of the dictionary,
in a archivable representation (e.g. XML and Unicode) is obvious.

This effort to bring the dictionary into the 21st century entailed
revising two Perl tools from the original project (both
kept for reference and empirical cross-checking): `STEDT5-U4Map-7.plx`
(STEDT-font -> Unicode 4.0 remapping) and `LahuParse.pl` (WordStar ->
Lexware parsing), and eventually a third, `Lex2XML.pl` (Lexware -> XML), added
recently to aid the process of rendering XML.
Each has a from-scratch Python port; none of the three ports
needs anything besides the Python standard library.

## Directory layout

Only the source material and the code needed
to regenerate the various modern versions are included here; every derived file is
reproducible and gitignored (see `.gitignore`). Three top-level folders:

  * **`originals/`** -- unconverted source material, exactly as
    salvaged/received: the `.doc`/`.docx` files, `Ken Whistler letter re
    Lahu.txt`, and the `DL*` directories of raw WordStar/Lexware files
    (`DLOtherFiles/`, `DLWordStarFiles/{ReadMe.txt,base/,lh/}`,
    `DLLexwareFiles/`). Also holds `originals/src/`, the three legacy
    Perl/`.plx` scripts this pipeline reimplements
    (`STEDT5-U4Map-7.plx`, `LahuParse.pl`, `Lex2XML.pl`), kept for
    reference and for empirically cross-checking the Python ports.
    Nothing in `originals/` is ever written to by any script.
  * **`generated/`** -- every intermediate and final pipeline output:
    the per-file plaintext/Lexware conversions, the concatenated
    `lahudico-*` master files, the TEI Lex-0 XML, and the rendered
    HTML/LaTeX/PDF (in `generated/latex/`). Entirely gitignored --
    regenerate it by running the pipeline below rather than restoring
    it from history.
  * **`src/`** (top level) -- all of our own code: the Python ports,
    the XSLT stylesheets, and the one-off table-derivation/ordering/
    concatenation helpers. Also holds `file-order.csv/.ods/.txt/.xlsx`
    -- these look like generated output (and are produced by
    `order_files.py`) but are treated as checked-in script parameters
    here, since `concat_master.sh` reads `file-order.txt` as an input
    on every run and the ordering is expensive to recompute from
    scratch-adjacent reasoning, not just data. Also holds
    `lahu-tei-lex0.xml`, a hand-written annotated TEI reference doc
    (not used at runtime by any script, just documentation kept next
    to the code it documents).

The READMEs live at the project root, alongside these three folders.

Scripts that take a "project root" argument expect this top-level
folder (the parent of `originals/`, `generated/`, and `src/`), not
`src/` itself -- see each script's own `Usage:` docstring, and the
invocation examples below.

## Pipeline overview

```
originals/DLOtherFiles/*  (20 front/back-matter files, incl. HEADER)
originals/DLWordStarFiles/base/BASE.*  (135 body files)
        |
        |  src/dl_convert.py   (WordStar -> Unicode, from scratch)
        v
generated/DLOtherFiles-plaintext/*.txt          (front/back matter, plain text)
generated/DLWordStarFiles/base-plaintext/*.txt  (body, plain text)
generated/DLWordStarFiles/base-lexware/lex.*.txt  (body, Lexware/MDF bands)
generated/DLWordStarFiles/base-lexware/LOG.*.txt  (per-file parse-warning logs)
        |
        |  src/order_files.py  (figure out correct collation order)
        v
src/file-order.csv / file-order.xlsx / file-order.txt
        |
        |  src/concat_master.sh  (concatenate in that order)
        v
generated/lahudico-plaintext.txt   (whole dictionary, plain text, in order)
generated/lahudico-lexware.txt     (whole dictionary, Lexware bands, in order)
        |
        |  src/lex2xml.py  (Lexware -> XML, from scratch)
        v
generated/lahudico-lexware.xml     (whole dictionary, XML)
        |
        |  src/lahu-to-tei.xsl  (our ad hoc XML -> TEI Lex-0)
        v
generated/tei/lahu.xml              (TEI Lex-0 digital edition)
        |
        +-- src/lahu-html.xsl  --> generated/latex/lahu.html
        +-- src/lahu-latex.xsl --> generated/latex/lahu.tex --xelatex--> generated/latex/lahu.pdf
```

Run from the project root (the folder containing `originals/`,
`generated/`, and `src/`). The whole pipeline is wrapped in one script,
`src/regenerate-all-files.sh`, which runs all eight steps below in
order and stops on the first error:

```
src/regenerate-all-files.sh .
```

Or run the steps individually (useful if you only need to re-run part
of the pipeline, e.g. after editing just the render stylesheets):

```
python3 src/dl_convert.py .
python3 src/order_files.py .
src/concat_master.sh .
python3 src/lex2xml.py generated/lahudico-lexware.txt generated/lahudico-lexware.xml generated/lex2xml-report.log Lahu
python3 src/render_tei.py --tei generated/lahudico-lexware.xml --xsl src/lahu-to-tei.xsl --out generated/tei/lahu.xml
python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-html.xsl --out generated/latex/lahu.html
python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-latex.xsl --out generated/latex/lahu.tex
xelatex -interaction nonstopmode -output-directory=generated/latex generated/latex/lahu.tex   # twice, for page refs
```

See **README-tei.md** for the TEI transduction and HTML/PDF rendering
in detail (band-to-TEI mapping table, font notes, known
simplifications). If the two `xelatex` steps blow up into a log
hundreds of megabytes long full of `Missing character ... nullfont`
warnings, that's a missing-font problem, not a pipeline bug -- see
README-tei.md's "If your compile log explodes into millions of lines".

A second, independent path cross-checks the above against the *actual*
1994 LahuParse.pl output:

```
originals/DLLexwareFiles/lex.LH-*.TXE   (135 authentic 1994 Lexware files,
                                          still in STEDT-font byte encoding)
        |
        |  src/stedt_convert.py  (STEDT font -> Unicode, ported from
        |                        STEDT5-U4Map-7.plx directly, no
        |                        re-parsing)
        v
generated/DLLexwareFiles-plaintext/lex.LH-*.TXE.txt
```

```
python3 src/stedt_convert.py originals/src/STEDT5-U4Map-7.plx originals/DLLexwareFiles generated/DLLexwareFiles-plaintext
```

## The scripts

(All paths below are relative to `src/`, where our code lives; the two
legacy Perl scripts and the STEDT table live in `originals/src/`
instead -- see "Directory layout" above.)

**`regenerate-all-files.sh`** -- runs the whole pipeline end to end
(all eight steps below, in order, stopping on the first error): the
one command in "Run from the project root" above. Takes the same
optional project-root argument as `dl_convert.py`/`order_files.py`/
`concat_master.sh` (defaults to the parent of `src/`).

**`dl_convert.py`** -- the main conversion engine. Reworks WordStar's
"alternate font" escape convention (bytes 0x17/0x11, or 0x01/0x0E in
some front matter) plus a battery of other WordStar/CP-M artifacts
(8th-bit word-boundary marking during justification, trailing
Ctrl-Z padding, sub/superscript toggles, backspace-diacritic
composition, bold/underline/italic toggles) directly into a Unicode
output stream, using a DL-ASCII -> Unicode table built by
`build_tables.py`. It produces two kinds of output from the same
underlying per-line pipeline:

  * **Plain text**: WordStar dot-commands stripped, layout rendered
    conventionally.
  * **Lexware**: a from-scratch Python port of `LahuParse.pl`'s
    dictionary-entry classifier, tagging each logical line with a
    band name (`hw`/`..hw` for headword/sub-headword, `pos`, `gl`,
    `ex`, `no`, `bz`, `ld`, `xx`, `err` -- see below). A blank line
    precedes every new top-level article. Sub-headword bands are
    named by dot-count (`..hw`, `...hw`, ...) rather than the
    original `..shw`, so nesting depth reads directly off the band
    name.

The one genuinely tricky part of the whole port: the STEDT/DL-ASCII
source stores a diacritic keystroke *before* the base character it
modifies (an artifact of the original "type base, backspace, type
diacritic" CP/M keystroke sequence), while Unicode combining marks
must follow the base character. `dl_convert.py`'s table-driven
substitution handles this directly by mapping each DL-ASCII diacritic
code to its already-composed (or correctly-ordered combining)
Unicode form, rather than doing a separate reorder pass.

**Content-preservation / `err` band**: every parseable line's content
makes it into the Lexware output even when the classifier can't
confidently identify what kind of line it is. When a warning would
previously have only gone to the LOG file (e.g. "could not extract
headword," "no part of speech," "could not extract gloss," or a wholly
unrecognized line), the same diagnostic message is now *also* written
inline as an `err` band immediately at that point in the output,
right next to whatever content band (usually `xx`, the catch-all raw
content) accompanies it. Nothing that reaches the parser is silently
dropped. One bug in the original port (a sub-headword extraction
failure path that discarded the line's content outright) was fixed
as part of this.

**`build_tables.py`** -- derives the `LAHU_UNICODE` DL-ASCII -> Unicode
table used by `dl_convert.py`, by parsing both original Perl scripts'
own character tables (STEDT5-U4Map-7.plx's `__DATA__` block and
LahuParse.pl's `%stedt_char` table) and composing them into a single
NFC-normalized Unicode string per DL-ASCII code. Defaults to reading
those two files from `originals/src/`.

**`lahu_collate.py`** -- the Lahu collation sort key. Parses a headword
into consonant + vowel + tone and produces a sort key following the
dictionary's own authoritative collation order (confirmed against the
collation line decoded from `originals/DLOtherFiles/HEADER`'s footer,
with a single-glottal-stop reading for the two checked tones where the
source had an apparent doubled-glottal-stop typo):

```
a á â à ā âʔ àʔ | a i u e o ɛ ɔ ɨ ə | q qh k kh g ŋ c ch j t th d n p ph b m h g̈ š y f v l
```

**`order_files.py`** -- reads every file's Lexware output, extracts its
top-level headwords, and sorts the 135 body files by collation key
(walking past any leading non-syllabic headwords -- bare consonants or
onomatopoeia with no vowel, which can't carry a collation key -- to
find the first entry that classifies the file). Writes
`src/file-order.csv` (full detail: initial, first/last headword, entry
count, filenames) and `src/file-order.txt` (just the ordered
filenames, for the concatenation script).

There are 135 body files but only 105 distinct (consonant+vowel)
initials -- 20 initials are split across 2-8 files each (the heaviest,
vowel-initial *ɔ*, spans 8 files), which is why the file count exceeds
the initial count. `file-order.csv` shows exactly which files belong
to which split group and confirms they land consecutively and in
correct tone order after sorting.

**`concat_master.sh`** -- concatenates the 135 plaintext and Lexware
files in the order from `src/file-order.txt`, producing
`generated/lahudico-plaintext.txt` and `generated/lahudico-lexware.txt`.

**`lex2xml.py`** -- a faithful, empirically-verified Python port of
`Lex2XML.pl` (see `README-lex2xml.md` for details). Produces
`generated/lahudico-lexware.xml` from `generated/lahudico-lexware.txt`.

**`stedt_convert.py`** -- an independent port of `STEDT5-U4Map-7.plx`
itself (not `LahuParse.pl`), used only to convert the authentic 1994
`originals/DLLexwareFiles/lex.LH-*.TXE` files (already-parsed Lexware
output, but still in STEDT-font byte encoding) straight to Unicode, as
a cross-check against the from-scratch `dl_convert.py` pipeline above.
It replays the original script's 6-step, byte-level algorithm exactly
(deduplicate doubled diacritic bytes, sort "high" diacritics after
ordinary ones within a run, space-pad a bare trailing diacritic,
reorder diacritic-before-base to base-then-diacritic, remap bytes to
Unicode, then a couple of small Unicode-level cleanups for dotless-i
and free-standing modifier-letter diacritics). Output goes to
`generated/DLLexwareFiles-plaintext/`, never back into `originals/`.

**`lahu-to-tei.xsl`**, **`lahu-html.xsl`**, **`lahu-latex.xsl`**,
**`render_tei.py`** -- transduce `generated/lahudico-lexware.xml` into
standard TEI Lex-0 XML, then render that TEI as HTML and as a
print-quality PDF (via XeLaTeX). See **README-tei.md** for full detail;
this is a separate, later stage of the pipeline, so it gets its own
README rather than duplicating everything here.

## Known data-quality caveats

  * `originals/DLOtherFiles/HEADER` is mostly WordStar dot-commands and
    CP/M binary padding; its converted plain-text output is expected to
    look mostly like noise, apart from the collation-sequence line
    used to derive the sort order above. It's included in the
    conversion (rather than skipped like the four true binary/font
    resource files, `LAHU.CHR`, `LQLAHU.D1%`, `LQLAHUBD.H1%`,
    `LQLAHUEL.H1%`) because it's the only place the authoritative
    collation sequence is recorded.
  * `generated/conversion-report.log` tallies every stripped or
    unrecognized control byte across all 155 converted files
    (front/back matter + body). The great majority are WordStar
    subscript/superscript toggles and other formatting bytes that
    carry no textual content once stripped.
  * Real parsing ambiguity in the source shows up as `err` bands in
    the Lexware output (1,783 across the whole dictionary as of the
    current classifier) -- mostly lines the classifier couldn't
    confidently type (long example/gloss continuations wrapped across
    lines, stray formatting artifacts, and a handful of leftover
    WordStar toggle bytes the upstream conversion didn't fully
    resolve). These are real editorial-quality flags worth reviewing,
    not silent data loss -- the raw content is always preserved
    alongside the `err` band (typically in the accompanying `xx`
    band).
  * `dl_convert.py`'s classifier recognizes one specific, very common
    shape of `err`/`xx` pair and fixes it automatically: an indented
    continuation line with no Lahu-script text of its own, immediately
    following a gloss that's still being accumulated (or, failing
    that, the most recently flushed `gl` band). This is almost always
    the tail end of a gloss or example translation that wrapped across
    more physical lines than the original classification window
    recognized. Rather than losing this into an `xx`/`err` pair, it's
    appended onto the gloss and logged as a `Merged as gloss
    continuation (...)` warning in the per-file `LOG.*.txt` instead of
    an inline error (117 lines recovered this way on the current
    data). Anything left over as `xx` after this merge is genuinely
    unclassified rather than a pipeline artifact, so the TEI/render
    stylesheets show it inline in the dictionary text (see
    README-tei.md) rather than hiding it as an editorial note --
    that's the fastest way for a human reviewer to spot and fix
    whatever's left.

## Outputs, at a glance

All generated; all gitignored (see "Directory layout" above).

| File | What |
|---|---|
| `generated/DLOtherFiles-plaintext/*.txt` | Front/back matter, Unicode plain text |
| `generated/DLWordStarFiles/base-plaintext/*.txt` | Body, Unicode plain text (per file) |
| `generated/DLWordStarFiles/base-lexware/lex.*.txt` | Body, Unicode Lexware bands (per file) |
| `generated/DLWordStarFiles/base-lexware/LOG.*.txt` | Per-file parse-warning logs |
| `src/file-order.csv` / `.xlsx` / `.txt` | Collation order of the 135 body files (checked-in parameter, not gitignored) |
| `generated/lahudico-plaintext.txt` | Whole dictionary, plain text, in order |
| `generated/lahudico-lexware.txt` | Whole dictionary, Lexware bands, in order |
| `generated/lahudico-lexware.xml` | Whole dictionary, XML |
| `generated/conversion-report.log` | Aggregate stripped/unknown-character tally |
| `generated/lex2xml-report.log` | XML tag-frequency statistics |
| `generated/DLLexwareFiles-plaintext/lex.LH-*.TXE.txt` | Authentic 1994 Lexware output, Unicode (cross-check) |
| `src/lahu-tei-lex0.xml` | Annotated TEI header/entry-structure reference (checked-in, hand-written) |
| `generated/tei/lahu.xml` | TEI Lex-0 digital edition |
| `generated/latex/lahu.html` | Rendered HTML |
| `generated/latex/lahu.tex`, `generated/latex/lahu.pdf` | Rendered LaTeX source and compiled PDF |

See inline comments in each script for line-level detail,
`README-lex2xml.md` for the XML conversion specifically, and
`README-tei.md` for the TEI transduction and HTML/PDF rendering.
