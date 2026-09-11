# TEI Lex-0 transduction and rendering

This extends the pipeline in README.md one more step: our ad hoc
band-tagged XML (`generated/lahudico-lexware.xml`, from
`src/lex2xml.py`) is transduced into standard **TEI Lex-0** XML, then
rendered from that TEI into HTML and a print-quality PDF (via XeLaTeX).
The approach (and some of the rendering code) is adapted from the
Jäschke Tibetan-English Dictionary project elsewhere in this workspace,
which used the same three-stage design: an XSLT transducer into TEI,
then a small family of XSLT stylesheets rendering that TEI into
different output formats.

## Pipeline

```
generated/lahudico-lexware.xml
        |
        |  src/lahu-to-tei.xsl  (our ad hoc bands -> TEI Lex-0)
        v
generated/tei/lahu.xml
        |
        +--  src/lahu-html.xsl   -->  generated/latex/lahu.html
        |
        +--  src/lahu-latex.xsl  -->  generated/latex/lahu.tex  (dictionary body only)
                                            |
                                            |  \input from src/latex/lahu-master.tex
                                            |  (preamble, title page, table of contents)
                                            v  --xelatex-->
                                       generated/latex/lahu.pdf
```

The final PDF is compiled from `src/latex/lahu-master.tex`, a
hand-authored scaffold, not from `generated/latex/lahu.tex` directly.
`lahu-master.tex` owns the documentclass, packages, body font, the
dictionary's entry-formatting macros, the running footer, the title
page (`src/latex/title.tex`), and the table of contents
(`src/latex/toc.tex`); it `\input`s the generated dictionary body
inside a `multicols` block it opens and closes. See "Rendering: PDF"
below.

Everything is run through one small generic driver, `src/render_tei.py`
(itself adapted from the Jäschke project's `scripts/render_tei.py`),
which applies any XSLT stylesheet to any XML file using `lxml`:

```
python3 src/render_tei.py --tei generated/lahudico-lexware.xml \
    --xsl src/lahu-to-tei.xsl --out generated/tei/lahu.xml

python3 src/render_tei.py --tei generated/tei/lahu.xml \
    --xsl src/lahu-html.xsl --out generated/latex/lahu.html

python3 src/render_tei.py --tei generated/tei/lahu.xml \
    --xsl src/lahu-latex.xsl --out generated/latex/lahu.tex

xelatex -interaction nonstopmode -output-directory=generated/latex -jobname=lahu src/latex/lahu-master.tex
xelatex -interaction nonstopmode -output-directory=generated/latex -jobname=lahu src/latex/lahu-master.tex   # second pass, for TOC/page refs
```

Run `xelatex` from the project root (`-jobname=lahu` keeps the output
named `generated/latex/lahu.pdf`, matching the earlier single-file
layout, rather than `lahu-master.pdf`); see "Rendering: PDF" below.

`render_tei.py` also strips a handful of stray control bytes before
parsing (see "A well-formedness wrinkle in the Lexware XML" below), and
accepts `--param NAME VALUE` (repeatable) to pass parameters through to
the stylesheet, e.g. `--param show-editorial-notes 1`.

Verified end to end on the full 135-file, 5,061-entry dictionary: the
transducer output is well-formed XML; the HTML renders all 5,061
entries and 26,251 sub-entries; the LaTeX compiles cleanly under
XeLaTeX to a 661-page, two-column PDF (title page + table of contents
+ 33 letter-section dividers + the dictionary body) with all of
Matisoff's tone diacritics and IPA-ish characters (ɔ ɛ ɨ ə ŋ g̈ š ʔ, the
acute/grave/circumflex/macron tone marks, etc.) rendering correctly.

## Band-tag to TEI element mapping

