#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
process_front_and_back_matter.py -- render the recovered front/back-matter
documents from originals/DLOtherFiles/ (dedication, list of plates,
acknowledgments, symbols & abbreviations, bibliography, appendices, ...)
into LaTeX, so they can be \\input from src/latex/lahu-master.tex alongside
the dictionary body.

WHICH FILES, AND IN WHAT ORDER
-------------------------------
originals/DLOtherFiles/CONTENTS.TXE is a free-text note the author (or
KWW, who computerized the *Dictionary*) left for whoever assembled the
1988 camera-ready copy -- production instructions for a human typesetter,
not a machine-readable manifest, and not exhaustive: it describes the
Press-supplied preliminaries (false title, map, title page, copyright),
the dedication, and the printed Table of Contents' own entries (List of
Plates, Acknowledgments, Symbols and Abbreviations, Introduction,
Bibliography, Plates), but omits several files that are nonetheless real,
finished-enough content -- DIALIST.TXA, LINGTERM.TXA, and BIRDLIST.TXC,
each headed "APPENDIX #" (or similar) in the original with the appendix
NUMBER left blank, i.e. genuinely written but never assigned a final
position by the author. Per the project owner (see conversation), these
are included as back-matter appendices, and CONTENTS.TXE is *not*
over-interpreted as a strict inclusion/exclusion list.

The Introduction essay CONTENTS.TXE describes (sections 1.0-4.5: history
of the project, the Lahu people/language, transcription, entry format)
is not present anywhere in this archive and cannot be reconstructed here.

Excluded, and why (see also the module docstring in dl_convert.py):
  ABBREVS.TXB   Superseded single-column draft of ABBREVS2.TXE, itself
                marked "REFORMAT INTO DOUBLE COLUMNS AFTER PROOFING --KWW".
  BACKMATT.TXA  An internal planning wishlist for back matter never
                finished ("Personal names -- glean from AW's files...",
                etc.), not reader-facing content.
  LAHUDICT.TXT  An internal memo about the DL-ASCII keystroke scheme
                itself, not *Dictionary* content.
  HEADER, LAHU.CHR, LQLAHU.D1%, LQLAHUBD.H1%, LQLAHUEL.H1%
                Binary printer font / character-ROM / footer-tag data,
                no prose at all (HEADER is already used for the printed
                running-footer collation sequence -- see lahu_collate.py).
  LAHUPREF.TXA  Just the heading "PREFACE IN LAHU" with no body text
                beneath it -- per the project owner, still included, as
                a near-blank page (so a reader who goes looking for it,
                per the running head, finds an explicit placeholder
                rather than a silent gap).

FRONT/BACK MATTER ENCODING BUG FOUND AND FIXED HERE
-----------------------------------------------------
dl_convert.py's plain-text pipeline (convert_file_to_plain_text) converts
one physical line at a time. Several of these files have an ALTFONT run
(\\x17...\\x11 or \\x01...\\x0e) that is opened on one physical line and
not closed until several blank-line-separated paragraphs later (verified:
FRONTISP.TXE, PLATES.TXE, ACKNOWL.TXE, BIBLIOG.TXE, and ABBREVS2.TXE all
have this). Per-line processing only converts the first line of such a
run and leaves the rest as raw, unconverted DL-ASCII. This script instead
converts each file as a single whole-file pass (see
_convert_whole_file_preserving_layout below) so a multi-line run comes
out correctly regardless of where it happens to wrap. This is a
front/back-matter-only fix: it does not touch dl_convert.py or change
main dictionary body output (the 135 BASE.* files were checked and don't
have this pattern -- see README.md).

