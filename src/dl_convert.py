#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dl_convert.py -- modernize the salvaged WordStar files of James A. Matisoff's
"The Dictionary of Lahu" (1988) into readable Unicode plain text, and
convert the 135 main-body files into a Lexware-format (band-tagged) file.

PROVENANCE / DESIGN
--------------------
This script reworks the logic of two legacy Perl scripts found alongside
the salvaged data:

  * STEDT5-U4Map-7.plx (R. Cook / D. Yu) -- maps the custom "STEDT" Mac
    font (itself a later stand-in for the original CP/M "alternate font"
    used on the Osborne/Epson hardware) to Unicode 4.0. Its __DATA__
    table is the authoritative byte<->Unicode correspondence for the
    Lahu/IPA-ish glyph repertoire used throughout the Dictionary.

  * LahuParse.pl (Mike Brodhead, 1994) -- reads the raw WordStar files and
    (a) recognizes the WordStar "alternate font" escape runs, (b)
    substitutes each DL-ASCII keystroke for its special-font equivalent
    via %stedt_char, and (c) classifies each line of a dictionary article
    (headword / sub-headword / gloss / example / note / part-of-speech /
    etc.) for Lexware output. Its `lexware.ph` band-name include file was
    not recovered with the rest of the archive, so the Lexware band names
    used below (hw/pos/gl/ngl/exgl/ex/no/bz/ld/xx/err) are a reconstruction
    from context and from the band-naming convention described by the
    project owner: a dot count marks nesting depth around the *same* band
    name -- single-dot for a top-level article (".hw"), double-dot for a
    sub-article ("..hw"), and so on for deeper nesting -- while everything
    else is left undotted, in the Shoebox/MDF style the rest of the code
    implies.

  KEY SIMPLIFICATION vs. the original two-stage pipeline: rather than
  converting DL-ASCII -> STEDT-font bytes -> Unicode, this script merges
  %stedt_char with the STEDT5-U4Map-7.plx table ONE TIME (see
  build_tables.py, shipped alongside this script, for the derivation) to
  go DL-ASCII -> Unicode directly. The one genuinely tricky part, flagged
  by the project owner: the STEDT font stores diacritics BEFORE the base
  character they modify (a non-spacing-before convention inherited from
  the CP/M "backspace and overprint" keystroke sequence); Unicode combining
  marks go AFTER the base character. build_tables.py performs that
  reordering once, so everything downstream (LAHU_UNICODE, below) just
  uses correctly ordered Unicode combining sequences.

WORDSTAR / FILE-FORMAT NOTES (established by inspecting the raw bytes)
------------------------------------------------------------------------
  * Body files (originals/DLWordStarFiles/base/BASE.*) use bare CR (0x0D) line
    endings and are pure 7-bit ASCII plus C0 control codes; some
    front/back-matter files use CRLF and *do* use the high bit.
  * WordStar sets the high (8th) bit on the last character of each word
    during paragraph fill/justification (a "soft word-boundary" mark).
    This carries no separate meaning, so it is always safe to mask it off
    (byte & 0x7F) -- confirmed by masking recovering perfectly ordinary
    prose in SYMBOLS ("Du<E5>" -> "Due", i.e. 0xE5 & 0x7F == ord('e')).
  * Every file ends with one contiguous run of 0x1A (Ctrl-Z) bytes --
    classic CP/M end-of-block padding -- verified (programmatically, over
    all 135 base files) to always be a single trailing run with nothing
    real after it. It is stripped.
  * Lines starting with '.' are WordStar dot-commands (page layout,
    headers/footers, print-driver patches for the Epson LQ-1500, etc.)
    In this archive the WordStar 2-column layout is a PRINT-TIME
    formatting feature, not something baked into the stored text -- the
    stored files are already linear -- so simply dropping dot-command
    lines (exactly what LahuParse.pl already did) is sufficient
    "deformatting"; there is no interleaved column text to reflow.
  * Escape toggles found in the data (byte -> meaning):
        0x17 / 0x11   (Ctrl-W / Ctrl-Q)  ALTFONT on / off      (body files)
        0x01 / 0x0E   (Ctrl-A / Ctrl-N)  ALTFONT on / off      (some front/back matter)
        0x12 ... 0x11 (Ctrl-R ... Ctrl-Q) subscript region (unwrapped, kept as plain text --
                        LahuParse.pl itself discards subscript formatting, it doesn't
                        transliterate or mark it up)
        0x14 ... 0x14 (Ctrl-T ... Ctrl-T) superscript tone-number -> superscript digit
        0x08          (Backspace) diacritic-composition marker used *within* an
                        altfont run: "X" BS "d" means d combines onto X
        0x02 ... 0x02 (Ctrl-B) bold          -> **...**   (best-effort)
        0x13 ... 0x13 (Ctrl-S) underline     -> _..._     (best-effort)
        0x19 ... 0x19 (Ctrl-Y) italic        -> *...*
        0x1F          soft/wrap hyphen -> dropped if at end of line, else em dash
  * A handful of rarer control bytes (0x04, 0x05, 0x06, 0x0B, 0x16, 0x1E,
    and any stray/unpaired 0x12) show up inconsistently across files and
    do not have a single reliable interpretation across the whole corpus
    (their pairing behavior differs from file to file). Per-file/per-run
    experimentation showed no safe universal rule, so these are simply
    stripped, and every stripped byte is tallied in the *.log report so
    the frequency is visible and auditable rather than silently guessed at.

OUTPUTS (all under generated/, never written into originals/)
----------------------------------------------------------------
  generated/DLOtherFiles-plaintext/                 (from originals/DLOtherFiles)
  generated/DLWordStarFiles/base-plaintext/         (from originals/DLWordStarFiles/base)
  generated/DLWordStarFiles/base-lexware/           (from originals/DLWordStarFiles/base, Lexware bands)
  generated/conversion-report.log                   (per-file warnings/unknowns tally)

