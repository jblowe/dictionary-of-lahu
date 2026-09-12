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
    to the code it documents). `src/latex/` holds the hand-authored
    PDF scaffold -- `lahu-master.tex` (documentclass, packages, entry
    macros, running head/footer), `title.tex` (title page), `toc.tex`
    (table of contents) -- which `\input`s the generated dictionary
    body; see README-tei.md's "Rendering: PDF".

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
        +-- src/lahu-latex.xsl --> generated/latex/lahu.tex  (dictionary body only)
                                        |
originals/DLOtherFiles/ --------------+
        |                              |
        |  src/process_front_and_back_matter.py                |
        v  (dedication, plates list, acknowledgments,           |
generated/latex/frontmatter*.tex,      symbols/abbreviations,   |
generated/latex/backmatter.tex         bibliography, appendices)|
        |                              |                        |
        +------------------------------+------------------------+
                                        |
                                        |  \input from src/latex/lahu-master.tex
                                        v  (title page, TOC, front/back matter,
                                            preamble) --xelatex-->
                                   generated/latex/lahu.pdf
```

Run from the project root (the folder containing `originals/`,
`generated/`, and `src/`). The whole pipeline is wrapped in one script,
`src/regenerate-all-files.sh`, which runs all nine steps below in
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
python3 src/process_front_and_back_matter.py .
xelatex -interaction nonstopmode -output-directory=generated/latex -jobname=lahu src/latex/lahu-master.tex   # twice, for TOC/page refs
```

The last step compiles `src/latex/lahu-master.tex` (a hand-authored
scaffold: title page, table of contents, front/back matter, preamble),
which `\input`s `generated/latex/lahu.tex` and the generated
`generated/latex/frontmatter*.tex`/`backmatter.tex` -- not those
generated files directly.