LAYOUT
------
The original was typed on a fixed-width font, with layout (tables,
aligned columns, right-flush captions) done using runs of literal spaces
-- there is no markup to recover it from. Each document below is
rendered in one of three modes, chosen per file by inspection:

  poem       Centered, one source line per output line, exactly as
             typed (no reflow). For the dedication and the (near-empty)
             Lahu preface stub.
  prose      Blank-line-delimited paragraphs are reflowed into normal
             justified paragraphs (wrapped lines rejoined, runs of
             spaces collapsed to one) -- for genuine running prose
             (Acknowledgments) where the original line wrap was just an
             artifact of the typewriter's margin, not meaningful layout.
  table      Rendered verbatim in a monospaced font with the original
             spacing and line breaks preserved exactly (\\ttfamily +
             \\obeyspaces\\obeylines) -- for anything using space-aligned
             columns (lists, glossaries, the abbreviation tables, the
             bibliography's own author/citation hanging layout, etc.),
             where collapsing whitespace would destroy the alignment
             that IS the content's structure.

Output
------
  generated/latex/frontmatter/NN-slug.tex   (one per document, generated)
  generated/latex/backmatter/NN-slug.tex    (one per document, generated)
  generated/latex/frontmatter-pre-toc.tex   (\\input list: before toc.tex)
  generated/latex/frontmatter-post-toc.tex  (\\input list: after toc.tex)
  generated/latex/backmatter.tex            (\\input list: after the body)

These three "-pre-toc"/"-post-toc"/"backmatter" files are themselves
generated (not hand-authored) -- they are simply an ordered list of
\\input and \\clearpage commands, one per document in this script's
manifest below, which is the single source of truth for both content
and order. \\input them from src/latex/lahu-master.tex (see that file's
own comments for where).

Usage (paths relative to the project root):
    python3 src/process_front_and_back_matter.py .
"""
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dl_convert as dlc

# ---------------------------------------------------------------------
# Whole-file DL-ASCII -> Unicode conversion, layout-preserving
# ---------------------------------------------------------------------

# dl_convert.convert_lahu() (reused unmodified below) rejects any
# character it doesn't recognize -- including a literal newline, which
# never appears inside a call to it in dl_convert.py itself (that
# pipeline only ever calls it on ALTFONT runs already isolated to a
# single physical line). Since we deliberately join whole-file text
# (real newlines and all) into one string before extracting ALTFONT runs
# -- precisely so a run that spans several physical lines converts
# correctly instead of only its first line -- a converted run may now
# legitimately contain embedded newlines. Registering '\n' as an
# additional pass-through character (once, here) is the smallest way to
# teach the shared, unmodified convert_lahu() that a newline inside a
# run is just a line break, not unrecognized Lahu content. This mutates
# dl_convert's module-level set only in this script's own process; the
# dl_convert.py source file itself is untouched, and running dl_convert.py
# on its own is unaffected.
dlc.UNCHANGED_CHARS.add('\n')



# Every one of these files' very first surviving line (right after the
# dot-command print-setup preamble is stripped) is a single bare ALTFONT
# toggle byte with nothing else on the line -- e.g. FRONTISP.TXE,
# PLATES.TXE, ACKNOWL.TXE, BIBLIOG.TXE, and ABBREVS2.TXE all start this
# way. dl_convert.py's per-line pipeline already treats this safely: a
# lone open with no close before end-of-line converts to nothing and
# the next line starts fresh (see extract_and_convert_altfont: it still
# calls convert_lahu on an empty slice and advances to end-of-line).
# But the moment lines are joined into one string (needed for the
# genuine multi-line runs this script exists to fix -- see module
# docstring), that same lone open marker instead runs forward looking
# for the FIRST close ANYWHERE LATER IN THE WHOLE FILE, silently
# swallowing everything in between -- confirmed to garble large stretches
# of ordinary English prose in ACKNOWL.TXE through the Lahu substitution
# table before this filter was added. Since this exact single-byte,
# nothing-else-on-the-line pattern is what the old per-line pipeline
# was already safely no-op'ing on, dropping such lines up front (before
# joining) preserves that same safe behavior while still letting the
# genuine multi-line runs (which always have real content alongside
# their open/close markers) join and convert correctly.
_LONE_TOGGLE_LINE_RE = re.compile(r'^[\x17\x01\x11\x0e]$')


# WordStar's soft/optional line-wrap hyphen (0x1F -- see dl_convert.py's
# module docstring) directly followed by a line break marks a word that
# was simply split at the print margin, mid-word, with no real hyphen
# intended (e.g. "many indi\x1f\r\nviduals" -> "individuals"). Elsewhere
# on a line, dl_convert.py's preprocess_line already turns a literal
# 0x1F into an em dash; at end-of-line it strips it with nothing left
# behind, which is correct for a single physical line in isolation, but
# this script reflows wrapped lines back into running paragraphs (see
# render_prose/render_bibliography), and naively rejoining "indi" and
# "viduals" with the usual single space would leave "indi viduals"
# instead of "individuals". Splicing the break out at the raw-text
# level, before any line-by-line processing, fixes this regardless of
# which rendering mode the document ends up using (harmless no-op for
# poem/table documents, where this word-wrap artifact doesn't occur --
# verified across the corpus; see conversation notes).
# Also eat the following line's leading indentation: that whitespace is
# just print-time continuation padding for the wrapped word, not real
# content (confirmed against DIALIST.TXA's "many Yun\x1f\r\n            nanese
# loanwords" -- without this, splicing left 23 spaces sitting inside the
# middle of "Yunnanese").
_SOFT_WRAP_HYPHEN_EOL_RE = re.compile(r'\x1f\n[ \t]*')


def _convert_whole_file_preserving_layout(path, warnings):
    """Like dl_convert.convert_file_to_plain_text, but processes the
    file's ENTIRE text as one string rather than one physical line at a
    time, so an ALTFONT run spanning multiple (often blank-line-
    separated) physical lines converts correctly. See module docstring
    and the _LONE_TOGGLE_LINE_RE comment above for the one safety filter
    this requires that the per-line pipeline didn't need."""
    raw = open(path, 'rb').read()
    raw = dlc.mask_high_bit(raw)
    raw = dlc.strip_trailing_ctrlz(raw)
    text = raw.decode('ascii', errors='replace')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = _SOFT_WRAP_HYPHEN_EOL_RE.sub('', text)
    lines = text.split('\n')
    kept = []
    for l in lines:
        if dlc.is_dot_command(l):
            continue
        l = dlc.preprocess_line(l, warnings)
        if _LONE_TOGGLE_LINE_RE.match(l.strip()):
            continue
        kept.append(l)
    joined = '\n'.join(kept)
    converted = dlc.extract_and_convert_altfont(joined, warnings)
    converted = re.sub(r'\n{3,}', '\n\n', converted)
    return dlc._finalize_text(converted.strip('\n') + '\n')


# ---------------------------------------------------------------------
# Editorial-only lines to drop everywhere (production notes to whoever
# assembled the camera-ready copy, never meant for the printed page) --
# see the examples in the module docstring above. Matched after
# stripping surrounding whitespace.
# ---------------------------------------------------------------------
_GENERIC_DROP_PATTERNS = [
    re.compile(r'^<<.*>>$'),                 # "<< FILENAME  Revision of ... >>"
    re.compile(r'^//.*//$'),                 # "//Appendix #   //" (never assigned)
    re.compile(r'^APPENDIX\s*#.*$', re.I),   # "APPENDIX #__"
    re.compile(r'^\\+.*\\+$'),               # "\ALSO TO BE INTERALPHABETIZED...\"
]


def _drop_editorial_lines(text):
    out = []
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped and any(p.match(stripped) for p in _GENERIC_DROP_PATTERNS):
            continue
        out.append(line)
    return '\n'.join(out)


def _drop_named_lines(text, exact_lines):
    """Drop any line whose whitespace-collapsed content exactly matches
    one of exact_lines (also whitespace-collapsed) -- used to remove a
    document's own embedded title when we're printing our own heading
    for it instead (see the manifest's 'title' vs the file's own
    centered ALL-CAPS heading line)."""
    targets = {' '.join(t.split()) for t in exact_lines}
    out = []
    for line in text.split('\n'):
        norm = ' '.join(line.split())
        if norm in targets:
            continue
        out.append(line)
    return '\n'.join(out)


# ---------------------------------------------------------------------
# LaTeX escaping + a small markdown-ish inline-markup pass. Ports the
# exact same escape rules/order as lahu-latex.xsl's latex-escape
# template (see that file) so front/back matter and the dictionary body
# render special characters identically.
# ---------------------------------------------------------------------

def latex_escape(text):
    text = text.replace('\\', '\\textbackslash{}')
    text = text.replace('&', '\\&')
    text = text.replace('%', '\\%')
    text = text.replace('$', '\\$')
    text = text.replace('#', '\\#')
    text = text.replace('_', '\\_')
    text = text.replace('{', '\\{')
    text = text.replace('}', '\\}')
    text = text.replace('^', '\\textasciicircum{}')
    text = text.replace('~', '\\textasciitilde{}')
    text = text.replace("'", '\\textquotesingle{}')
    text = text.replace('"', '\\textquotedbl{}')
    return text


_MD_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_MD_ITALIC_RE = re.compile(r'\*(.+?)\*')


def markup_and_escape(text):
    """dl_convert.py's plain-text pipeline renders WordStar bold/italic
    toggle bytes as **bold**/*italic* markdown (see its module
    docstring). Convert those to \\textbf{}/\\textit{} (escaping their
    contents first), then latex-escape whatever's left. NB: WordStar
    underline (which the same pipeline renders as _underline_) is
    deliberately NOT interpreted as markup here: several of these files
    use runs of literal underscores as a fill-in-the-blank placeholder
    (e.g. LINGTERM.TXA's "kham khunsàp ____________"), which would be
    misread as a single giant underline span. Bare underscores are just
    escaped like any other character instead.
    """
    placeholders = []

    def stash(snippet):
        placeholders.append(snippet)
        return '\x00%d\x00' % (len(placeholders) - 1)

    text = _MD_BOLD_RE.sub(lambda m: stash('\\textbf{%s}' % latex_escape(m.group(1))), text)
    text = _MD_ITALIC_RE.sub(lambda m: stash('\\textit{%s}' % latex_escape(m.group(1))), text)
    text = latex_escape(text)
    text = re.sub(r'\x00(\d+)\x00', lambda m: placeholders[int(m.group(1))], text)
    return text


# ---------------------------------------------------------------------
# Per-mode renderers. Each takes the already-converted, editorial-line-
# stripped Unicode text and returns a LaTeX body string (no page
# break/title -- render_document adds those).
# ---------------------------------------------------------------------

def render_poem(text):
    out = ['\\begin{center}']
    first_stanza = True
    for para in re.split(r'\n\s*\n', text.strip('\n')):
        lines = [l for l in para.split('\n') if l.strip()]
        if not lines:
            continue
        if not first_stanza:
            out.append('\\\\[1.5em]')
        first_stanza = False
        out.append(' \\\\\n'.join(markup_and_escape(l.strip()) for l in lines))
    out.append('\\end{center}')
    return '\n'.join(out)


def render_prose(text):
    out = []
    for para in re.split(r'\n\s*\n', text.strip('\n')):
        joined = ' '.join(para.split())
        if not joined:
            continue
        out.append(markup_and_escape(joined))
    return '\n\n'.join(out)


def render_table(text):
    """Monospace, exact-layout rendering. \\obeyspaces alone does NOT
    preserve a line's LEADING spaces -- TeX's line-reading tokenizer
    skips leading spaces on every physical source line regardless of
    \\obeyspaces's catcode change, which only affects how a space
    token behaves once read, not whether one is skipped in the first
    place (this is what \\obeylines is really for: it makes the
    end-of-line character itself active, which sidesteps that
    leading-space-skip entirely). Rather than \\obeylines's default
    (which ends each line with \\par, starting a brand new paragraph
    per line -- not what we want here), this defines the active
    end-of-line character as \\\\ instead, confirmed by a standalone
    test compile (see conversation notes) to preserve both leading
    indentation and internal multi-space runs exactly, without the
    "There's no line here to end" error two consecutive blank lines
    would otherwise cause (avoided by never emitting two blank lines
    in a row -- _convert_whole_file_preserving_layout already collapses
    3+ newlines to one blank line -- and by replacing any blank line
    with \\strut, an invisible full-height box, so \\\\ never fires
    with literally nothing typeset since the previous one).

    One more wrinkle found by compiling the real corpus: \\\\ itself
    takes an OPTIONAL [<length>] argument, so a line whose ORIGINAL
    text happens to start with a literal '[' (several of these
    documents use bracketed editorial asides, e.g. DIALIST.TXA's
    "[Letter from David Bradley ... by dialect group.]") gets its
    forced linebreak parsed as "\\\\[Letter from ... group.]", with
    everything up to the next ']' fed to TeX as a bogus dimension --
    confirmed to throw 'Missing number'/'Illegal unit of measure' at
    exactly that spot. \\\\\\relax (a no-op \\relax right after the
    linebreak) blocks that lookahead, matching the standard fix for
    this well-known LaTeX gotcha."""
    lines = text.strip('\n').split('\n')
    escaped = ['\\strut' if l.strip() == '' else markup_and_escape(l) for l in lines]
    body = '\n'.join(escaped)
    return (
        '\\begingroup\n'
        '\\footnotesize\\ttfamily\\obeyspaces\\noindent\n'
        '\\catcode`\\^^M=\\active%\n'
        '\\def^^M{\\\\\\relax}%\n'
        + body + '%\n'
        '\\endgroup'
    )


_BIBLIO_SECTION_HEADS = {
    ' '.join(h.split()).upper() for h in (
        'I.  WORKS ON THE LAHU LANGUAGE AND PEOPLE',
        'II.  WORKS WRITTEN IN LAHU',
        'III.  WORKS CONSULTED IN PREPARING THIS DICTIONARY',
    )
}


def render_bibliography(text):
    """BIBLIOG.TXE is genuinely two different layouts back to back: a
    space-aligned code table of journal/monograph-series and individual-
    work abbreviations, followed by three roman-numeral-headed sections
    of ordinary author/year citations (each a blank-line-delimited block
    -- see the sample in the module docstring's discussion). Render the
    first part like any other table; reflow each citation block in the
    second part into a hanging-indent paragraph (matching how the
    dictionary body itself formats hanging entries -- see \\headword's
    \\hangindent in lahu-master.tex), except the three section headers
    themselves, which get their own bold heading line instead."""
    lines = text.strip('\n').split('\n')
    split_at = None
    target = ' '.join('I.  WORKS ON THE LAHU LANGUAGE AND PEOPLE'.split())
    for i, l in enumerate(lines):
        if ' '.join(l.split()).upper() == target:
            split_at = i
            break
    if split_at is None:
        # Structure not found (shouldn't happen -- fall back to a plain table
        # rather than silently dropping the second half of the bibliography).
        return render_table(text)

    table_part = '\n'.join(lines[:split_at])
    entries_part = '\n'.join(lines[split_at:])

    out = [render_table(table_part), '\\vspace{1em}']
    for para in re.split(r'\n\s*\n', entries_part.strip('\n')):
        block_lines = [l for l in para.split('\n') if l.strip()]
        if not block_lines:
            continue
        joined = ' '.join(' '.join(block_lines).split())
        if joined.upper() in _BIBLIO_SECTION_HEADS:
            out.append('\\vspace{0.8em}\\noindent\\textbf{%s}\\vspace{0.4em}'
                        % markup_and_escape(joined))
            continue
        out.append(
            '\\par\\leftskip=0pt\\hangindent=1.5em\\hangafter=1\\noindent '
            + markup_and_escape(joined)
        )
    return '\n'.join(out)


_RENDERERS = {
    'poem': render_poem,
    'prose': render_prose,
    'table': render_table,
    'bibliography': render_bibliography,
}


# ---------------------------------------------------------------------
# Manifest: the single source of truth for which files are included,
# their order, display title, rendering mode, and which of the file's
# own embedded heading lines to drop (because we print 'title' as a
# proper LaTeX heading instead). See the module docstring for the
# reasoning behind each inclusion/exclusion/ordering decision, and
# src/front-back-matter-order.csv for the reviewed, approved ordering
# this manifest implements (each entry's 'label' below is the same
# string src/latex/toc.tex's \tocline calls use via \pageref{toc:...},
# so the two files must be kept in sync by hand if either changes).
#
# Each entry is a dict with:
#   kind    'file' (rendered from an originals/DLOtherFiles/ file) or
#           'placeholder' (synthetic -- no surviving source; see the
#           Introduction entry below)
#   label   used for \label{toc:LABEL} / \pageref{toc:LABEL} in toc.tex
#   filename, mode, drops   as before (file entries only)
#   title, body             as appropriate
# ---------------------------------------------------------------------

def _file_entry(filename, title, mode, drops, label):
    return {'kind': 'file', 'filename': filename, 'title': title,
            'mode': mode, 'drops': drops, 'label': label}


# The Introduction to the Dictionary (CONTENTS.TXE's own outline, section
# 2.2 aside) has no surviving text anywhere in originals/DLOtherFiles/ --
# confirmed by grepping every front/back-matter file for each section's
# distinctive language (genetic position, Sino-Tibetan, form-classes,
# lemmata, etc.) and finding no match. Rather than silently dropping
# these nine subsections, render one placeholder page that reproduces
# the outline from CONTENTS.TXE and marks each piece present or missing,
# so the gap is visible and navigable rather than silently absent. 2.2
# does survive (DIALIST.TXA) and gets its own real page right after.
_INTRO_OUTLINE = [
    ('1.0', 'History of the Lahu dictionary project', False),
    ('2.0', 'The Lahu people and the Lahu language', False),
    ('2.1', 'The genetic position of Lahu', False),
    ('2.2', 'Lahu dialects and cultural subdivisions', True),
    ('3.0', 'Transcription and alphabetical order of entries', False),
    ('4.0', 'Structure and format of the individual entry', False),
    ('4.1', 'Lemmata and lemmatizational dilemmas', False),
    ('4.2', 'Form-classes', False),
    ('4.3', 'Glosses', False),
    ('4.4', 'Subentries', False),
    ('4.5', 'Remarks: cross references and etymologies', False),
]


def _introduction_placeholder_entry():
    lines = ['\\clearpage', '\\thispagestyle{plain}', '\\label{toc:introduction}',
             '\\begin{center}', '{\\Large\\bfseries Introduction to the \\textit{Dictionary}}',
             '\\end{center}', '\\vspace{1em}',
             '\\textit{Only \\S 2.2 survives in the recovered source material '
             '(see the following page); \\S\\S 1.0, 2.0, 2.1, 3.0, and 4.0--4.5 '
             'are not present in any recovered file and are listed here only '
             'to preserve the original outline (from CONTENTS.TXE).}',
             '\\vspace{1em}', '', '\\begin{itemize}']
    for num, title, present in _INTRO_OUTLINE:
        mark = '' if present else ' \\textit{[not recovered]}'
        lines.append('\\item \\textbf{%s} %s%s' % (num, latex_escape(title), mark))
    lines.append('\\end{itemize}')
    return {'kind': 'placeholder', 'title': 'Introduction to the Dictionary',
            'label': 'introduction', 'body': '\n'.join(lines)}


FRONT_MATTER_PRE_TOC = [
    _file_entry('FRONTISP.TXE', 'Dedication', 'poem', [], 'dedication'),
    _file_entry('LAHUPREF.TXA', 'Preface in Lahu', 'poem',
                ['P R E F A C E    I N    L A H U'], 'preface-in-lahu'),
]

FRONT_MATTER_POST_TOC = [
    _file_entry('PLATES.TXE', 'List of Plates', 'table', ['LIST OF PLATES'],
                'list-of-plates'),
    _file_entry('ACKNOWL.TXE', 'Acknowledgments', 'prose', ['ACKNOWLEDGMENTS'],
                'acknowledgments'),
    _file_entry('SYMBOLS', 'Note on Phonetic Symbols', 'table',
                ['NOTE ON PHONETIC SYMBOLS'], 'symbols-and-abbreviations'),
    _file_entry('ABBREVS2.TXE', 'Symbols and Abbreviations', 'table',
                ['SYMBOLS and ABBREVIATIONS'], 'symbols-and-abbreviations-2'),
    _introduction_placeholder_entry(),
    # 2.2 Lahu dialects and cultural subdivisions -- confirmed match for
    # DIALIST.TXA ("The Divisions of the Lahu People") by title/content;
    # moved here from back matter (where it was misfiled as an
    # unassigned appendix) per src/front-back-matter-order.csv.
    _file_entry('DIALIST.TXA', '2.2  Lahu Dialects and Cultural Subdivisions',
                'table', ['"The Divisions of the Lahu People"'], 'intro-2-2'),
]

BACK_MATTER = [
    # Not in CONTENTS.TXE's own ToC -- each marked "Appendix #" (number
    # left blank) by the author, i.e. written but never assigned a
    # final position. Included as back matter before the Bibliography
    # per the project owner's decision; see the module docstring.
    _file_entry('LINGTERM.TXA', 'Appendix: Lahu Linguistic Terminology', 'table',
                [], 'appendix-lingterm'),
    _file_entry('BIRDLIST.TXC', 'Appendix: Vocabulary Supplement \u2014 Birdnames',
                'table', ['VOCABULARY SUPPLEMENT'], 'appendix-birdlist'),
    _file_entry('BIBLIOG.TXE', 'Bibliography', 'bibliography', ['BIBLIOGRAPHY'],
                'bibliography'),
    # CONTENTS.TXE's very last line -- must be the last section in the
    # whole book (confirmed by project owner).
    _file_entry('CAPTIONS.TXE', 'Plates', 'table', ['CAPTIONS'], 'plates'),
]


def _slug(filename):
    return re.sub(r'[^a-z0-9]+', '-', filename.lower()).strip('-')


def render_document(src_dir, entry, warnings):
    label_line = '\\label{toc:%s}\n' % entry['label']
    if entry['kind'] == 'placeholder':
        return entry['body'] + '\n'

    filename, title, mode, own_heading_drops = (
        entry['filename'], entry['title'], entry['mode'], entry['drops'])
    path = os.path.join(src_dir, filename)
    text = _convert_whole_file_preserving_layout(path, warnings)
    text = _drop_editorial_lines(text)
    if own_heading_drops:
        text = _drop_named_lines(text, own_heading_drops)
    text = re.sub(r'\n{3,}', '\n\n', text).strip('\n')
    body = _RENDERERS[mode](text)
    heading = (
        '\\clearpage\n'
        '\\thispagestyle{plain}\n'
        + label_line +
        '\\begin{center}\n'
        '{\\Large\\bfseries %s}\n'
        '\\end{center}\n'
        '\\vspace{1em}\n'
    ) % latex_escape(title)
    if not text:
        # LAHUPREF.TXA: heading only, no body content recovered.
        body = '\\vspace{2em}\\begin{center}\\textit{[No further text survives in the source.]}\\end{center}'
    return heading + body + '\n'


def write_group(base_dir, subdir, manifest, warnings, report, start_index=1):
    out_dir = os.path.join(base_dir, 'generated', 'latex', subdir)
    os.makedirs(out_dir, exist_ok=True)
    input_lines = []
    for idx, entry in enumerate(manifest, start=start_index):
        slug = _slug(entry.get('filename', entry['label']))
        out_name = '%02d-%s.tex' % (idx, slug)
        out_path = os.path.join(out_dir, out_name)
        try:
            tex = render_document(
                os.path.join(base_dir, 'originals', 'DLOtherFiles'),
                entry, warnings)
        except Exception as e:
            report.append('ERROR rendering %s: %s' % (entry.get('filename', entry['label']), e))
            continue
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(tex)
        input_lines.append('\\input{generated/latex/%s/%s}' % (subdir, out_name))
        report.append('OK %-14s -> %s/%s  (mode=%s, title=%r, label=%r)'
                       % (entry.get('filename', '(placeholder)'), subdir, out_name,
                          entry.get('mode', entry['kind']), entry['title'], entry['label']))
    return input_lines


def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    warnings = Counter()
    report = []

    pre_toc_inputs = write_group(base_dir, 'frontmatter', FRONT_MATTER_PRE_TOC, warnings, report,
                                  start_index=1)
    post_toc_inputs = write_group(base_dir, 'frontmatter', FRONT_MATTER_POST_TOC, warnings, report,
                                   start_index=1 + len(FRONT_MATTER_PRE_TOC))
    back_inputs = write_group(base_dir, 'backmatter', BACK_MATTER, warnings, report,
                               start_index=1)

    latex_dir = os.path.join(base_dir, 'generated', 'latex')
    os.makedirs(latex_dir, exist_ok=True)

    with open(os.path.join(latex_dir, 'frontmatter-pre-toc.tex'), 'w', encoding='utf-8') as f:
        f.write('%% Generated by src/process_front_and_back_matter.py -- do not edit by hand.\n')
        f.write('\n'.join(pre_toc_inputs) + '\n')

    with open(os.path.join(latex_dir, 'frontmatter-post-toc.tex'), 'w', encoding='utf-8') as f:
        f.write('%% Generated by src/process_front_and_back_matter.py -- do not edit by hand.\n')
        f.write('\n'.join(post_toc_inputs) + '\n')

    with open(os.path.join(latex_dir, 'backmatter.tex'), 'w', encoding='utf-8') as f:
        f.write('%% Generated by src/process_front_and_back_matter.py -- do not edit by hand.\n')
        f.write('\n'.join(back_inputs) + '\n')

    report_path = os.path.join(base_dir, 'generated', 'front-back-matter-report.log')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('Front/back matter conversion report\n')
        f.write('=' * 60 + '\n\n')
        f.write('\n'.join(report) + '\n\n')
        f.write('Warnings tally:\n')
        for k, v in sorted(warnings.items(), key=lambda kv: -kv[1]):
            f.write('  %6d  %s\n' % (v, k))

    print('\n'.join(report))
    print()
    print('%d warning types, %d total occurrences -- see %s'
          % (len(warnings), sum(warnings.values()), report_path))


if __name__ == '__main__':
    main()
