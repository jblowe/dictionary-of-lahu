#!/usr/bin/env python3
"""apply_corrections.py -- apply a curated, human-approved list of textual
fixes to the whole-dictionary Lexware band file, before it becomes XML.

WHY THIS EXISTS
----------------
This project's rule is that originals/ is never touched and everything
under generated/ is fully reproducible from originals/ + src/ -- nothing
in generated/ is ever hand-edited (see README.md's "Directory layout").
But proofreading the dictionary (English and Lahu text) will surface real
errors that need fixing somewhere durable. "Somewhere durable" can't be
any single generated/ output (the HTML, the PDF, the TEI, the search
site's database) individually, because all of those are independently
regenerated from generated/lahudico-lexware.txt on every pipeline run --
hand-fixing one would just be overwritten, and fixing all of them
separately would drift out of sync with each other.

So a correction is instead recorded as a small, permanent, checked-in
row in src/corrections-lahu.csv or src/corrections-english.csv (which
language the fix belongs to just decides which file it lives in; both
are read the same way), and this script applies every row in both files
to generated/lahudico-lexware.txt as a pipeline step that runs right
after concat_master.sh and right before lex2xml.py. Every artifact
downstream of that point (the ad hoc XML, the TEI, the HTML/PDF, the
flat CSV, the search website's database) then inherits the fix for
free, every time the pipeline is regenerated, with no per-format
patching and no risk of one output silently falling out of sync with
the rest.

HOW A CORRECTION IS ADDRESSED
------------------------------
Each row names a TEI-style entry_id (e.g. "Lahu.234" for a headword,
"Lahu.234.2" for its 2nd sub-entry -- the same IDs already visible in
generated/tei/lahu.xml and generated/lahu-flat.csv's entry_id/parent_id
columns) plus the exact old text to replace and what to replace it
with. This script re-derives the *same* entry/sub-entry numbering
scheme independently, by walking the Lexware band file the same way
lex2xml.py and lahu-to-tei.xsl do:

  - A line starting with exactly one '.' (e.g. ".hw") starts a new
    top-level entry; the Nth such line becomes "Lahu.N" (matching
    lex2xml.py's out_parts.append('<entry id="%s.%d">' % ...) counter,
    which increments on *every* single-dot line regardless of its band
    name -- so a stray single-dot line that isn't really a headword
    would also consume an entry-number slot here, exactly as it would
    in the real pipeline).
  - A line starting with 2+ dots (e.g. "..hw") starts a new sub-entry
    under the current top-level entry; the Mth such sub-entry (reset to
    1 at each new top-level entry) becomes "Lahu.N.M" (matching
    lahu-to-tei.xsl's `concat(../@id, '.', count(preceding-sibling::sub)
    + 1)`).
  - Every plain (non-dot) band line belongs to whichever scope --
    the enclosing top-level entry, or the most recently opened
    sub-entry -- is currently open, exactly like lex2xml.py's
    insub/inmode state machine.

If the Lexware band format or either script's counting rule ever
changes, this replication needs to change with it -- there's no shared
code between the three, only a shared, documented convention. This
script's parse_scopes() is the single place that convention lives on
this side; keep it lined up with lex2xml.py's convert() and
lahu-to-tei.xsl's `sub` template.

SAFETY
------
A correction is only applied if its old_text appears, verbatim,
EXACTLY ONCE among the band lines belonging to its stated entry_id
(further narrowed to lines with the stated `field` band name, if
given). Zero matches or more than one match is a hard error naming the
offending row -- like the Edit tool's own old_string uniqueness check
-- rather than silently applying a partial or wrong-place fix. This
matters more than usual here: Lahu tone diacritics are contrastive
(a/à/â/ā are different syllables), so a fuzzy or partial match could
silently change which word an entry means.

old_text/new_text may not contain a tab or newline -- a correction can
only replace text within a single band's value, never restructure the
band file itself (add/remove/merge entries, sub-entries, or bands),
which would desynchronize this script's entry numbering from
lex2xml.py's on every subsequent run.

Usage:
    python3 src/apply_corrections.py [infile] [-o outfile]
        [--corrections FILE [FILE ...]] [--report LOG] [--dialect Lahu]
        [--dry-run]

Run with no arguments from the project root to apply
src/corrections-lahu.csv and src/corrections-english.csv, in place, to
generated/lahudico-lexware.txt (the default pipeline wiring -- see
regenerate-all-files.sh). With zero rows in both files (the normal
starting state), this is a byte-for-byte no-op.
"""