| Lexware band / structure | TEI Lex-0 |
|---|---|
| `.hw` (top-level headword) | `entry/form[@type='lemma']/orth[@xml:lang='lhu']` |
| `..hw` (sub-headword) | sibling `re/form[@type='compound']/orth[@xml:lang='lhu']` |
| `pos` | `gramGrp/gram[@type='pos']` |
| `ld` ("LOAN" / "LOAN?") | `usg[@type='etym']` |
| `bz` (bracketed label, e.g. `[RL]`, `[poetic]`, `[q.v.]`) | `usg[@type='label']`, brackets stripped |
| `gl` not immediately after an `ex` | `sense/def` (see sense numbering below) |
| `gl` immediately after an `ex` | that example's `cit[@type='translation']/quote` |
| `ex` | `cit[@type='example']/quote[@xml:lang='lhu']` |
| `no` | `note` |
| `xx` | `note[@type='unclassified']` -- rendered like a plain note, visible by default (see below) |
| `err`, `srcxcrN` | `note[@type='editorial'][@resp='pipeline']` -- hidden by default |
| `divider` (a "PUT x HERE" letter-section marker, see below) | `milestone[@unit='letter'][@n='x']` |
| `comment`, `mode`, `hdr` | never occur in the real Lahu data; templates present but produce nothing |

### Letter dividers

The original typesetting instructions include 33 "PUT x HERE" markers
(one per letter/digraph in the collation sequence), each marking where
a new letter-section begins in the printed dictionary. `dl_convert.py`
recognizes these (`^\s*PUT (.+?) HERE\s*$`) as their own `divider` band
rather than falling through to `xx`/`err` as unclassified text; see
`README.md`. Because `lex2xml.py`'s band-to-XML conversion has no
concept of "outside any entry," a `divider` line lands as the LAST
child of whatever `entry` or `sub` happened to be open at that point in
the source -- not necessarily a top-level sibling of `entry`. Both
`lahu-html.xsl` and `lahu-latex.xsl` handle this by applying templates
to `tei:milestone` from inside both the entry and sub-entry (`tei:re`)
templates, so the divider renders correctly regardless of source
nesting depth (see "Formatting conventions" below for how each medium
renders it).

Entries keep their source `id` (`Lahu.N`) as `xml:id` directly (it's
already a valid TEI `xml:id`); sub-entries get `Lahu.N.M`.

### Sense numbering

Matisoff numbers multiple senses inline in the gloss text itself
("1. ...", "2. ...", or "a. ...", "b. ..."). The transducer splits a
short (2 characters or fewer) leading numeric or single-letter marker
followed by ". " into `sense/@n`; if a gloss doesn't match that shape,
it becomes a single unnumbered `sense` rather than guessed at. This is
a deliberately conservative heuristic: false negatives (an unsplit
numbered sense) just look like plain prose; false positives are
avoided by requiring the short, tightly-shaped prefix.

### Why stray top-level content is dropped

`generated/lahudico-lexware.xml` has a few `xx`/`err` elements that are NOT
children of any `entry` (running-header noise like "THE DICTIONARY OF
LAHU" repeated at each of the 135 original files' page boundaries,
about 131 times total). These carry no lexicographic content, so
`lahu-to-tei.xsl` only ever applies templates to `entry` elements at
the top level and silently drops this noise. Everything that IS inside
an entry or sub-entry is preserved, including pipeline diagnostics
(as editorial notes).

### Known simplifications

- Only the shape of the leading marker is checked for sense
  numbering (see above); it does not attempt to detect deeper
  hierarchical sense structure (e.g. "1a.", "1b.").
- `usg` elements are emitted as siblings of `sense` within the
  entry/sub-entry, not nested inside a specific `sense` -- our source
  data has no reliable way to tell which sense a `bz`/`ld` band
  belongs to when an entry has more than one, so they're kept in
  document order near the sense they most likely modify rather than
  attached to it structurally.
- `bz` values are not sub-typed (register vs. dialect vs. cross-
  reference); every bracketed annotation becomes `usg[@type='label']`
  with the same treatment, whether it was `[RL]`, `[poetic]`, or
  `[q.v.]`. Splitting these into more specific TEI patterns (e.g. a
  real `xr`/`ref` cross-reference for `[q.v.]`) is a plausible future
  refinement, not attempted here since we don't have resolvable
  targets for the cross-references.

## Formatting conventions (both HTML and PDF)

- **Hanging indent, two levels deep.** A top-level entry's own wrapped
  lines indent to the same column where its sub-entries' headwords
  start; a sub-entry's first line starts at that column, and ITS
  wrapped lines indent one further level. This applies per "paragraph"
  (the headword/sense line, each note, each example individually), so
  a long note or example wraps consistently with the headword line
  above it rather than snapping back to the margin. In the HTML this
  is a CSS custom property (`--indent`, in `lahu-html.xsl`); in the
  PDF it's a LaTeX length (`\dictindent`, in `lahu-latex.xsl`), set via
  `\leftskip`/`\hangindent`/`\hangafter` rather than a fixed first-line
  `\hspace`, specifically so it composes correctly with wrapping.
