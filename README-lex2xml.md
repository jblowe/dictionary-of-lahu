# Lexware -> XML conversion (`lex2xml.py`)

`lex2xml.py` is a from-scratch Python port of `Lex2XML.pl` (jbl,
9/9/97; the original is kept at `originals/src/Lex2XML.pl`), the
original tool for converting a Lexware band-tagged file into XML. It
was verified empirically against the real Perl script (perl 5.34.0)
before being trusted: run on all 135 body Lexware files individually
and on the full `generated/lahudico-lexware.txt`, the Python port
produces XML and tag-frequency logs identical to `Lex2XML.pl` in every
case, modulo three disclosed, intentional deviations described below
(all three needed so the output is genuinely well-formed XML, which
matters once you want to feed it to further tooling -- see
README-tei.md for the TEI Lex-0 transducer this feeds into).

One of those three was caught as an unintended bug during the initial
byte-for-byte verification pass and immediately fixed to match Perl
exactly (so it never became a real deviation): Python's default
whitespace-trimming -- both `str.strip()` and regex `\s` in Unicode
mode -- treats the C0 "separator" control bytes 0x1C-0x1F as
whitespace, while Perl's `\s` does not. A few Lahu entries contain a
leftover 0x1F byte (an unresolved WordStar formatting-toggle remnant),
and the first draft of the port was silently trimming it off where the
real Perl script keeps it. Fixed by trimming only Perl's narrower ASCII
whitespace set.

The other two ARE genuine, disclosed deviations from Perl's literal
behavior -- see "Two more deliberate deviations" below.

## Usage

`lex2xml.py` lives in `src/` alongside the rest of the code; the
Lexware input/output paths are ordinary arguments, so it can be run
from the project root (or anywhere) as:

```
python3 src/lex2xml.py <infile> <outfile.xml> <logfile> <dialect>
```

Run against `generated/lahudico-lexware.txt` to produce
`generated/lahudico-lexware.xml` and `generated/lex2xml-report.log`
(tag-frequency statistics, in the same format as the original Perl's
log):

```
python3 src/lex2xml.py generated/lahudico-lexware.txt generated/lahudico-lexware.xml generated/lex2xml-report.log Lahu
```

## What it does

Reads the Lexware file line by line (`band\tvalue`):

  * Blank lines are skipped.
  * `&`, `<`, `>` are XML-escaped everywhere, including inside band
    values, so a literal `<` typed in the dictionary text becomes
    `&lt;` rather than breaking the XML.
  * A line starting with `*` becomes a `<comment>` element wrapping
    the whole line, unparsed.
  * A line starting with digits is a numbered "mode" band -- a
    nesting convention from a different dictionary project. Unused in
    our Lahu data, but supported for fidelity with the original.
  * Every other band becomes a same-named XML element wrapping its
    value (`<gl>...</gl>`, `<ex>...</ex>`, `<err>...</err>`, etc.). A
    band with an *empty* value is dropped entirely -- no element is
    emitted for it at all. This matches the original's `brackets()`
    helper, which returns nothing for empty data.
  * A bracket-citation convention, `[[[...`, used by some other
    dictionaries built on this same tooling, is expanded into nested
    `<srcxcrN>` tags by `brackets()`. It shows up occasionally in our
    Lahu data too (56 times in the full dictionary) -- typically where
    an unclosed `[` appears in a long editorial note that got split
    across several `xx`/`err` lines by the upstream parser -- and is
    handled identically to the original.

## Headword and sub-headword nesting (the part the user specifically
## asked about)

A line starting with one or more dots is an entry/sub-entry marker:

  * A single dot (our `.hw` band) starts a new top-level
    `<entry id="DIALECT.N">`, first closing the previous entry (and
    any currently-open `<sub>` or `<mode>`).
  * Two or more dots (`..hw`, `...hw`, ...) starts a new `<sub>`
    element, first closing any previously-open `<sub>`.

