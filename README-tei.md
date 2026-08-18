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
        +--  src/lahu-latex.xsl  -->  generated/latex/lahu.tex  --xelatex-->  generated/latex/lahu.pdf
```

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
xelatex -interaction nonstopmode -output-directory=generated/latex generated/latex/lahu.tex
xelatex -interaction nonstopmode -output-directory=generated/latex generated/latex/lahu.tex   # second pass, for page refs
```

`render_tei.py` also strips a handful of stray control bytes before
parsing (see "A well-formedness wrinkle in the Lexware XML" below), and
accepts `--param NAME VALUE` (repeatable) to pass parameters through to
the stylesheet, e.g. `--param show-editorial-notes 1` or
`--param body-font "Charis SIL"`.

Verified end to end on the full 135-file, 5,061-entry dictionary: the
transducer output is well-formed XML; the HTML renders all 5,061
entries and 26,251 sub-entries; the LaTeX compiles cleanly under
XeLaTeX to a 656-page, two-column PDF with all of Matisoff's tone
diacritics and IPA-ish characters (ɔ ɛ ɨ ə ŋ g̈ š ʔ, the acute/grave/
circumflex/macron tone marks, etc.) rendering correctly.

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
| `comment`, `mode`, `hdr` | never occur in the real Lahu data; templates present but produce nothing |

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
xelatex -interaction nonstopmode -output-directory=generated/latex generated/latex/lahu.tex
xelatex -interaction nonstopmode -output-directory=generated/latex generated/latex/lahu.tex   # second pass, for page refs
```

Requires XeLaTeX (part of TeX Live / MacTeX) for Unicode support.
**Default font: DejaVu Serif** -- chosen (over, say, a macOS system
font) because Matisoff's romanization leans heavily on combining tone
diacritics over both vowels and consonants (including g with a
combining diaeresis, g̈, for the voiced velar fricative), and DejaVu
has some of the broadest free Unicode coverage of IPA Extensions and
combining marks available, plus it ships with most complete TeX Live
installations so it's likely already on your system via `fontspec`
without a separate download. If XeLaTeX can't find it, either install
DejaVu Serif or point `--param body-font` at any other Unicode font you
have with good combining-diacritic support, e.g. `"Charis SIL"` or
`"Doulos SIL"` (both purpose-built for exactly this kind of linguistic
data; see <https://software.sil.org/charis/>).

Verified by compiling the full dictionary: 656 pages, no LaTeX errors
(a normal handful of "Overfull \hbox" warnings from a few long
unbreakable compound headwords in the narrow two-column layout, purely
cosmetic).

Pass `--param show-editorial-notes 1` to include pipeline diagnostic
notes in the PDF.

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
    afterward -- no need to regenerate `lahu.tex` itself.
  * **Or point at a font you already have**, by regenerating
    `lahu.tex` with `--param body-font "..."` set to any installed
    Unicode font (see the font paragraph above for combining-diacritic
    caveats), e.g.:
    ```
    python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-latex.xsl \
        --out generated/latex/lahu.tex --param body-font "Charis SIL"
    ```

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
| `src/lahu-latex.xsl` | TEI Lex-0 to XeLaTeX source |
| `src/render_tei.py` | Generic XSLT runner (any stylesheet, any XML) |
| `generated/tei/lahu.xml` | The transduced TEI Lex-0 edition (generated, gitignored) |
| `generated/latex/lahu.html` | Rendered HTML (generated, gitignored) |
| `generated/latex/lahu.tex`, `generated/latex/lahu.pdf` | Rendered LaTeX source and compiled PDF (generated, gitignored) |