- **No em-dash prefixes.** Notes and sub-entries used to be marked
  with a leading "&mdash;"; this was removed once indentation alone
  made the structure legible, per user preference.
- **Bracketed annotations (`[RL]`, `[poetic]`, `[LOAN]`, etc.) are
  italic, not colored.** Earlier drafts used a brownish text color for
  these; both stylesheets now use plain italic instead.
- **Notes and examples both render indented one level deeper than the
  headword/sense line they belong to**, not flush with it. A
  top-level entry's notes and examples start at the same column its
  sub-entries' headwords start at (one indent unit in), wrapping one
  further unit; a sub-entry's notes and examples start one unit
  deeper than that (two units in), wrapping to three. In the HTML
  this is `.entry > .note`/`.entry > .example` and
  `.sub-entry > .note`/`.sub-entry > .example`; in the LaTeX it's the
  `\leftskip` set at the top of `\notetext`/`\examplecit` (one
  `\dictindent`) and `\subnotetext`/`\subexamplecit` (two
  `\dictindent`).
- **Notes render between slashes:** `<no>text</no>` becomes
  "/ text /" (CSS `::before`/`::after` content in the HTML; literal
  `/ ... /` in the LaTeX `\notetext`/`\subnotetext` macros). This
  applies uniformly to genuine `no`-derived notes and to the
  `xx`-derived `type="unclassified"` notes described below, since both
  render through the same `tei:note[not(@type='editorial')]` template.