GLOSS-CONTINUATION MERGE (post-classification heuristic)
---------------------------------------------------------
  Some glosses/example-translations wrap across more physical lines than
  the line-by-line classifier's own in-progress window recognizes --
  typically because the immediately preceding line was already claimed
  by a more specific pattern (e.g. an example line), which flushes
  whatever gloss was accumulating and starts a fresh one, orphaning the
  next physical line. Before falling through to the generic "unknown
  line" case, parse_base_file_to_lexware() checks for the single most
  common shape of orphaned continuation: an indented line with no
  Lahu-script altfont marker of its own (no 0x17 byte), immediately
  after a gloss that's either still accumulating in the `gloss` buffer
  or was just flushed as the most recent `gl` band. When it matches,
  the line is appended onto that gloss/translation instead of being
  emitted as an `xx`/`err` pair, and a "Merged as gloss continuation
  (...)" line is written to the per-file LOG.*.txt as a WARNING rather
  than an error. Anything that still doesn't match this shape (e.g. it
  contains an altfont run, or there's no gloss in progress to attach
  it to) falls through to the ordinary xx/err handling unchanged --
  see README.md's "Known data-quality caveats" for the current
  before/after counts.

USAGE
-----
  python3 dl_convert.py [path-to-project-root]     (defaults to '.';
                          the root containing originals/ and generated/)
"""

import glob
import os
import re
import sys
import unicodedata
from collections import Counter

# =====================================================================
# 1. THE MERGED DL-ASCII -> UNICODE TABLE
#    (mechanically derived by composing LahuParse.pl's %stedt_char with
#    STEDT5-U4Map-7.plx's byte->Unicode table and reordering
#    diacritic-before-base to base-then-combining-mark; see
#    build_tables.py, shipped alongside this script, for the derivation.)
# =====================================================================

LAHU_UNICODE = {
    '!': 'ˆ',  # circumflex
    '$': 'ə',  # schwa
    '%': 'ɔ',  # open-o
    '0': '̌',  # hacheck/caron
    '1': 'ā',  # a-bar (macron)
    '2': 'ɛ̄',  # epsilon-bar
    '3': 'ē',  # e-bar
    '4': 'ə̄',  # schwa-bar
    '5': 'ɔ̄',  # open-o-bar
    '6': 'ɨ̄',  # barred-i-bar
    '7': 'ū',  # u-bar
    '8': 'ī',  # i-bar (STEDT's dotless-i is a font-rendering workaround no longer needed in Unicode)
    '9': 'ō',  # o-bar
    ':': '́',  # acute (standalone/combining form)
    ';': '̀',  # grave (standalone/combining form)
    '<': 'î',  # i-circumflex
    '>': 'ô',  # o-circumflex
    '?': '̈',  # umlaut/diaeresis (standalone/combining form)
    '@': 'ɛ',  # epsilon
    'A': 'à',  # a-grave
    'B': 'ɔ̂',  # open-o-circumflex
    'C': 'ê',  # e-circumflex
    'D': 'è',  # e-grave
    'E': 'é',  # e-acute
    'F': 'ə̀',  # schwa-grave
    'G': 'ɔ̀',  # open-o-grave
    'H': 'ɨ̀',  # barred-i-grave
    'I': 'í',  # i-acute (see note at '8' above re: dotless-i)
    'J': 'ù',  # u-grave
    'K': 'ì',  # i-grave (see note at '8' above re: dotless-i)
    'L': 'ò',  # o-grave
    'M': 'û',  # u-circumflex
    'N': 'ɨ̂',  # barred-i-circumflex
    'O': 'ó',  # o-acute
    'P': 'š',  # s-hacheck (esh substitute)
    'Q': 'á',  # a-acute
    'R': 'ə́',  # schwa-acute
    'S': 'ɛ̀',  # epsilon-grave
    'T': 'ɔ́',  # open-o-acute
    'U': 'ú',  # u-acute
    'V': 'ə̂',  # schwa-circumflex
    'W': 'ɛ́',  # epsilon-acute
    'X': 'ɛ̂',  # epsilon-circumflex
    'Y': 'ɨ́',  # barred-i-acute
    'Z': 'â',  # a-circumflex
    '\\': 'ʔ',  # glottal stop
    ']': '̊',  # over-ring (standalone/combining form)
    '^': 'ɨ',  # barred-i
    '_': '≡',  # "triple-dash" -> IDENTICAL TO (three stacked bars)
    '{': 'ŋ',  # ng (eng)
    '|': '≣',  # "quadruple-dash" -> STRICTLY EQUIVALENT TO (four stacked bars)
    '}': 'g̈',  # g-umlaut (voiced velar fricative substitute)
    '~': '~',  # alternation tilde
    '&': '⪤',  # comparative-linguistics "cognate with" connector (was a
               # literal passthrough ampersand; every occurrence in the
               # corpus is this use, never literal English "and")
}

# Characters that pass through an ALTFONT run unmodified (shared between
# the ordinary and the alternate font): from LahuParse.pl's $unchanged,
# minus \x19 (italics), which this script now handles as a toggle before
# altfont extraction rather than passing through literally.
UNCHANGED_CHARS = set(" (),-=aiueogjdnbmhyfvl" "qkctp" "h" "w*rs'z/")
# NB: '&' used to be listed here (plain passthrough); it's now a LAHU_UNICODE
# entry instead (see above), since every occurrence in the corpus is the
# comparative-linguistics "cognate with" connector, not literal English "and".

# Small, deliberately conservative extension beyond LahuParse.pl's original
# $unchanged: plain ASCII punctuation/letters that turn up inside ALTFONT
# runs in citation-heavy entries (e.g. an embedded English quotation or a
# stray footnote/section-reference character) and clearly aren't Lahu
# phonetic substitutes. The 1994 original had no entry for these either and
# would have logged the same "unknown character" warning; passing them
# through unchanged is strictly better than mangling or dropping them.
UNCHANGED_CHARS |= set('".#x+[')

# The six diacritics that can ALSO appear "bare" (not composed onto a
# base letter via the char+BS+diacritic keystroke sequence) -- typically
# used to accent citation forms in other languages/abbreviations. When
# bare, render as a free-standing (spacing) Unicode modifier letter
# instead of a combining mark with nothing to combine with.
STANDALONE_DIAC = {
    ':': 'ˊ',  # MODIFIER LETTER ACUTE ACCENT
    ';': 'ˋ',  # MODIFIER LETTER GRAVE ACCENT
    '!': 'ˆ',  # MODIFIER LETTER CIRCUMFLEX ACCENT
    '0': 'ˇ',  # CARON
    '?': '¨',  # DIAERESIS
    ']': '˚',  # RING ABOVE
}
DIAC_TRIGGERS = set(STANDALONE_DIAC)

# '.' (dot below) is a seventh composing diacritic -- used throughout
# citation forms from Sanskrit/Pali/Tibetan(WT)/Burmese(WB) loanword
# etymologies for retroflex/other dotted consonants, e.g. "n\x08." -> ṇ,
# "s\x08." -> ṣ, "t\x08." -> ṭ, "d\x08." -> ḍ (~60 occurrences across the
# corpus; verified by grepping every base+BS+char triple in the raw
# source). Deliberately kept OUT of STANDALONE_DIAC/DIAC_TRIGGERS: unlike
# the six above, a bare '.' is overwhelmingly ordinary sentence-final
# punctuation, so it must never be caught by the bare-standalone-diacritic
# path -- only usable here, in composition (base + BS + diacritic).
# NFC normalization (already applied at the end of both pipelines) folds
# base+U+0323 into the precomposed Unicode letter (ṇ, ṣ, ṭ, ḍ, ...)
# automatically, so no further composition step is needed.
COMPOSE_ONLY_DIAC = {
    '.': '̣',  # COMBINING DOT BELOW
}
# Combined lookup used only at the point of composing a diacritic onto a
# preceding base character (see convert_lahu): every DIAC_TRIGGERS byte's
# COMBINING form (not its bare/spacing STANDALONE_DIAC form) plus the
# compose-only diacritics above.
_COMPOSE_DIAC_VALUE = {d: LAHU_UNICODE[d] for d in DIAC_TRIGGERS}
_COMPOSE_DIAC_VALUE.update(COMPOSE_ONLY_DIAC)

SUPERSCRIPT_DIGITS = {
    '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
    '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '0': '⁰',
}
# a rendered superscript digit that ends up (rarely) inside an ALTFONT run
# should just pass through, not be treated as an unknown character
UNCHANGED_CHARS |= set(SUPERSCRIPT_DIGITS.values())

ALTFONT_OPEN = set('\x17\x01')
ALTFONT_CLOSE = set('\x11\x0e')

# =====================================================================
# 2. LOW-LEVEL BYTE / LINE PREPROCESSING
# =====================================================================

def mask_high_bit(data: bytes) -> bytes:
    """WordStar sets the 8th bit on the last character of each word during
    paragraph fill. It carries no independent meaning; mask it off."""
    return bytes(b & 0x7F for b in data)


def strip_trailing_ctrlz(data: bytes) -> bytes:
    """Strip the trailing CP/M end-of-block padding (a run of 0x1A,
    optionally followed by stray CR/LF), verified to always occur as a
    single contiguous run at the true end of file in this archive."""
    return data.rstrip(b'\x1a\r\n')


def split_logical_lines(text: str):
    """Body files use bare CR; some front/back-matter files use CRLF.
    Normalize both to a plain list of lines."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.split('\n')