**Important limitation, inherited unchanged from the original Perl:**
`Lex2XML.pl` does not track a nesting *stack* -- it only remembers
"is a `<sub>` currently open," via a single boolean flag. That means
`..hw` (dot-count 2) and `...hw` (dot-count 3, if it ever occurred)
would be treated identically: every sub-headword becomes a *sibling*
`<sub>` element directly inside the enclosing `<entry>`, never nested
inside another `<sub>`. Concretely:

```xml
<entry id="Lahu.2">
  <hw>a</hw>
  ...
  <sub>
    <hw>a ɛ̀</hw>
    ...
  </sub>
  <sub>
    <hw>qɔ̄ a ɛ̀ te ve</hw>
    ...
  </sub>
</entry>
```

Both sub-entries above are flat siblings of each other, not nested,
regardless of how many dots preceded their `..hw` band in the source.
Since our Lexware output (per `dl_convert.py`) currently only ever
emits one or two dots (`.hw` / `..hw`), this limitation doesn't lose
any real structure for *this* dictionary -- but it's worth knowing if
the band convention is ever extended to a third nesting level.

A special legacy `hdr` band (used only by a different, non-Lahu
dictionary built with the same original tooling) is supported for
parity with the Perl but never appears in our data.

## Two more deliberate deviations from Lex2XML.pl

Both were found by trying to actually parse
`generated/lahudico-lexware.xml` with a real XML parser (`lxml`) once a
downstream TEI transducer needed to consume it -- Perl's own
string/file handling never complained, since Perl doesn't validate XML
well-formedness on write.

1. **Stray illegal XML characters.** A handful of leftover WordStar
   formatting-toggle control bytes (e.g. 0x19, 0x1F) survive in a small
   fraction of entries from the upstream WordStar-to-Unicode
   conversion. These are flatly illegal in XML 1.0 (the `Char`
   production excludes 0x00-0x08, 0x0B, 0x0C, and 0x0E-0x1F) -- about
   10,000 such bytes across the full `generated/lahudico-lexware.xml`,
   one of which broke `lxml`'s parser outright on first attempt. `lex2xml.py` now
   strips them (`strip_illegal_xml_chars`); Perl passes them through
   uncomplained.
2. **Unclosed `<sub>` at end-of-file.** If the very last dot-line in
   the Lexware input is a sub-headword (`..hw`), the real Perl leaves
   that `<sub>` unclosed -- it only ever emits an unconditional final
   `</entry>`, with no check for whether a `<sub>` (or `<mode>`) was
   still open. `lex2xml.py` now closes any tag still open when the
   input ends.

Both are narrow, mechanical fixes (verified to be the *only* two
categories of difference across all 135 files plus the full master
file -- see "Verifying it yourself" below), not changes to any
linguistic content or band-to-tag mapping.

## Verifying it yourself

```
perl originals/src/Lex2XML.pl generated/lahudico-lexware.txt /tmp/perl.xml /tmp/perl.log Lahu
python3 src/lex2xml.py generated/lahudico-lexware.txt /tmp/py.xml /tmp/py.log Lahu
diff /tmp/perl.xml /tmp/py.xml
diff /tmp/perl.log /tmp/py.log
```

The log files are still byte-for-byte identical (line/tag counts are
unaffected by the two structural/character fixes above). The XML files
now differ only in the two disclosed ways: the ~10,000 stripped control
bytes, and (only on inputs that end mid-sub-entry) one extra `</sub>`
right before the final `</entry>`.

## Tag statistics for the whole dictionary (`generated/lex2xml-report.log`)

| Tag | Count |
|---|---|
| `hw` | 31,312 |
| `sub` | 26,251 |
| `entry` | 5,061 |
| `gl` | 38,350 |
| `pos` | 30,950 |
| `no` | 11,480 |
| `ex` | 5,314 |
| `err` | 1,783 |
| `xx` | 1,342 |
| `bz` | 2,345 |
| `ld` | 1,621 |
| `srcxcr` | 56 |

(`err`/`xx` are lower than in earlier drafts of this table because
`dl_convert.py`'s gloss-continuation-merge heuristic now recovers 117
lines that used to fall through to `xx`/`err`; see the "Known
data-quality caveats" section of README.md.)