- **Example translations are not quoted.** The Lahu example and its
  English translation are set off by a plain space/quad, not wrapped
  in quotation marks -- an earlier draft used curly single quotes
  (HTML `::before`/`::after`) or backtick/quote (LaTeX `` `...' ``);
  both were removed.
- **The Lahu text in an example (`<ex>` / `cit[@type='example']/quote`)
  is set 2pt smaller than the surrounding entry text**, in both HTML
  (`.example .lahu`, `calc(1em - 2pt)` relative to the example line's
  own already-reduced size) and LaTeX (`\fontsize{7pt}{8.4pt}` in
  `\examplecit`/`\subexamplecit`, ambient body text being `\small`,
  9pt, so 2pt smaller lands at 7pt -- the same absolute size used for
  sub-entry headwords). The English translation on the same line stays
  at the surrounding text's own size.
- **Sub-headwords are bold, not italic, and 2pt smaller than
  top-level headwords.** In the HTML, `.sub-entry .hw` is
  `font-weight: bold; font-size: calc(1.05em - 2pt)`. In the LaTeX,
  `\subentry`'s headword argument is set at `\fontsize{7pt}{8.4pt}`
  (ambient body size is `\small`, 9pt in the 10pt documentclass) in
  bold, versus the plain `\textbf` at ambient size used by the
  top-level `\headword`.
- **`xx` bands (unclassified fallback content) render inline, visibly,
  by default** -- as an ordinary note (`type="unclassified"` in the
  TEI, styled identically to a genuine note), not hidden behind
  `show-editorial-notes` like `err`/`srcxcrN` are. Most of what
  remains as `xx` after `dl_convert.py`'s gloss-continuation merge
  (see README.md's "Known data-quality caveats") is genuine,
  if unclassified, dictionary text rather than pipeline noise, so
  hiding it by default would have silently dropped real content from
  the rendered dictionary. Keeping it visible also makes residual
  parsing gaps easy for a human reviewer to spot directly in the
  rendered page.
- **Letter dividers** (`tei:milestone[@unit='letter']`, see "Letter
  dividers" above) render as a full-width ornamental break: a large
  italic bold letter flanked by horizontal rules, interrupting the
  two-column flow rather than sitting inside a column. In the HTML
  this is CSS `column-span: all` on `.letter-divider` (works even
  though the divider can be nested inside `.entry`/`.sub-entry`, since
  it's still an in-flow descendant of the `.dictionary` multicol
  container). In the PDF (`lahu-latex.xsl` + `src/latex/lahu-master.tex`)
  it's the `\dividerletter` macro, which closes the current `multicols`
  block, prints the rule/letter/rule centered at full page width, then
  reopens `multicols`.
- **PDF only: title page, table of contents, and running head/foot.**
  See "Rendering: PDF" below.

## Rendering: HTML

```
python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-html.xsl --out generated/latex/lahu.html
```

Two-column CSS layout (matching the printed dictionary's general
feel). **Font: DejaVu Serif** (a conventional, widely available system
serif, with fallbacks to Georgia / Times New Roman / the browser's
generic serif) -- not a Google Fonts webfont. An earlier draft used
Google-hosted EB Garamond, which renders Lahu's combining tone
diacritics poorly (missing glyphs / misplaced marks in some browsers);
DejaVu Serif is the same font used for the PDF edition (see below) and
has much more complete Unicode coverage of IPA Extensions and
combining marks, so no separate download is needed for most users. If
you want an even better linguistically-tailored typeface, install
"Charis SIL" or "Doulos SIL" (see below) and add it ahead of 'DejaVu
Serif' in the `body { font-family: ... }` rule.

Pass `--param show-editorial-notes 1` to include the pipeline
diagnostic notes (gray boxes) in the output; they're hidden by default.

## Rendering: PDF (via XeLaTeX)

```
python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-latex.xsl --out generated/latex/lahu.tex

xelatex -interaction nonstopmode -output-directory=generated/latex -jobname=lahu src/latex/lahu-master.tex
xelatex -interaction nonstopmode -output-directory=generated/latex -jobname=lahu src/latex/lahu-master.tex   # second pass, for TOC/page refs
```

Requires XeLaTeX (part of TeX Live / MacTeX) for Unicode support. Run
from the project root (the `\input` paths in `lahu-master.tex` are
relative to it); `-jobname=lahu` keeps the output named
`generated/latex/lahu.pdf` even though the file actually compiled is
`src/latex/lahu-master.tex`.

**`lahu-latex.xsl`'s output (`generated/latex/lahu.tex`) is body
content only** -- the dictionary entries, not a compilable document by
itself. Compile `src/latex/lahu-master.tex` (which `\input`s that body
inside its own `multicols` block), not the XSLT output directly. This
split exists so the title page, table of contents, and any future
front/back matter can be hand-edited without touching generated
output. See `src/latex/lahu-master.tex`, `src/latex/title.tex`, and
`src/latex/toc.tex`.

**Default font: DejaVu Serif** -- set via `\setmainfont` in
`src/latex/lahu-master.tex` (not a stylesheet parameter, since font
selection now lives in that hand-authored file). Chosen (over, say, a
macOS system font) because Matisoff's romanization leans heavily on
combining tone diacritics over both vowels and consonants (including g
with a combining diaeresis, g̈, for the voiced velar fricative), and
DejaVu has some of the broadest free Unicode coverage of IPA
Extensions and combining marks available, plus it ships with most
complete TeX Live installations so it's likely already on your system
via `fontspec` without a separate download. If XeLaTeX can't find it,
either install DejaVu Serif or edit the `\setmainfont{...}` line in
`src/latex/lahu-master.tex` to any other Unicode font you have with
good combining-diacritic support, e.g. `"Charis SIL"` or `"Doulos SIL"`
(both purpose-built for exactly this kind of linguistic data; see
<https://software.sil.org/charis/>).

**Optional math font, for the `⪤` cognate symbol:** the comparative-
linguistics "cognate with" connector `⪤` (U+2AA4 GREATER-THAN
OVERLAPPING LESS-THAN -- what `&` in the source data is recoded to;
see the `LAHU_UNICODE` table in `src/dl_convert.py`) isn't in DejaVu
Serif, isn't in "DejaVu Math TeX Gyre" either, and isn't in any of the
few hundred fonts that ship with a standard TeX Live install. Without
it installed, `⪤` will render as a blank/missing-glyph box wherever it
appears (about 940 places in the full dictionary) -- everything else
compiles and renders fine regardless, this is purely cosmetic for that
one symbol. **"STIX Two Math"** is a free, open-license (OFL) math font
that does have this glyph. To install it:

  * **macOS (Homebrew):** `brew install --cask font-stix-two-math`
  * **Manually (any OS):** download `STIXTwoMath-Regular.ttf` from
    Google Fonts' mirror of the STIX Two family
    (<https://github.com/google/fonts/tree/main/ofl/stixtwomath>) and
    install it like any other font (double-click on macOS/Windows, or
    drop into `~/.local/share/fonts` and run `fc-cache -f` on Linux).

No changes to `lahu-master.tex` are needed after installing -- it
already checks for "STIX Two Math" via `\IfFontExistsTF` and wires it
in as a per-character fallback just for `⪤` (the same pattern used for
`≣`/"DejaVu Math TeX Gyre" just above it in the file); the main body
font stays DejaVu Serif throughout. Just re-run the two `xelatex`
invocations after installing -- no need to regenerate anything.

**Letter dividers, title page, table of contents, running head/foot:**
see `src/latex/lahu-master.tex`'s own comments for the full macro
reference. Briefly:
- 33 letter-section dividers (`\dividerletter`, driven by
  `tei:milestone` in the generated body), each a full-width rule/
  ornamental-letter/rule that closes and reopens `multicols`.
- A standalone title page (`src/latex/title.tex`).
- A table of contents (`src/latex/toc.tex`) listing every front/back-
  matter document (list of plates, acknowledgments, symbols and
  abbreviations, the Introduction outline, the dictionary body's 33
  letter sections, the two back-matter appendices, the bibliography,
  and plates), each with a page number, matching the order in
  `src/front-back-matter-order.csv` and the section order in
  `originals/DLOtherFiles/CONTENTS.TXE`. This is a **hand-built list
  using `\label`/`\pageref`, not `\tableofcontents`/`\addcontentsline`**
  -- see the `\dividerletter` comment in `lahu-master.tex` for why:
  `\addcontentsline` corrupted a page of the compiled PDF when all 33
  dividers were present (a real hyperref/multicol interaction bug,
  confirmed by removing it), so don't reintroduce it without
  re-testing a full compile. Front-matter entries automatically show
  roman numerals and dictionary-body/back-matter entries automatically
  show arabic numerals -- `\pageref` just echoes whatever
  `\pagenumbering` was active on the page a label sits on.
- A running footer (Lahu collation sequence, centered, on every body
  page) and a running head/footer with page numbers: page number in
  the outer corner (left on even/verso pages, right on odd/recto
  pages); header shows the book title on even pages and the current
  letter section (via `\rightmark`, updated by `\markright` in
  `\dividerletter`) on odd pages. `\thispagestyle{empty}` on the title
  and TOC pages suppresses all of this there.

Verified by compiling the full dictionary: 661 pages (title + TOC +
33 dividers + the dictionary body), no LaTeX errors (a normal handful
of "Overfull \hbox" warnings from a few long unbreakable compound
headwords in the narrow two-column layout, purely cosmetic).

Pass `--param show-editorial-notes 1` to `render_tei.py`'s
`lahu-latex.xsl` step to include pipeline diagnostic notes in the PDF.

### If your compile log explodes into millions of lines

If `xelatex`'s log (or a `nohup.out` wrapping it) balloons to hundreds
of megabytes of `Missing character: There is no ... in font nullfont!`
lines -- one for every character on every page -- this is not a
pipeline bug and not an infinite loop; it means `fontspec` couldn't
find the body font at all. The very first sign is further up the same
log:

```
! Package fontspec Error: 
(fontspec)                The font "DejaVu Serif" cannot be found; ...
! Font TU/DejaVuSerif(0)/m/n/10="DejaVu Serif/OT" at 10.0pt not loadable
```

When that happens, XeTeX silently substitutes `nullfont` (a font with
zero glyphs) for the rest of the run rather than aborting, so the
compile "succeeds" and writes a PDF -- but every page of it is blank,
and the log balloons because every single character gets its own
warning. Two fixes, matching the font-fallback guidance above:

  * **Install DejaVu** (matches what this pipeline was verified
    against): on macOS, `brew install --cask font-dejavu` installs the
    whole family, including Serif. Re-run the two `xelatex` invocations
    afterward -- no need to regenerate anything.
  * **Or point at a font you already have**, by editing the
    `\setmainfont{...}` line near the top of `src/latex/lahu-master.tex`
    to any installed Unicode font (see the font paragraph above for
    combining-diacritic caveats), e.g. `\setmainfont{Charis SIL}...`,
    then re-run the two `xelatex` invocations. No need to regenerate
    `generated/latex/lahu.tex` for this -- the font is set in
    `lahu-master.tex`, not in the generated body.

Either way, a missing/misnamed font only ever affects the two `xelatex`
steps at the very end of the pipeline -- if you hit this, everything
from `dl_convert.py` through the TEI/HTML rendering already succeeded.

### A LaTeX-escaping wrinkle worth knowing about

Beyond LaTeX's classic seven special characters (`\ & % $ # _ { }`),
`^` and `~` also need escaping outside math mode -- a literal `^`
otherwise aborts the compile with "Missing $ inserted". A few dozen of
Matisoff's comparative-linguistics notes contain a literal `^` (e.g.
`ga^` marking a syllable that would carry a circumflex) or `~` (marking
free variation, e.g. `N ~ hɔ ~ qha`), so `lahu-latex.xsl`'s
`latex-escape` helper escapes both (`\textasciicircum{}` /
`\textasciitilde{}`), in addition to the classic seven. This was
caught by actually compiling the full document, not just a hand-picked
sample -- worth remembering if you ever add a new render stylesheet
that emits LaTeX: always run a full-document compile before trusting
the escaping is complete.