def is_dot_command(line: str) -> bool:
    return line.startswith('.')


# =====================================================================
# 3. PER-LINE TEXT PIPELINE (bold/italic/underline, superscripts,
#    stray-control cleanup) -- shared by both the plain-text and the
#    Lexware pipelines.
# =====================================================================

def _toggle_pair_sub(line: str, byte: str, open_mark: str, close_mark=None) -> str:
    close_mark = close_mark if close_mark is not None else open_mark
    if byte not in line:
        return line
    parts = line.split(byte)
    out = [parts[0]]
    for idx, p in enumerate(parts[1:], start=1):
        out.append((open_mark if idx % 2 == 1 else close_mark) + p)
    return ''.join(out)


_SUPERSCRIPT_RE = re.compile('\x14([^\x14]*)\x14')


def preprocess_line(line: str, warnings: Counter) -> str:
    # superscript tone-digits
    line = _SUPERSCRIPT_RE.sub(
        lambda m: ''.join(SUPERSCRIPT_DIGITS.get(c, c) for c in m.group(1)), line)
    # bold / underline / italic toggles (best-effort; see module docstring)
    line = _toggle_pair_sub(line, '\x02', '**')
    line = _toggle_pair_sub(line, '\x13', '_')
    line = _toggle_pair_sub(line, '\x19', '*')
    # soft wrap-hyphen / em dash
    line = re.sub(r'\x1f(\s|$)', r'\1', line)
    line = line.replace('\x1f', '—')
    # strip any remaining control byte we don't have a confident, uniform
    # rule for (see docstring) -- but keep the bytes the altfont-extraction
    # stage still needs.
    keep = set('\x17\x01\x11\x0e\x08\t')
    out = []
    for ch in line:
        if ord(ch) < 0x20 and ch not in keep:
            warnings['stripped 0x%02X' % ord(ch)] += 1
            continue
        out.append(ch)
    return ''.join(out)


_BACKSPACE_RUN_RE = re.compile(r'\x08{2,}')