import argparse
import csv
import sys
from collections import defaultdict

REQUIRED_COLUMNS = ['entry_id', 'field', 'old_text', 'new_text', 'reason', 'source']


class CorrectionError(Exception):
    """A problem with a correction row itself (bad CSV, illegal
    characters) -- distinct from a MatchError, which is a problem
    applying an otherwise well-formed row to the current text."""


class MatchError(Exception):
    """A well-formed correction row didn't match the text the way it
    was supposed to (not found, or found more than once)."""


def load_corrections(paths):
    """Read one or more corrections CSVs, tag each row with its source
    file (for the report), and validate old_text/new_text up front."""
    rows = []
    for path in paths:
        try:
            f = open(path, newline='', encoding='utf-8')
        except FileNotFoundError:
            raise CorrectionError(f'corrections file not found: {path}')
        with f:
            reader = csv.DictReader(f)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise CorrectionError(
                    f'{path}: missing required column(s) {missing} '
                    f'(found {reader.fieldnames})')
            for i, row in enumerate(reader, start=2):  # 1 = header
                entry_id = (row['entry_id'] or '').strip()
                if not entry_id:
                    continue  # allow blank/comment-ish rows to be skipped silently
                old_text = row['old_text'] or ''
                new_text = row['new_text'] or ''
                for label, text in (('old_text', old_text), ('new_text', new_text)):
                    if '\t' in text or '\n' in text:
                        raise CorrectionError(
                            f'{path}:{i}: {label} contains a tab or newline -- a '
                            f'correction may only replace text within a single '
                            f"band's value, it can't restructure the band file")
                if old_text == '':
                    raise CorrectionError(f'{path}:{i}: old_text is empty')
                if new_text == '':
                    raise CorrectionError(
                        f'{path}:{i}: new_text is empty -- a proofreading candidate '
                        f'sheet with no proposed fix yet was probably copied in before '
                        f'someone filled one in; if you really do want to delete this '
                        f'text, replace new_text with an explicit empty marker instead')
                if old_text == new_text:
                    raise CorrectionError(f'{path}:{i}: old_text and new_text are identical')
                rows.append({
                    'entry_id': entry_id,
                    'field': (row['field'] or '').strip(),
                    'old_text': old_text,
                    'new_text': new_text,
                    'reason': (row['reason'] or '').strip(),
                    'source': (row['source'] or '').strip(),
                    '_file': path,
                    '_lineno': i,
                })
    return rows


def parse_scopes(lines, dialect):
    """Walk the Lexware band file exactly the way lex2xml.py and
    lahu-to-tei.xsl do (see module docstring), and return, for every
    line index, the entry_id/sub_id it belongs to (or None for content
    before the first entry, e.g. stray running-header xx/err noise).

    Returns a list `scope_of` parallel to `lines` (scope_of[i] is the
    scope for lines[i]), plus a dict scope_lines mapping each scope id
    to the list of line indices that belong to it.
    """
    scope_of = [None] * len(lines)
    scope_lines = defaultdict(list)

    n = 0            # top-level entry counter, matches lex2xml.py's `n`
    m = 0            # sub-entry counter, reset at each new top-level entry
    current_scope = None

    for i, raw in enumerate(lines):
        line = raw.rstrip('\r')
        if line.strip() == '':
            continue

        j = 0
        while j < len(line) and line[j] == '.':
            j += 1
        dots = line[:j]

        if dots == '.':
            n += 1
            m = 0
            current_scope = f'{dialect}.{n}'
        elif len(dots) >= 2:
            m += 1
            current_scope = f'{dialect}.{n}.{m}'
        # else: plain band line, current_scope unchanged

        scope_of[i] = current_scope
        if current_scope is not None:
            scope_lines[current_scope].append(i)

    return scope_of, scope_lines


def band_name_of(line):
    """The band name a line carries, with any leading dots stripped --
    e.g. '..hw\\tword' -> 'hw', 'no\\ttext' -> 'no'."""
    stripped = line.lstrip('.')
    tab = stripped.find('\t')
    return stripped[:tab] if tab != -1 else stripped