## Front/back matter

`src/process_front_and_back_matter.py` recovers the dedication, list of
plates, acknowledgments, symbols and abbreviations, bibliography, and
three back-matter appendices from `originals/DLOtherFiles/` and renders
them straight to LaTeX (`generated/latex/frontmatter/*.tex`,
`backmatter/*.tex`), `\input` from `src/latex/lahu-master.tex` around
the dictionary body. It's a separate script from `dl_convert.py` on
purpose: it does its own document-level layout rendering (reflowing
prose, preserving space-aligned tables verbatim, splicing multi-line
runs) that doesn't belong in the core WordStar-to-Unicode converter,
even though it imports and reuses a few of that script's byte-level
functions (`mask_high_bit`, `preprocess_line`, `extract_and_convert_altfont`,
etc.) rather than duplicating them.

**Which files, and why.** `originals/DLOtherFiles/CONTENTS.TXE` turns
out to be more than production notes -- lines 49-123 are a direct
transcription of the book's own printed Table of Contents: List of
Plates, Acknowledgments, Symbols and Abbreviations, an Introduction (with
a full numbered outline, 1.0 through 4.5), the dictionary body,
Bibliography (I/II/III), and Plates, in that order. `src/front-back-
matter-order.csv` records this order (one row per section, reviewed and
approved by the project owner) and is the document to edit if the order
ever needs to change; the manifest in `process_front_and_back_matter.py`
implements it.