def _expand_multibase_diacritic_runs(s: str, warnings: Counter) -> str:
    """Rare WordStar keystroke irregularity: K base characters followed by
    K consecutive backspaces followed by K diacritic characters, e.g.
    "st\x08\x08.." (instead of the normal, interleaved "base BS diacritic"
    repeated K times, e.g. "s\x08.t\x08."). Each backspace moves the print
    head back one more position, so after K of them the head is sitting K
    characters back; printing each diacritic in turn overstrikes one base
    and (typewriter-style) advances the head by one, so the diacritics end
    up applied to the K preceding bases in the same left-to-right order --
    i.e. this means exactly the same thing as the normal interleaved form.
    Rewritten here into K ordinary single triples so the composition logic
    in convert_lahu below can handle it completely unmodified.

    Verified against the one occurrence of this pattern in the whole
    corpus: "ust\x08\x08..ra" in BASE.LH-IU.TXE (Skt. "camel", -> uṣṭra),
    where the same word appears correctly keystroked the normal way
    elsewhere in the dictionary (BASE.LH-KA.TXE); see README.md.
    """
    if '\x08\x08' not in s:
        return s
    out = []
    i = 0
    for m in _BACKSPACE_RUN_RE.finditer(s):
        k = len(m.group(0))
        start, end = m.start(), m.end()
        if start - k < i or end + k > len(s):
            continue  # not enough room for a clean K/K/K match; leave it
            # for the ordinary per-character loop (which drops stray
            # backspaces and warns, same as any other unexpected control byte)
        bases = s[start - k:start]
        diacs = s[end:end + k]
        out.append(s[i:start - k])
        out.append(''.join(b + '\x08' + d for b, d in zip(bases, diacs)))
        warnings['multi-backspace diacritic run expanded (k=%d)' % k] += 1
        i = end + k
    out.append(s[i:])
    return ''.join(out)


def convert_lahu(s: str, warnings: Counter) -> str:
    """Convert the contents of one ALTFONT run (DL-ASCII Lahu keystrokes)
    to Unicode. Handles the char+BS+diacritic composition, bare
    diacritics, the main substitution table, and pass-through characters."""
    s = _expand_multibase_diacritic_runs(s, warnings)
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == '\x08':
            # stray backspace with nothing sensible to compose -- drop
            i += 1
            continue
        if c in ('\x19', '\x02', '\x13'):
            # italic/bold/underline toggle bytes reaching this deep (e.g. via
            # the Lexware pipeline, which doesn't pre-resolve them into
            # markdown the way the plain-text pipeline does) -- a band field
            # has no use for print-attribute toggles, so drop silently.
            i += 1
            continue
        if i + 2 < n and s[i + 1] == '\x08' and s[i + 2] in _COMPOSE_DIAC_VALUE:
            base = s[i]
            diac = s[i + 2]
            base_uni = LAHU_UNICODE.get(base)
            if base_uni is None:
                base_uni = base if (base in UNCHANGED_CHARS or base.isalpha()) else base
                if not (base in UNCHANGED_CHARS or base.isalpha()):
                    warnings['unknown base before diacritic %r' % base] += 1
            out.append(base_uni + _COMPOSE_DIAC_VALUE[diac])
            i += 3
            continue
        if c in DIAC_TRIGGERS:
            out.append(STANDALONE_DIAC[c])
            i += 1
            continue
        if c in LAHU_UNICODE:
            out.append(LAHU_UNICODE[c])
        elif c in UNCHANGED_CHARS:
            out.append(c)
        else:
            warnings['unknown Lahu character %r (0x%02X)' % (c, ord(c))] += 1
            out.append('‹%02X›' % ord(c))
        i += 1
    return ''.join(out)


def extract_and_convert_altfont(line: str, warnings: Counter) -> str:
    """Full (non-structure-preserving) conversion: walk the line, convert
    every ALTFONT run to Unicode, drop the toggle bytes and any stray
    subscript / unmatched markers. Used for the plain-text pipeline."""
    out = []
    i, n = 0, len(line)
    strip_stray = ALTFONT_OPEN | ALTFONT_CLOSE | {'\x08', '\x12'}
    while i < n:
        c = line[i]
        if c in ALTFONT_OPEN:
            j = i + 1
            while j < n and line[j] not in ALTFONT_CLOSE:
                j += 1
            out.append(convert_lahu(line[i + 1:j], warnings))
            i = j + 1 if j < n else n
        elif c in strip_stray:
            i += 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


# Defensive normalization, applied at the very end of both the plain-text
# and Lexware pipelines (see below): the source has no curly/typographic
# quotation marks anywhere -- Matisoff's WordStar files only ever use
# plain ' and " -- so none of the conversion logic above deliberately
# produces curly quotes either. Kept here as a guard in case any future
# change (a new table entry, a copy-pasted note, etc.) introduces one
# accidentally; folds it straight back to the plain ASCII equivalent
# rather than letting a stray curly quote slip through unnoticed.
_TYPOGRAPHIC_QUOTES = {
    '’': "'",  # RIGHT SINGLE QUOTATION MARK -> APOSTROPHE
    '‘': "'",  # LEFT SINGLE QUOTATION MARK -> APOSTROPHE
    '”': '"',  # RIGHT DOUBLE QUOTATION MARK -> QUOTATION MARK
    '“': '"',  # LEFT DOUBLE QUOTATION MARK -> QUOTATION MARK
}


def _finalize_text(text: str) -> str:
    """NFC-normalize and defensively straighten any typographic quotes.
    Shared final step for both the plain-text and Lexware pipelines."""
    for curly, straight in _TYPOGRAPHIC_QUOTES.items():
        text = text.replace(curly, straight)
    return unicodedata.normalize('NFC', text)


def convert_line_to_plain_unicode(line: str, warnings: Counter) -> str:
    line = preprocess_line(line, warnings)
    line = extract_and_convert_altfont(line, warnings)
    return line


# =====================================================================
# 4. PLAIN-TEXT PIPELINE (front/back matter AND body files)
# =====================================================================

