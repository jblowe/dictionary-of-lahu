#!/usr/bin/env python3
"""detect_english_candidates.py -- find likely English-text proofreading
candidates in the dictionary and write them as a review sheet, NOT as
approved corrections (see "Proofreading and corrections" in README.md
for the full picture: this script is the detector: it proposes,
generated/proofreading-candidates-english.csv is disposable and
regenerated fresh every run; a human decides which rows are real and
copies just those into the permanent, curated src/corrections-english.csv,
which is what apply_corrections.py actually applies).

WHY SO FEW CANDIDATES, ON PURPOSE
-----------------------------------
This dictionary's English side is full of things a generic spellchecker
would wrongly flag: dialect/language abbreviations (Bs., Skt., WT, PLB),
Latin binomial species names, romanized citation forms from a dozen
other languages (Tibetan Wylie, Thai, Burmese, Shan, Japanese, French,
Yiddish...), and technical linguistics jargon Matisoff coins freely
(causativizer, allotones, epenthetically). An early, unfiltered version
of this detector flagged over 1,000 "misspellings" this way -- almost
all wrong. Getting useful signal out of a spellchecker over this text
required several precision-first design choices, arrived at
empirically (see the conversation that produced this script for the
full trial-and-error): every one of these is a deliberate,
recall-costing choice, not an oversight.

Two independent checks, run over generated/lahu-flat.csv's definition
and notes columns (English-bearing fields; Lahu headwords/examples are
never touched):

1. SPLIT-WORD DETECTOR (the strong, high-confidence one): looks for two
   adjacent tokens, neither a real English word on its own, whose
   concatenation IS a real word -- e.g. "physi cally" -> "physically",
   "descen dants" -> "descendants". This is almost always a WordStar
   line-wrap that survived conversion as a literal space (or a stray
   inserted paren, e.g. "to(gether)"). Concatenation-is-a-real-word is
   an unusually strong signal on its own; validated by hand against
   real output at ~95%+ precision (one recurring false positive
   pattern -- short 2-letter Lahu grammatical particles that happen to
   concatenate into an unrelated English word, e.g. Lahu "ji ve"
   colliding with English "jive" -- excluded by requiring each half be
   at least 3 characters).

2. SINGLE-WORD TYPO DETECTOR (weaker, more tightly gated): an isolated
   (appears exactly once in the whole corpus, in exactly this casing),
   lowercase, ASCII, length >= 5 word that isn't a real word, but is
   exactly one character edit away from one that both (a) is common
   enough in general English (or well-attested elsewhere in this exact
   corpus) and (b) isn't reachable by relaxing any of these thresholds
   without pulling in Latin species epithets and foreign-citation forms
   as "corrections" to short common English words -- that pull-in
   is exactly what an early looser version of this check did, and
   tightening it (min length 5, correction-frequency floor, corpus-
   frequency floor) was what got it from ~2% precision to something
   worth a human's time.

Both checks additionally skip a candidate if: it's immediately preceded
by a citation marker (a bare "<", "cf.", "cognate", "q.v.", or a
trailing "also") -- these almost always introduce a foreign-language
form, not English prose; it sits inside a double-quoted span (usually a
non-English title or direct quotation); or it's adjacent to a non-ASCII
letter (a sign the "word" is actually a fragment of a longer non-ASCII
token, e.g. a diacritic-bearing foreign form split by this script's own
ASCII-only tokenizer).

Requires the `spellchecker` package (`pyspellchecker`;
`pip install pyspellchecker --break-system-packages` if missing) --
a pure-Python, offline word-frequency dictionary, no network calls.

Usage:
    python3 src/detect_english_candidates.py [path/to/lahu-flat.csv]
        [-o generated/proofreading-candidates-english.csv]
        [--lexware generated/lahudico-lexware.txt]

Every candidate is validated against the actual Lexware band file (the
same one apply_corrections.py patches) before being written out -- a
candidate that can't be found as an exact, unique match on a single
`gl` or `no` band line (e.g. because it only exists inside a joined,
renumbered multi-sense definition) is silently dropped rather than
shown, so every row in the output CSV is guaranteed apply-able as-is.
"""