Of the Introduction's outline, only **2.2 "Lahu dialects and cultural
subdivisions" survives**, as `DIALIST.TXA` ("The Divisions of the Lahu
People") -- confirmed by title and content, not merely inferred. It was
initially misfiled as an unassigned back-matter appendix before this
match was found; it's now correctly placed in front matter, right where
2.2 belongs. Sections 1.0, 2.0, 2.1, 3.0, and 4.0-4.5 have no surviving
file anywhere in the archive -- confirmed by grepping every front/back-
matter file for each section's distinctive language (genetic position,
Sino-Tibetan, history of the dictionary project, lemmata,
form-classes, subentries, etc.) and finding no match outside of
`ABBREVS2.TXE`'s "Form Classes and Construction Types," which is a
grammatical-abbreviation glossary, not the 4.2 essay. Rather than
silently dropping these nine subsections, `_introduction_placeholder_entry()`
renders one page reproducing the outline and marking each piece present
or missing, so the gap is visible and navigable instead of silently
absent.

`LINGTERM.TXA` and `BIRDLIST.TXC` are a different case: real content,
each headed "APPENDIX #" in the original with the number left blank --
written, but never assigned a final position by the author, and not
part of CONTENTS.TXE's own outline at all. Per the project owner,
they're included as back-matter appendices (before the Bibliography)
rather than over-interpreting CONTENTS.TXE as exhaustive.