def convert_file_to_plain_text(path: str, warnings: Counter) -> str:
    raw = open(path, 'rb').read()
    raw = mask_high_bit(raw)
    raw = strip_trailing_ctrlz(raw)
    text = raw.decode('ascii', errors='replace')
    lines = split_logical_lines(text)
    out_lines = []
    for line in lines:
        if is_dot_command(line):
            continue
        out_lines.append(convert_line_to_plain_unicode(line, warnings))
    # collapse 3+ blank lines down to a single blank line (page-break debris)
    result = '\n'.join(out_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    # normalize: composed base+diacritic sequences from the citation-form
    # backspace mechanism (see convert_lahu) may not be in NFC even though
    # the static LAHU_UNICODE table entries are; do it once, here, for the
    # whole file so output is always in one canonical, consistent form.
    return _finalize_text(result.strip('\n') + '\n')


# =====================================================================
# 5. LEXWARE PIPELINE (135 main-body BASE.* files only)
#    A close port of LahuParse.pl's classification loop. Markers \x17
#    and \x11 are threaded through (re-wrapped around converted text)
#    exactly as the original did, and only consumed once a field is
#    finally extracted by the classifier below.
# =====================================================================

BAND_HW = '.hw'
BAND_SHW = '..hw'
BAND_POS = 'pos'
BAND_LOAN = 'ld'
BAND_BZ = 'bz'
BAND_NOTE = 'no'
BAND_GL = 'gl'
BAND_EX = 'ex'
BAND_XX = 'xx'
BAND_ERR = 'err'
BAND_DIVIDER = 'divider'


class LexEntry:
    """Accumulates the band-tagged lines for the file currently being
    processed, mirroring LahuParse.pl's direct `print OUT` calls."""

    def __init__(self):
        self.bands = []

    def emit(self, band, text):
        self.bands.append('%s\t%s' % (band, text))

    def as_text(self):
        return '\n'.join(self.bands) + '\n'


def _remove_subscripting(line: str) -> str:
    # while (/^([^\x12]*)\x12([^\x11]*)\x11(.*)$/) { $_ = $1.$2.$3 }
    pat = re.compile(r'^([^\x12]*)\x12([^\x11]*)\x11(.*)$', re.S)
    while True:
        m = pat.match(line)
        if not m:
            return line
        line = m.group(1) + m.group(2) + m.group(3)


def _transliterate_altfont_runs(line: str, warnings: Counter) -> str:
    """Convert every \\x17...\\x11 run's DL-ASCII content to Unicode, but
    RE-WRAP the result in the same \\x17/\\x11 markers (they're needed as
    structural anchors by the classifier below)."""
    out = []
    rest = line
    while rest:
        m = re.match(r'^([^\x17]*)\x17([^\x11]*)\x11(.*)$', rest, re.S)
        if not m:
            out.append(rest)
            break
        plain, lahu, rest = m.group(1), m.group(2), m.group(3)
        out.append(plain)
        out.append('\x17' + convert_lahu(lahu, warnings) + '\x11')
    return ''.join(out)


_TONE_TR = str.maketrans('1234567890', ''.join(SUPERSCRIPT_DIGITS[d] for d in '1234567890'))


def _transliterate_superscripts(line: str) -> str:
    out = []
    rest = line
    while rest:
        m = re.match(r'^([^\x14]*)\x14([^\x14]*)\x14(.*)$', rest, re.S)
        if not m:
            out.append(rest)
            break
        plain, tones, rest = m.group(1), m.group(2), m.group(3)
        out.append(plain)
        out.append(tones.translate(_TONE_TR))
    return ''.join(out)


def parse_base_file_to_lexware(path: str, warnings: Counter):
    """Port of the main `while (<BASE>)` loop in LahuParse.pl. Returns
    (lexware_text, log_lines)."""
    raw = open(path, 'rb').read()
    raw = mask_high_bit(raw)
    raw = strip_trailing_ctrlz(raw)
    text = raw.decode('ascii', errors='replace')
    lines = split_logical_lines(text)

    out = []          # band-tagged output lines
    log = []          # parse-diagnostic lines (like LahuParse.pl's LOG file)

    gloss = ''
    prev_gloss = ''
    note = ''
    incomplete = False
    lineno = 0

    def gloss_purge():
        nonlocal gloss, prev_gloss
        if gloss:
            g = gloss
            if re.match(r'^([Ii]bid|[Ii]d)\.(.*)$', g):
                m = re.match(r'^(?:[Ii]bid|[Ii]d)\.(.*)$', g)
                g = prev_gloss + ' ' + m.group(1)
            g = re.sub(r' +', ' ', g)
            g = g.replace('\x1f ', '')
            g = re.sub(r'[\x11\x12\x17]', '', g)
            out.append(BAND_GL + '\t' + g)
            prev_gloss = g
        gloss = ''

    def note_purge():
        nonlocal note
        gloss_purge()
        if note:
            n = re.sub(r' +', ' ', note)
            n = n.replace('\x1f ', '')
            n = re.sub(r'[\x11\x12\x17]', '', n)
            out.append(BAND_NOTE + '\t' + n)
            note = ''

    for raw_line in lines:
        lineno += 1
        line = raw_line
        if line == '':
            continue
        if is_dot_command(line):
            continue

        line = _remove_subscripting(line)

        # partial (cross-line) Lahu run bookkeeping
        if incomplete:
            m = re.match(r'^(\s*)(\S)(.*)$', line, re.S)
            if m:
                line = m.group(1) + '\x17' + m.group(2) + m.group(3)
            incomplete = False
        m = re.match(r'^(.*)\x17([^\x11]*)$', line, re.S)
        if m:
            line = m.group(1) + '\x17' + m.group(2) + '\x11'
            incomplete = True

        line = _transliterate_altfont_runs(line, warnings)
        line = _transliterate_superscripts(line)

        # ---- merge multiple Lahu runs per line (see LahuParse.pl) ----
        if (line.count('\x17') >= 1 and line.count('\x11') >= 2
                and not re.match(r'^\s*/', line) and not note):
            lahu_end = line.rfind('\x11')
            if lahu_end <= 35:
                m = re.match(r'^([^\x17]*)\x17(.*)\x11([^\x11]*)$', line, re.S)
                if m:
                    left, middle, right = m.group(1), m.group(2), m.group(3)
                    middle = middle.replace('\x17', '').replace('\x11', '')
                    line = left + '\x17' + middle + '\x11' + right
            else:
                m = re.search(r'( / )(.*)', line, re.S)
                m2 = re.search(r'(\x11[^\x17]*)(  \([^)]*\) )(.*)', line, re.S)
                m3 = re.search(r'(\S   )(.*)', line, re.S)
                if m:
                    lxm, delim, gls = line[:m.start()], m.group(1), m.group(2)
                    mm = re.match(r'^([^\x17]*)\x17(.*)\x11([^\x11]*)$', lxm, re.S)
                    if mm:
                        left, middle, right = mm.group(1), mm.group(2), mm.group(3)
                        middle = middle.replace('\x17', '').replace('\x11', '')
                        line = left + '\x17' + middle + '\x11' + right + delim + gls
                elif m2:
                    lxm, delim, gls = line[:m2.start()] + m2.group(1), m2.group(2), m2.group(3)
                    mm = re.match(r'^([^\x17]*)\x17(.*)\x11([^\x11]*)$', lxm, re.S)
                    if mm:
                        left, middle, right = mm.group(1), mm.group(2), mm.group(3)
                        middle = middle.replace('\x17', '').replace('\x11', '')
                        line = left + '\x17' + middle + '\x11' + right + delim + gls
                elif m3:
                    lxm, delim, gls = line[:m3.start()], m3.group(1), m3.group(2)
                    mm = re.match(r'^([^\x17]*)\x17(.*)\x11([^\x11]*)$', lxm, re.S)
                    if mm:
                        left, middle, right = mm.group(1), mm.group(2), mm.group(3)
                        middle = middle.replace('\x17', '').replace('\x11', '')
                        line = left + '\x17' + middle + '\x11' + right + delim + gls

        rec = line  # preserved original (marker-bearing) line, for xx/log output
        plain_for_log = re.sub(r'[\x11\x12\x14\x17]', '', rec)

        # "PUT x HERE" letter-divider markers (the divider letter is wrapped
        # in altfont escapes even in the raw source, so it only becomes
        # plain text here, after those escapes have been stripped above).
        # Checked first/highest-priority so it can never fall through to
        # the xx/err "unknown line" classification below.
        m_divider = re.match(r'^\s*PUT (.+?) HERE\s*$', plain_for_log)
        if m_divider:
            note_purge()
            out.append(BAND_DIVIDER + '\t' + m_divider.group(1))
            continue

        # ================= line classification =================

        m_ngloss = re.match(r'^ {11,}((\d+)|([a-z]))(\. +)((?:\[[^\]]+\] +)*)(.+)$', line)
        if m_ngloss:
            bznum, bz_dot, bz_brackets, rest_gloss = (
                m_ngloss.group(1), m_ngloss.group(4), m_ngloss.group(5), m_ngloss.group(6))
            gloss_purge()
            if bz_brackets:
                out.append(BAND_BZ + '\t' + bz_brackets.strip())
            gloss = bznum + bz_dot + rest_gloss
            continue

        if gloss and re.match(r'^ {35,}(.*)', line):
            next_part = re.match(r'^ {35,}(.*)', line).group(1)
            if not re.search(r'[^-]-$', gloss):
                gloss += ' '
            gloss += next_part
            continue

        if note and re.match(r'^ +(.*)', line):
            m_end = re.match(r'^ +(.*?) */ *$', line)
            if m_end:
                note = note + ' ' + m_end.group(1)
                note_purge()
            else:
                note = note + ' ' + re.match(r'^ +(.*?) *$', line).group(1)
            continue

        if re.match(r'^\S', line):
            # ---- new headword ----
            gloss_purge()
            m_hw = re.match(r'^\x17([^\x11]*)\x11(.*)$', line, re.S)
            hw_err = None
            if m_hw:
                hw, rest = m_hw.group(1), m_hw.group(2)
            else:
                hw_err = '*** Barf! Could not extract headword. (%d) *** %s' % (lineno, plain_for_log)
                log.append(hw_err)
                hw, rest = '', line
            if out:  # blank line separates this article from the previous one
                out.append('')
            out.append(BAND_HW + '\t' + hw)
            if hw_err:
                out.append(BAND_ERR + '\t' + hw_err)
            gloss = ''
            note = ''

            m = re.match(r'^ +(\[q+\.v\.\])(.*)', rest)
            if m:
                out.append(BAND_BZ + '\t' + m.group(1))
                rest = m.group(2)
            m = re.match(r'^ +\(([^)]*)\) (.*)$', rest, re.S)
            if m:
                out.append(BAND_POS + '\t' + m.group(1))
                rest = m.group(2)
            m = re.match(r'^ +(LOAN\??) (.*)$', rest, re.S)
            if m:
                out.append(BAND_LOAN + '\t' + m.group(1))
                rest = m.group(2)
            m = re.match(r'^ *((\d+)|([a-z]))(\. +)((?:\[[^\]]+\] +)+)(.+)$', rest, re.S)
            if m:
                out.append(BAND_BZ + '\t' + m.group(5).strip())
                rest = m.group(1) + m.group(4) + m.group(6)
            else:
                m = re.match(r'^ *((?:\[[^\]]+\] +)+)(.+)$', rest, re.S)
                if m:
                    out.append(BAND_BZ + '\t' + m.group(1).strip())
                    rest = m.group(2)
            m = re.match(r'^\s*(\S.*?)\s*$', rest, re.S)
            if m:
                gloss = m.group(1)
            else:
                msg = '*** Barf! Could not extract gloss. (hw:%d) *** %s' % (lineno, plain_for_log)
                out.append(BAND_XX + '\t' + plain_for_log)
                out.append(BAND_ERR + '\t' + msg)
                log.append(msg)
            continue

        m_shw = re.match(r'^(?: {5})+([^\s/])?\x17.*(?:\([^)]*\))? +(\S.*)', line)
        if m_shw and ' /' not in line and '\x11/' not in line:
            gloss_purge()
            # NB: unanchored in the original (no leading ^) -- finds the
            # first \x17...\x11 run wherever it starts on the line.
            m = re.search(r'(\S)?\x17([^\x11]*)\x11([^(\s]*)(.*)$', line, re.S)
            shw_err = None
            if m:
                shw = (m.group(1) or '') + m.group(2) + m.group(3)
                rest = m.group(4)
            else:
                # the original silently discarded the line here (shw=rest='');
                # preserve the content instead of losing it.
                shw_err = '*** Barf! Could not extract sub-headword. (%d) *** %s' % (lineno, plain_for_log)
                log.append(shw_err)
                shw, rest = '', ''
            out.append(BAND_SHW + '\t' + shw)
            if shw_err:
                out.append(BAND_ERR + '\t' + shw_err)
                out.append(BAND_XX + '\t' + plain_for_log)
            gloss = ''
            note = ''

            m = re.match(r'^ +(\[q+\.v\.\])(.*)', rest)
            if m:
                out.append(BAND_BZ + '\t' + m.group(1))
                rest = m.group(2)
            m = re.match(r'^ +\(([^)]*)\) (.*)$', rest, re.S)
            if m:
                out.append(BAND_POS + '\t' + m.group(1))
                rest = m.group(2)
            elif re.search(r' ve *$', shw):
                out.append(BAND_POS + '\tV')
            else:
                msg = '*** Barf! No part of speech for headword %s' % shw
                log.append(msg)
                out.append(BAND_ERR + '\t' + msg)
            m = re.match(r'^ +(LOAN\??) (.*)$', rest, re.S)
            if m:
                out.append(BAND_LOAN + '\t' + m.group(1))
                rest = m.group(2)
            m = re.match(r'^ *((\d+)|([a-z]))(\. +)((?:\[[^\]]+\] +)+)(.+)$', rest, re.S)
            if m:
                out.append(BAND_BZ + '\t' + m.group(5).strip())
                rest = m.group(1) + m.group(4) + m.group(6)
            else:
                m = re.match(r'^ *((?:\[[^\]]+\] +)+)(.+)$', rest, re.S)
                if m:
                    out.append(BAND_BZ + '\t' + m.group(1).strip())
                    rest = m.group(2)
            m = re.match(r'^\s*(\S.*?)\s*$', rest, re.S)
            if m:
                gloss = m.group(1)
            else:
                msg = '*** Barf! Could not extract gloss. (shw:%d) *** %s' % (lineno, plain_for_log)
                out.append(BAND_XX + '\t' + plain_for_log)
                out.append(BAND_ERR + '\t' + msg)
                log.append(msg)
            continue

        m_ex = re.match(r'^(?: {5})+(\S)?\x17(.*) (?:\x11)?/', line)
        if m_ex:
            gloss_purge()
            # NB: unanchored in the original.
            m = re.search(r'(\S)?\x17([^\x11]*)\x11([^/]*)', line, re.S)
            if m:
                ex = (m.group(1) or '') + m.group(2) + m.group(3)
                out.append(BAND_EX + '\t' + ex)
            else:
                msg = '*** Barf! Could not extract example. (ex:%d) *** %s' % (lineno, plain_for_log)
                out.append(BAND_XX + '\t' + plain_for_log)
                out.append(BAND_ERR + '\t' + msg)
                log.append(msg)

            m = re.search(r'\x11 +\(([^)]*)\) */? *(.*)', line, re.S)
            if m:
                out.append(BAND_POS + '\t' + m.group(1))
                gloss = m.group(2)
            else:
                m = re.search(r'\x11 */ +(.*)', line, re.S)
                if m:
                    gloss = m.group(1)
                else:
                    msg = '*** Barf! Could not extract gloss. (ex:%d) *** %s' % (lineno, plain_for_log)
                    out.append(BAND_XX + '\t' + plain_for_log)
                    out.append(BAND_ERR + '\t' + msg)
                    log.append(msg)
            continue

        if re.match(r'^ +/', line):
            gloss_purge()
            m = re.match(r'^ +/ *(.*?) */ *$', line, re.S)
            if m:
                note = m.group(1)
                note_purge()
            else:
                m = re.match(r'^ +/ *(.*?) *$', line, re.S)
                note = m.group(1) if m else ''
            continue

        # unknown -- but first check for the single most common shape:
        # an indented line with no Lahu-script text of its own (no
        # altfont-run marker at all), immediately following a `gl` band.
        # This is almost always the tail of a gloss that wrapped across
        # more physical lines than the classifier's own gloss-in-
        # progress window recognized (typically because the *previous*
        # line had already been classified as something else -- e.g. an
        # example -- closing that window early). Rather than losing
        # this into an xx/err pair, merge it onto the most recently
        # emitted `gl` band's text and log a warning instead of an
        # inline error; see README.md.
        # NB: the natural-looking check "is out[-1] already a gl band" is
        # wrong in the common case -- a gloss being built up across
        # several physical lines lives in the `gloss` accumulator
        # variable and is not flushed to `out` until the *next*
        # recognized band-line triggers gloss_purge(). So by the time an
        # unrecognized continuation line like this one is reached, the
        # gloss it continues is usually still sitting unflushed in
        # `gloss`, not yet in `out` at all. Append to that buffer first;
        # only fall back to patching the last flushed `gl` band in `out`
        # if there is no gloss currently in progress (e.g. a `no` line
        # intervened and flushed it already).
        m_cont = re.match(r'^(\s+)(\S.*)$', line, re.S)
        if m_cont and '\x17' not in line and (gloss or (out and out[-1].startswith(BAND_GL + '\t'))):
            cont_text = re.sub(r'[\x11\x12\x14\x17]', '', m_cont.group(2)).strip()
            cont_text = re.sub(r' +', ' ', cont_text)
            if gloss:
                sep = '' if re.search(r'[^-]-$', gloss) else ' '
                gloss = gloss + sep + cont_text
            else:
                prev_band, prev_text = out[-1].split('\t', 1)
                sep = '' if re.search(r'[^-]-$', prev_text) else ' '
                out[-1] = prev_band + '\t' + prev_text + sep + cont_text
            warn_msg = 'Merged as gloss continuation (%d): %s' % (lineno, plain_for_log)
            log.append(warn_msg)
            continue

        # unknown
        note_purge()
        msg = 'Unknown line (%d): %s' % (lineno, plain_for_log)
        out.append(BAND_XX + '\t' + plain_for_log)
        out.append(BAND_ERR + '\t' + msg)
        log.append(msg)

    gloss_purge()

    entry = LexEntry()
    entry.bands = out
    return _finalize_text(entry.as_text()), log


# =====================================================================
# 6. DRIVER
# =====================================================================

# Files that are pure printer/font binary resources, not prose -- running
# the text pipeline on them would just produce noise. See module
# docstring / conversion notes.
#   LAHU.CHR                     Intel-HEX encoded downloadable font bitmap
#   LQLAHU.D1%, LQLAHUBD.H1%,
#   LQLAHUEL.H1%                 binary Epson LQ-1500 downloadable font files
# NOTE: HEADER is NOT excluded, even though it's mostly WordStar
# dot-commands plus a trailing raw binary/garbage blob (looks like a stray
# CP/M directory-entry fragment) once those are dropped -- it still goes
# through the normal pipeline like every other file; whatever undecodable
# bytes remain in that trailing fragment come out as U+FFFD replacement
# characters rather than being silently omitted.
NON_PROSE_FILES = {'LAHU.CHR', 'LQLAHU.D1%', 'LQLAHUBD.H1%', 'LQLAHUEL.H1%'}


def process_plaintext_dir(src_dir, dst_dir, warnings, report):
    os.makedirs(dst_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f)))
    for fn in files:
        if fn in NON_PROSE_FILES:
            report.append('SKIPPED (not prose -- font/binary resource): %s' % fn)
            continue
        src = os.path.join(src_dir, fn)
        try:
            text = convert_file_to_plain_text(src, warnings)
        except Exception as e:
            report.append('ERROR converting %s: %s' % (src, e))
            continue
        dst = os.path.join(dst_dir, fn + '.txt')
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(text)
    return files