import argparse
import csv
import re
import sys
from collections import Counter

from spellchecker import SpellChecker

from apply_corrections import parse_scopes, apply_one, MatchError

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*")
ADJACENT_WORD_RE = re.compile(r"[A-Za-z]+")
PAIR_RE = re.compile(r"\b([A-Za-z]{3,})([ (]{1,2})([A-Za-z]{3,})\b")
CITATION_CONTEXT_RE = re.compile(
    r'(<|cf\.|cognate|q\.v\.|also\b.{0,3}$'
    r'|\b[A-Z][a-z]{1,5}\.\s*$'      # a trailing abbreviation like "Jse." "var." "Skt." "Eng."
    r'|\b(?:Shan|Tai|Thai|Siamese|Burmese|Chinese|Mandarin|Sanskrit|Pali|Jingpho'
    r'|Japanese|Khmer|Hindi|Latin|Greek|Yiddish|French|WB|WT|PLB|PTB|PT|PL|TN)\s*$)',
    re.IGNORECASE)

MIN_SINGLE_WORD_LEN = 5
ENGLISH_FREQ_MIN = 3e-4
CORPUS_COUNT_MIN = 50

FIELDS = ['definition', 'notes']


def in_citation_context(text, start, end):
    preceding = text[max(0, start - 25):start]
    if CITATION_CONTEXT_RE.search(preceding):
        return True
    before_char = text[start - 1] if start > 0 else ''
    after_char = text[end] if end < len(text) else ''
    if (before_char and not before_char.isascii()) or (after_char and not after_char.isascii()):
        return True
    if text[:start].count('"') % 2 == 1:
        return True
    return False


def find_split_word_candidates(rows, sc):
    out = []
    for r in rows:
        for field in FIELDS:
            t = r[field]
            if not t:
                continue
            for m in PAIR_RE.finditer(t):
                t1, sep, t2 = m.group(1), m.group(2), m.group(3)
                if t1.lower() in sc or t2.lower() in sc:
                    continue
                joined = (t1 + t2).lower()
                if joined not in sc:
                    continue
                if in_citation_context(t, m.start(), m.end()):
                    continue
                old_text = m.group(0)
                new_text = t1 + t2
                out.append({
                    'entry_id': r['entry_id'], 'flat_field': field,
                    'old_text': old_text, 'new_text': new_text,
                    'reason': f'looks like a word-wrap split ("{old_text}" -> "{new_text}")',
                    'source': 'detect_english_candidates.py:split-word',
                    'context': t[max(0, m.start() - 30):m.end() + 30],
                })
    return out


def has_unknown_neighbor(text, start, end, sc):
    """True if the word-like run immediately before or after this span
    (across a single connecting space or hyphen -- e.g. the "shilly" in
    "shilly-shally", the "cheiro" in "cheiro mancy") is itself not a
    real dictionary word. A candidate typo should be an isolated oddity
    in otherwise-ordinary text; two unknown words back to back is a
    much better fit for "half of a compound/reduplication this
    dictionary's spellchecker just doesn't know" than "two coincidental
    typos in a row"."""
    before = text[max(0, start - 20):start]
    m = re.search(r"[A-Za-z]+[ \-]$", before)
    if m:
        neighbor = m.group(0)[:-1]
        if neighbor and neighbor.lower() not in sc:
            return True
    after = text[end:end + 20]
    m = re.match(r"^[ \-][A-Za-z]+", after)
    if m:
        neighbor = m.group(0)[1:]
        if neighbor and neighbor.lower() not in sc:
            return True
    return False