Excluded: `ABBREVS.TXB` (an earlier single-column draft of
`ABBREVS2.TXE`, itself marked "REFORMAT INTO DOUBLE COLUMNS AFTER
PROOFING -- KWW"); `BACKMATT.TXA` (an internal planning wishlist, not
finished prose); `LAHUDICT.TXT` (a memo about the DL-ASCII keystroke
scheme itself); `HEADER`/`LAHU.CHR`/`LQLAHU*` (binary printer
font/character-ROM data, no text -- `HEADER` is separately used for
the printed running-footer collation sequence, see `lahu_collate.py`).
`LAHUPREF.TXA` is just the heading "PREFACE IN LAHU" with no surviving
body text; it's still included, rendered as a near-blank page, so a
reader following the running head finds an explicit placeholder rather
than a silent gap. See the script's own module docstring and manifest
tables (`FRONT_MATTER_PRE_TOC`, `FRONT_MATTER_POST_TOC`, `BACK_MATTER`)
for the exact, single-source-of-truth list and order.

**Rendering modes.** The original was typed on a fixed-width font, with
tables and aligned columns done using runs of literal spaces -- there's
no markup to recover that structure from otherwise. Each document is
rendered in one of three modes, picked per file by inspection:
`poem` (centered, line-for-line, no reflow -- the dedication and the
preface stub), `prose` (blank-line-delimited paragraphs reflowed into
normal justified text -- Acknowledgments), or `table` (monospace,
`\obeyspaces` plus a custom active-end-of-line-character trick so both
leading indentation and internal multi-space runs survive exactly --
everything with space-aligned columns, including most of the
appendices). `BIBLIOG.TXE` gets a dedicated `bibliography` mode: its
own abbreviation-code table (`table` mode) followed by three
roman-numeral-headed sections of ordinary author/year citations,
reflowed into hanging-indent paragraphs like the dictionary body's own
entries.