**Front/back matter** (dedication, list of plates, acknowledgments,
symbols and abbreviations, an Introduction outline with one recovered
subsection, bibliography, and two unassigned back-matter appendices) is
recovered from `originals/DLOtherFiles/` by
`src/process_front_and_back_matter.py`, a separate script from
`dl_convert.py` by design (it reuses a few of that script's byte-level
conversion functions but does its own document-level layout rendering,
which doesn't belong in the core WordStar-conversion script). The order
follows the book's own printed Table of Contents, transcribed almost
verbatim in `originals/DLOtherFiles/CONTENTS.TXE` -- see
`src/front-back-matter-order.csv` for the full section-by-section order
(one row per section, including the nine Introduction subsections with
no surviving file) and that script's module docstring for exactly which
of the ~20 files in `originals/DLOtherFiles/` are included and why
(several are excluded as superseded drafts, internal production notes,
or binary printer/font resources -- also see README-tei.md). Front
matter is roman-numbered (title page through the Introduction and its
recovered 2.2 "Lahu dialects" section); the dictionary body resets to
arabic 1; back matter (the two unassigned appendices, the bibliography,
and finally Plates) continues the arabic numbering. `src/latex/toc.tex`
lists every front/back-matter section by name with the correct roman or
arabic page number, resolved automatically via `\pageref`.

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

**Letter dividers**: the original typesetting instructions include 33
"PUT x HERE" markers (one per letter/digraph in the collation
sequence), each marking where a new letter-section begins in the
printed dictionary. These are recognized as their own `divider` band
(`^\s*PUT (.+?) HERE\s*$` against the already-unescaped line) rather
than falling through to the unknown-line `xx`/`err` path -- checked
first, highest priority, so a divider line can never be misclassified.
See README-tei.md for how `divider` becomes a `tei:milestone` and
renders as an ornamental letter break in the HTML/PDF.

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

**`extract_flat_file.py`** -- one-off export: walks
`generated/tei/lahu.xml` (same two-level entry/subentry document-order
traversal as `build_search_db.py` below) and writes
`generated/lahu-flat.csv`, one row per headword and sub-headword, for
spreadsheet-based review outside the TEI/LaTeX pipeline. Not part of
`regenerate-all-files.sh`; run it by hand:

```sh
python3 src/extract_flat_file.py
```

**`extract_loans.py`** -- one-off export, reads `generated/lahu-flat.csv`
and pulls out every `LOAN`/`LOAN?`-tagged entry, extracting a source
language from its etymology note (the same regex-based extraction
`build_search_db.py` reuses for the website's `search_loan_source`
column). Writes `generated/lahu-loanwords.xlsx`:

```sh
python3 src/extract_loans.py
```

## Static search website (docs/)

`docs/` is a self-contained, client-side-only website -- a searchable
digital edition of the dictionary meant to be published with GitHub
Pages (repo Settings -> Pages -> Deploy from branch -> `main` ->
`/docs`; no GitHub Actions workflow needed). Unlike everything else in
this project, `docs/` is checked into git rather than gitignored,
since GitHub Pages serves those files directly.

**How it works.** `src/build_search_db.py` reads `generated/tei/lahu.xml`
(the same source `extract_flat_file.py` uses) and writes
`docs/lahu-dictionary.sqlite3` -- two tables, `articles` (one row per
top-level headword) and `subentries` (one row per sub-headword, linked
by `article_id`), each with plain columns for display and a parallel
set of `search_*` columns (Unicode-normalized, case-folded, but
*not* diacritic-stripped -- Lahu tone marks are contrastive, unlike
the roman cross-language forms a project like STEDT can safely
diacritic-fold) for substring search. It also extracts a loanword
source language from each `LOAN`/`LOAN?` entry's etymology note, the
same way the one-off `src/extract_loans.py` script did for an earlier
spreadheet request. Row `id` order is already correct Lahu collation
order, because `generated/tei/lahu.xml` already is (no need to re-run
`src/lahu_collate.py`'s sort key here).

The page itself (`docs/index.html` + `docs/app.js` + `docs/style.css`)
is plain, hand-written JavaScript -- no Node/npm build step, no
framework. It loads the whole `.sqlite3` file once into the browser's
memory using the official `@sqlite.org/sqlite-wasm` build (vendored by
hand into `docs/lib/sqlite3-wasm/` -- see that folder's `README.md`
for provenance and how to update it) and runs every search query
locally; nothing is ever sent to a server. Layout uses Bootstrap 5
(loaded from a CDN). A search result is always a whole dictionary
article (headword + all its subentries), and the paragraph display
mode is styled to resemble the LaTeX rendering's entry macros (see
`src/latex/lahu-master.tex`'s `\headword`/`\graminfo`/`\notetext`/
`\subentry` comments).

**Rebuilding it.** `src/build_search_db.py` is standalone -- it is
*not* part of `regenerate-all-files.sh` -- run it by hand whenever you
want to refresh the website's data, after regenerating
`generated/tei/lahu.xml`:

```sh
python3 src/build_search_db.py
```

This overwrites `docs/lahu-dictionary.sqlite3` and `docs/db-meta.json`
(the latter carries the database's true decompressed byte size, so the
page can show accurate download-progress -- GitHub Pages gzips a file
this size, so the browser's own `Content-Length` header reports the
compressed wire size instead).

**Publishing it.** `src/publish-site.sh` does the above and then
commits and pushes `docs/` (and `src/build_search_db.py`, if it
changed) to `origin main`, which is all GitHub Pages needs to redeploy
-- there's no CI build step, unlike `~/GitHub/stedt-static`'s
Actions-based publish, since `docs/` has nothing left to build once
`build_search_db.py` has run:

```sh
src/publish-site.sh                                  # default commit message
src/publish-site.sh "Refresh site after fixing entry X"
```

It only stages `docs/` and `src/build_search_db.py` -- any other
pending changes in your working tree (LaTeX/pipeline work, README
edits, etc.) are left uncommitted, exactly as they were; commit those
yourself, separately. That separation is deliberate and worth keeping
by hand too when you're not using the script: a commit that touches
the print/TEI pipeline and a commit that touches the website are
usually about two different things, even on days when you did both.

One-time setup, if you haven't already: repo **Settings -> Pages ->
Build and deployment -> Source: "Deploy from a branch"**, branch
`main`, folder `/docs`. After that, every push that changes `docs/`
redeploys automatically.

**Deploying to a non-GitHub-Pages server.** `src/deploy-to-ec2.sh`
copies `docs/` (the website) and `generated/` (the full pipeline
output, for anyone who wants the raw TEI/HTML/PDF alongside the
searchable site) to a plain Apache box via `rsync` -- both are plain
static files with no absolute paths, so they work unmodified at any
URL depth:

```sh
src/deploy-to-ec2.sh                     # uses the defaults baked into the script
PEM_KEY=~/.ssh/other.pem EC2_HOST=1.2.3.4 src/deploy-to-ec2.sh   # override per run
```

After the transfer it always runs an explicit remote `chmod` pass
(`644` on files, `755` on directories) rather than trusting whatever
permissions the files happen to have locally -- worth knowing because
a file created at mode `600` and copied verbatim is exactly what once
made this site 403 on EC2 with a "disallowed MIME type" error (Apache
returning an HTML error page for a JS module import). If a deploy ever
does 403 again, that's the first thing to check.

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
    the Lexware output (1,750 across the whole dictionary as of the
    current classifier -- 33 fewer than earlier counts, since the 33
    "PUT x HERE" letter-divider lines are now their own `divider` band
    instead of falling through to `xx`/`err`; see "The scripts" above)
    -- mostly lines the classifier couldn't
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
| `generated/lahu-flat.csv` | Whole dictionary flattened to one row per headword/sub-headword, for spreadsheet review (`src/extract_flat_file.py`) |
| `generated/lahu-loanwords.xlsx` | Every `LOAN`/`LOAN?`-tagged entry with extracted source language, formatted spreadsheet (`src/extract_loans.py`, reads the CSV above) |
| `src/lahu-tei-lex0.xml` | Annotated TEI header/entry-structure reference (checked-in, hand-written) |
| `generated/tei/lahu.xml` | TEI Lex-0 digital edition |
| `generated/latex/lahu.html` | Rendered HTML |
| `generated/latex/lahu.tex` | Rendered LaTeX dictionary body (not standalone; `\input` from `src/latex/lahu-master.tex`, checked-in, hand-authored) |
| `generated/latex/frontmatter/*.tex`, `backmatter/*.tex` | Rendered LaTeX front/back matter, one file per recovered document (from `src/process_front_and_back_matter.py`) |
| `generated/latex/frontmatter-pre-toc.tex`, `frontmatter-post-toc.tex`, `backmatter.tex` | Ordered `\input` lists for the files above (also generated -- see that script's module docstring for the order and why) |
| `generated/front-back-matter-report.log` | Front/back matter conversion warnings tally |
| `generated/latex/lahu.pdf` | Compiled PDF (from `src/latex/lahu-master.tex`, which also holds the title page, table of contents, and front/back matter -- see `src/latex/title.tex`/`toc.tex`) |

**Exception: `docs/`.** These two files are also generated -- by
`src/build_search_db.py`, from `generated/tei/lahu.xml` -- but unlike
everything above, they're checked into git rather than gitignored,
since GitHub Pages serves `docs/` directly (see "Static search
website" above):

| File | What |
|---|---|
| `docs/lahu-dictionary.sqlite3` | The search website's whole database (client-side SQLite, loaded via `sqlite3_deserialize`) |
| `docs/db-meta.json` | The database's true (decompressed) byte size, for the page's download-progress indicator |

See inline comments in each script for line-level detail,
`README-lex2xml.md` for the XML conversion specifically, and
`README-tei.md` for the TEI transduction and HTML/PDF rendering.