def apply_one(lines, scope_lines, correction):
    entry_id = correction['entry_id']
    field = correction['field']
    old_text = correction['old_text']
    new_text = correction['new_text']

    candidate_idxs = scope_lines.get(entry_id, [])
    if not candidate_idxs:
        raise MatchError(f'entry_id {entry_id!r} does not exist in the current text '
                          f'(no lines are scoped to it)')

    if field:
        candidate_idxs = [i for i in candidate_idxs if band_name_of(lines[i]) == field]
        if not candidate_idxs:
            raise MatchError(f'entry_id {entry_id!r} exists, but has no {field!r} band')

    matches = [i for i in candidate_idxs if lines[i].count(old_text) > 0]
    if not matches:
        raise MatchError(f'old_text {old_text!r} not found under entry_id {entry_id!r}'
                          + (f', field {field!r}' if field else ''))
    if len(matches) > 1:
        raise MatchError(f'old_text {old_text!r} under entry_id {entry_id!r} is ambiguous: '
                          f'matches {len(matches)} different band lines '
                          f'({[band_name_of(lines[i]) for i in matches]}) -- narrow it down '
                          f'with a more specific field or more context in old_text')

    idx = matches[0]
    if lines[idx].count(old_text) > 1:
        raise MatchError(f'old_text {old_text!r} appears more than once on the same '
                          f'{band_name_of(lines[idx])!r} band line under entry_id {entry_id!r} '
                          f'-- make old_text longer/more specific so it matches exactly once')

    tab = lines[idx].find('\t')
    if tab == -1:
        raise MatchError(f'entry_id {entry_id!r}: matched line has no tab-separated '
                          f'value ({lines[idx]!r}) -- refusing to touch it')
    prefix, value = lines[idx][:tab + 1], lines[idx][tab + 1:]
    new_value = value.replace(old_text, new_text, 1)
    return idx, prefix + new_value


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('infile', nargs='?', default='generated/lahudico-lexware.txt',
                     help='Lexware band file to correct (default: '
                          'generated/lahudico-lexware.txt)')
    ap.add_argument('-o', '--output', default=None,
                     help='output path (default: overwrite infile in place)')
    ap.add_argument('--corrections', nargs='+',
                     default=['src/corrections-lahu.csv', 'src/corrections-english.csv'],
                     help='corrections CSV(s) to apply (default: both curated files)')
    ap.add_argument('--report', default='generated/corrections-report.log',
                     help='where to write the applied-corrections report '
                          '(default: generated/corrections-report.log)')
    ap.add_argument('--dialect', default='Lahu',
                     help='entry_id prefix, must match the dialect argument '
                          'given to lex2xml.py (default: Lahu)')
    ap.add_argument('--dry-run', action='store_true',
                     help="validate and report what would change, but don't write "
                          'infile/output or the report')
    args = ap.parse_args()
    output = args.output or args.infile

    try:
        corrections = load_corrections(args.corrections)
    except CorrectionError as e:
        sys.exit(f'error: {e}')

    with open(args.infile, encoding='utf-8') as f:
        text = f.read()
    trailing_newline = text.endswith('\n')
    lines = text.split('\n')
    if trailing_newline:
        lines = lines[:-1]

    scope_of, scope_lines = parse_scopes(lines, args.dialect)

    applied = []
    errors = []
    for c in corrections:
        try:
            idx, new_line = apply_one(lines, scope_lines, c)
        except MatchError as e:
            errors.append((c, str(e)))
            continue
        lines[idx] = new_line
        applied.append((c, idx))

    if errors:
        print(f'{len(errors)} correction(s) failed to apply:', file=sys.stderr)
        for c, msg in errors:
            print(f"  {c['_file']}:{c['_lineno']} ({c['entry_id']}): {msg}", file=sys.stderr)
        sys.exit(1)

    report_lines = [
        f'Applied {len(applied)} correction(s) from {", ".join(args.corrections)}',
        f'Input:  {args.infile}',
        f'Output: {output}{" (dry run -- not written)" if args.dry_run else ""}',
        '',
    ]
    for c, idx in applied:
        field_note = f" [{c['field']}]" if c['field'] else ''
        report_lines.append(
            f"{c['entry_id']}{field_note}: {c['old_text']!r} -> {c['new_text']!r}"
            f" ({c['reason']}, source: {c['source']}, {c['_file']}:{c['_lineno']})")
    report_text = '\n'.join(report_lines) + '\n'

    print(report_text, end='')

    if args.dry_run:
        return

    out_text = '\n'.join(lines)
    if trailing_newline:
        out_text += '\n'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(out_text)

    with open(args.report, 'w', encoding='utf-8') as f:
        f.write(report_text)


if __name__ == '__main__':
    main()