**A LaTeX `\obeylines` gotcha found by compiling the real corpus:**
`\obeyspaces` alone does not preserve a line's *leading* spaces --
TeX's line-reading tokenizer skips them before catcodes even apply.
The `table` renderer instead makes the end-of-line character itself
active (`\catcode`\^^M=\active`) and defines it as `\\\relax` (not
plain `\\`, and not `\obeylines`'s default `\par`): `\relax` blocks
`\\`'s optional `[<length>]` lookahead, which otherwise misfires
whenever a line happens to start with a literal `[` (e.g. DIALIST.TXA's
"[Letter from David Bradley ... by dialect group.]"), throwing
"Missing number"/"Illegal unit of measure" at compile time. Blank
lines are replaced with `\strut` rather than emitted as-is, since two
consecutive forced line breaks with nothing typeset between them is a
separate LaTeX error ("There's no line here to end").

**Two conversion bugs specific to this script, both fixed in it (not
in `dl_convert.py`):**
1. Several of these files (FRONTISP.TXE, PLATES.TXE, ACKNOWL.TXE,
   BIBLIOG.TXE, ABBREVS2.TXE) have an ALTFONT run that opens on one
   physical line and doesn't close until several lines later.
   `dl_convert.py`'s plain-text pipeline converts one physical line at
   a time, so only the run's first line converts correctly; this
   script instead converts each file as one whole-file pass. That in
   turn requires one safety filter: every one of these files' very
   first surviving line is a single bare ALTFONT toggle byte with
   nothing else on it, which the old per-line pipeline already safely
   no-ops on, but which -- once lines are joined -- would otherwise run
   forward looking for its close ANYWHERE LATER IN THE FILE, silently
   converting large stretches of ordinary English through the Lahu
   substitution table. Confirmed and fixed; see
   `_LONE_TOGGLE_LINE_RE` in the script.
2. WordStar's soft/optional line-wrap hyphen (0x1F directly followed by
   a line break) marks a word split at the print margin with no real
   hyphen intended (e.g. "many indi\x1f\r\nviduals" -> "individuals").
   Reflowing wrapped lines back into paragraphs needs this spliced out
   -- including the following line's leading indentation, which is
   just wrap padding -- before rejoining with a single space, or the
   result is a word split by a run of stray spaces instead of a
   wrongly-spaced join. See `_SOFT_WRAP_HYPHEN_EOL_RE`.

**Fonts.** `\ttfamily` needs an explicit `\setmonofont{DejaVu Sans
Mono}` in `lahu-master.tex` (fontspec otherwise falls back to Latin
Modern Mono, which lacks the IPA Extensions this corpus needs
throughout). DejaVu Sans Mono is missing two characters DejaVu Serif
has -- ˊ/ˋ (U+02CA/U+02CB, MODIFIER LETTER ACUTE/GRAVE ACCENT, the
standalone form of a citation-form diacritic) -- given their own
`\newunicodechar` fallback to `\rmfamily`, the same pattern already
used for `≣`/`⪤` (see "Rendering: PDF" above).

**Page numbering and page style.** Front matter (title page through
the dedication/preface, the letter-based table of contents, and the
plates-list/acknowledgments/symbols-and-abbreviations documents) is
roman-numbered; the dictionary body resets to arabic 1; back matter
continues the arabic numbering -- standard book convention. All of
front and back matter uses `\pagestyle{plain}` rather than the
dictionary body's `\pagestyle{fancy}`: the fancy footer's collation-
sequence strip is a navigational aid specific to the alphabetical
dictionary and doesn't belong on, say, the bibliography. A single
`\thispagestyle{plain}` per document (set by `render_document`) isn't
enough on its own for anything longer than one page -- confirmed by
Acknowledgments' second page falling back to the fancy dictionary
footer without the persistent `\pagestyle{plain}` also set in
`lahu-master.tex` around the whole front/back matter section.

## A well-formedness wrinkle in the Lexware XML

`generated/lahudico-lexware.xml` (produced by `src/lex2xml.py`) is not,
by itself, guaranteed to be well-formed XML for two reasons documented
in detail in `src/lex2xml.py`'s module docstring and
`README-lex2xml.md`:

1. A handful of leftover WordStar formatting-toggle control bytes
   (illegal in XML 1.0) survive in a small fraction of entries.
2. If the very last dot-line in the source Lexware text is a sub-
   headword, the original `Lex2XML.pl` (and, originally, our faithful
   port) leaves that `<sub>` unclosed at end-of-file.

Both are now fixed directly in `lex2xml.py` (two disclosed,
intentional deviations from `Lex2XML.pl`'s literal behavior), so
`generated/lahudico-lexware.xml` as currently generated is already
well-formed. `render_tei.py` sanitizes control bytes on the way in
regardless, as a defensive second layer -- so this pipeline keeps
working even if `generated/lahudico-lexware.xml` is ever regenerated
by an older copy of `lex2xml.py`, or if any other similarly-shaped
input is fed through it.

## Files

| File | What |
|---|---|
| `src/lahu-tei-lex0.xml` | Annotated TEI header/entry-structure reference (checked-in, hand-written; not used at runtime) |
| `src/lahu-to-tei.xsl` | The transducer: ad hoc Lexware-band XML to TEI Lex-0 |
| `src/lahu-html.xsl` | TEI Lex-0 to HTML5 |
| `src/lahu-latex.xsl` | TEI Lex-0 to XeLaTeX source (dictionary body only; see below) |
| `src/latex/lahu-master.tex` | Hand-authored scaffold: documentclass/packages, body font, entry-formatting macros (`\headword`, `\dividerletter`, etc.), running head/footer, page numbering/style switches, `\input`s title.tex/toc.tex/the generated dictionary body/the generated front-back matter. Compile THIS with XeLaTeX, not `generated/latex/lahu.tex` directly |
| `src/latex/title.tex` | Hand-authored standalone title page, `\input` from lahu-master.tex |
| `src/latex/toc.tex` | Hand-authored table of contents (`\label`/`\pageref`-based, not `\tableofcontents`; see "Rendering: PDF"), `\input` from lahu-master.tex |
| `src/render_tei.py` | Generic XSLT runner (any stylesheet, any XML) |
| `src/process_front_and_back_matter.py` | Recovers front/back matter from `originals/DLOtherFiles/` and renders it straight to LaTeX; see "Front/back matter" above |
| `generated/tei/lahu.xml` | The transduced TEI Lex-0 edition (generated, gitignored) |
| `generated/latex/lahu.html` | Rendered HTML (generated, gitignored) |
| `generated/latex/lahu.tex` | Rendered LaTeX dictionary body (generated, gitignored; not standalone, see `src/latex/lahu-master.tex`) |
| `generated/latex/frontmatter/*.tex`, `backmatter/*.tex` | Rendered LaTeX front/back matter, one file per document (generated, gitignored) |
| `generated/latex/frontmatter-pre-toc.tex`, `frontmatter-post-toc.tex`, `backmatter.tex` | Ordered `\input` lists for the files above (generated, gitignored) |
| `generated/latex/lahu.pdf` | Compiled PDF, from `src/latex/lahu-master.tex` (generated, gitignored) |