def process_lexware_base(src_dir, plaintext_dst, lexware_dst, warnings, report):
    os.makedirs(plaintext_dst, exist_ok=True)
    os.makedirs(lexware_dst, exist_ok=True)
    files = sorted(f for f in os.listdir(src_dir) if f.startswith('BASE.'))
    for fn in files:
        src = os.path.join(src_dir, fn)
        try:
            text = convert_file_to_plain_text(src, warnings)
            with open(os.path.join(plaintext_dst, fn + '.txt'), 'w', encoding='utf-8') as f:
                f.write(text)
        except Exception as e:
            report.append('ERROR (plaintext) converting %s: %s' % (src, e))

        try:
            lex_text, log_lines = parse_base_file_to_lexware(src, warnings)
            corename = fn[len('BASE.'):]
            with open(os.path.join(lexware_dst, 'lex.' + corename + '.txt'), 'w', encoding='utf-8') as f:
                f.write(lex_text)
            if log_lines:
                with open(os.path.join(lexware_dst, 'LOG.' + corename + '.txt'), 'w', encoding='utf-8') as f:
                    f.write('\n'.join(log_lines) + '\n')
        except Exception as e:
            report.append('ERROR (lexware) converting %s: %s' % (src, e))
    return files


def main():
    # base_dir is the project root (originals/ and generated/ are its
    # siblings); see README.md for the full originals/generated/src
    # layout. Inputs are read from originals/, outputs written to
    # generated/, which keeps every derived file out of the raw source
    # material and out of version control (generated/ is gitignored).
    base_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    other_src = os.path.join(base_dir, 'originals', 'DLOtherFiles')
    base_src = os.path.join(base_dir, 'originals', 'DLWordStarFiles', 'base')

    other_dst = os.path.join(base_dir, 'generated', 'DLOtherFiles-plaintext')
    base_plain_dst = os.path.join(base_dir, 'generated', 'DLWordStarFiles', 'base-plaintext')
    base_lex_dst = os.path.join(base_dir, 'generated', 'DLWordStarFiles', 'base-lexware')

    warnings = Counter()
    report = []

    print('Converting front/back matter: %s -> %s' % (other_src, other_dst))
    other_files = process_plaintext_dir(other_src, other_dst, warnings, report)
    print('  %d files converted' % len(other_files))

    print('Converting main body: %s' % base_src)
    print('  plain text -> %s' % base_plain_dst)
    print('  lexware    -> %s' % base_lex_dst)
    base_files = process_lexware_base(base_src, base_plain_dst, base_lex_dst, warnings, report)
    print('  %d files converted' % len(base_files))

    report_path = os.path.join(base_dir, 'generated', 'conversion-report.log')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('DL conversion report\n')
        f.write('=' * 60 + '\n\n')
        if report:
            f.write('Notes / errors:\n')
            for r in report:
                f.write('  ' + r + '\n')
            f.write('\n')
        f.write('Stripped / unknown character tally (all files combined):\n')
        for k, v in warnings.most_common():
            f.write('  %6d  %s\n' % (v, k))
    print('\nWrote %s (%d distinct warning types)' % (report_path, len(warnings)))


if __name__ == '__main__':
    main()