def find_single_word_candidates(rows, sc):
    occurrences = {}
    word_counter = Counter()
    for r in rows:
        for field in FIELDS:
            t = r[field]
            if not t:
                continue
            for m in WORD_RE.finditer(t):
                w = m.group(0)
                word_counter[w.lower()] += 1
                occurrences.setdefault(w, []).append((r['entry_id'], field, t, m.start(), m.end()))

    out = []
    for w, occ_list in occurrences.items():
        if len(occ_list) != 1 or len(w) < MIN_SINGLE_WORD_LEN or not w.islower():
            continue
        if w in sc:
            continue
        corr = sc.correction(w)
        if not corr or corr == w:
            continue
        eng_freq = sc.word_usage_frequency(corr)
        corpus_n = word_counter.get(corr, 0)
        if not (eng_freq >= ENGLISH_FREQ_MIN or corpus_n >= CORPUS_COUNT_MIN):
            continue
        eid, field, t, start, end = occ_list[0]
        if in_citation_context(t, start, end):
            continue
        if has_unknown_neighbor(t, start, end, sc):
            continue
        out.append({
            'entry_id': eid, 'flat_field': field,
            'old_text': w, 'new_text': corr,
            'reason': f'looks like a typo (one edit from common word {corr!r})',
            'source': 'detect_english_candidates.py:single-word',
            'context': t[max(0, start - 30):end + 30],
        })
    return out


# generated/lahu-flat.csv's 'definition'/'notes' columns are joined from
# possibly-multiple raw Lexware bands (gl/no); the raw band name to check
# against is the same name minus the join, tried in this order.
FLAT_FIELD_TO_BAND = {'definition': ['gl'], 'notes': ['no']}


def validate_against_lexware(candidates, lexware_path, dialect='Lahu'):
    """Confirm each candidate resolves to exactly one real band line via
    apply_corrections.py's own matching logic, and fill in the raw band
    name it actually matched -- so every row in the output is guaranteed
    to be apply-able, and uses the vocabulary apply_corrections.py
    expects (raw band names, not flat-file column names)."""
    with open(lexware_path, encoding='utf-8') as f:
        text = f.read()
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    _, scope_lines = parse_scopes(lines, dialect)

    validated = []
    for c in candidates:
        for band in FLAT_FIELD_TO_BAND[c['flat_field']]:
            trial = {'entry_id': c['entry_id'], 'field': band,
                     'old_text': c['old_text'], 'new_text': c['new_text']}
            try:
                apply_one(lines, scope_lines, trial)
            except MatchError:
                continue
            validated.append({
                'entry_id': c['entry_id'], 'field': band,
                'old_text': c['old_text'], 'new_text': c['new_text'],
                'reason': c['reason'], 'source': c['source'], 'context': c['context'],
            })
            break
    return validated


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('flat_csv', nargs='?', default='generated/lahu-flat.csv')
    ap.add_argument('-o', '--output', default='generated/proofreading-candidates-english.csv')
    ap.add_argument('--lexware', default='generated/lahudico-lexware.txt')
    ap.add_argument('--dialect', default='Lahu')
    args = ap.parse_args()

    with open(args.flat_csv, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    sc = SpellChecker(distance=1)

    split_candidates = find_split_word_candidates(rows, sc)
    single_candidates = find_single_word_candidates(rows, sc)

    # Drop any single-word candidate that's really just one half of a
    # split-word candidate already found for the same entry/field (e.g.
    # "cally" -> "call" would otherwise duplicate "physi cally" ->
    # "physically" on the same line -- applying both would make the
    # second one fail to match after the first has already run).
    split_spans = {(c['entry_id'], c['flat_field']): c['old_text'] for c in split_candidates}
    single_candidates = [
        c for c in single_candidates
        if split_spans.get((c['entry_id'], c['flat_field']), '').find(c['old_text']) == -1
    ]

    candidates = split_candidates + single_candidates
    validated = validate_against_lexware(candidates, args.lexware, args.dialect)

    fieldnames = ['entry_id', 'field', 'old_text', 'new_text', 'reason', 'source', 'context']
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(validated)

    print(f'{len(candidates)} raw candidates, {len(validated)} confirmed apply-able, '
          f'written to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
