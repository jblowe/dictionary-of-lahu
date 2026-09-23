#!/usr/bin/env python3
"""detect_lahu_candidates.py -- find likely Lahu-text proofreading
candidates and write them as a review sheet (see "Proofreading and
corrections" in README.md: this is the detector, not the corrections
list -- generated/proofreading-candidates-lahu.csv is disposable and
regenerated fresh every run; a human reviews it and copies only the
rows they've confirmed, WITH a specific fix filled in, into the
permanent, curated src/corrections-lahu.csv that apply_corrections.py
actually applies).

Unlike the English side, there's no off-the-shelf dictionary or
spellchecker for Lahu, and this dictionary's own ~31,000 headwords/
sub-headwords are the only corpus there is to check anything against.
Rather than a generic character n-gram anomaly model (tried during
development; it flags plenty of statistically rare syllables, but
almost all of them turned out to be real, attested phonological
alternations -- see below -- not typos, and telling the two apart
needs Lahu-specific judgment this script doesn't have), this uses two
narrower, structural checks that lean on the dictionary's own internal
conventions instead of guessing at what's phonologically "normal":

1. SUB-ENTRY ROOT CHECK: a sub-entry is lexicographically supposed to
   extend its parent headword -- share at least one morpheme with it.
   This check tokenizes both (on whitespace/hyphen/=/~/≡/≣/,/;,
   also splicing "(n)"-style optional-final-segment parentheses both
   ways) and flags a sub-entry that shares no token, in any tone-
   stripped/case-folded form, with its parent.

   Getting this to a usable precision took several rounds of finding
   and excluding LEGITIMATE patterns that first looked like anomalies:
   parent headwords using "~" to list tone/register variants (the
   sub-entries under these instantiate a general pattern, not a
   specific root, so they're skipped entirely); a pervasive final-nasal
   alternation where a headword's optional or fixed final "-n" is
   dropped or added in derived forms (both directions are common enough
   in the real data that this is clearly a live feature of Lahu
   morphology here, not noise -- handled by also matching a token
   with its final "n" stripped); and case differences for proper-noun
   sub-entries built on a common-noun root (e.g. "Lî" -> "Lî-co"). Even
   after all of that, a small residual (developer testing found ~18
   candidates out of 21.6k checked sub-entries) may still include a
   phonological alternation this script doesn't know about yet (e.g.
   final glottal-stop ʾ dropping was noticed but not generalized) --
   flagged, not asserted, for exactly that reason.

2. CROSS-REFERENCE TARGET CHECK: an etymological/cross-reference note
   in the form "cf. TARGET (POS)" names another entry in this same
   dictionary. This check resolves TARGET against the full headword/
   sub-headword index (again tone-stripped for comparison) and flags
   it when it can't be found. Deliberately narrow: only the single,
   unambiguous "cf. TARGET (POS)" shape is checked (TARGET is a single
   orthographic word, no internal spaces, though it may carry its own
   attached parens like "khá(n)"); comma-chained multi-target lists,
   "SYN."/"ANT." (which can point to a same-meaning WORD or to a
   grammatical CLASS -- not reliably distinguishable), and phrasal
   wrappers ("perhaps X", "also X", "the native Lh. cognate X") are all
   left unchecked rather than parsed unreliably. On the real dictionary
   this resolves ~93% of ~4,000 "cf." citations; the unresolved ~7%
   are the candidates.

Neither check proposes a specific fix (unlike the English detector) --
these surface a genuine structural anomaly, but figuring out whether
the sub-entry or its parent has the typo, or whether the "cf."
reference or its target does, needs a human (ideally someone who knows
Lahu) to look at the actual entry. new_text is left blank in the
output sheet for this reason; fill it in only once you've worked out
the actual fix, and only then copy the row into
src/corrections-lahu.csv.

Usage:
    python3 src/detect_lahu_candidates.py [path/to/lahu-flat.csv]
        [-o generated/proofreading-candidates-lahu.csv]
"""

import argparse
import csv
import re
import sys
import unicodedata

TONE_MARKS = '́̀̂̄̊'


def strip_tone(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if c not in TONE_MARKS)
    return unicodedata.normalize('NFC', s).lower()


def split_tokens(hw):
    hw = re.sub(r'[~=≡≣/,;]', ' ', hw)
    return [t for t in re.findall(r"[^\s\-\(\)]+", hw) if t]


def token_variants(hw):
    variants = set()
    for base in (hw, re.sub(r'\(([^)]*)\)', r'\1', hw), re.sub(r'\([^)]*\)', '', hw)):
        for tok in split_tokens(base):
            t = strip_tone(tok)
            variants.add(t)
            if t.endswith('n'):
                variants.add(t[:-1])
    return variants


def find_subentry_root_candidates(rows):
    parents = {r['entry_id']: r['headword'] for r in rows if not r['parent_id']}
    out = []
    for r in rows:
        if not r['parent_id']:
            continue
        parent_hw = parents.get(r['parent_id'], '')
        sub_hw = r['subheadword']
        if not parent_hw or '~' in parent_hw:
            continue
        if sub_hw.startswith('--') or (' ' in sub_hw and len(sub_hw.split()) > 4):
            continue
        if not (token_variants(parent_hw) & token_variants(sub_hw)):
            out.append({
                'entry_id': r['entry_id'], 'field': 'hw', 'old_text': sub_hw, 'new_text': '',
                'reason': (f'sub-entry {sub_hw!r} shares no root with its parent '
                           f'headword {parent_hw!r} -- check for a transcription '
                           f'inconsistency in one or the other'),
                'source': 'detect_lahu_candidates.py:subentry-root',
                'context': f'parent={parent_hw!r} sub={sub_hw!r}',
            })
    return out


def build_headword_index(rows):
    raw = set()
    norm = set()
    for r in rows:
        hw = r['subheadword'] or r['headword']
        raw.add(hw)
        norm.add(strip_tone(hw).strip())
        for comp in re.split(r'[\s\-=≡≣~]+', hw):
            if comp:
                norm.add(strip_tone(comp))
    return raw, norm


def find_cf_targets(text):
    """Find each 'cf. TARGET (POS)' citation, scanning for a balanced
    top-level paren group so a target with its own attached parens
    (e.g. an optional "khá(n)") isn't cut short at its first '('."""
    out = []
    for m in re.finditer(r'\bcf\.\s+', text):
        seg_start = m.end()
        depth = 0
        paren_start = None
        i = seg_start
        n = len(text)
        while i < n:
            c = text[i]
            if c == ';':
                if depth == 0:
                    break
            elif c == '(':
                if depth == 0:
                    paren_start = i
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0 and paren_start is not None:
                    target = text[seg_start:paren_start].strip(' ,')
                    posmark = text[paren_start + 1:i]
                    if (target and ' ' not in target
                            and re.fullmatch(r"[A-Za-z][A-Za-z+\- ]{0,20}", posmark)):
                        out.append((target, m.start()))
                    break  # only the first, unambiguous target per "cf." -- see docstring
            i += 1
    return out


def find_crossref_candidates(rows):
    all_raw, all_norm = build_headword_index(rows)
    out = []
    for r in rows:
        t = r['notes']
        if not t:
            continue
        for target, pos in find_cf_targets(t):
            if target in all_raw or strip_tone(target) in all_norm:
                continue
            out.append({
                'entry_id': r['entry_id'], 'field': 'no', 'old_text': target, 'new_text': '',
                'reason': (f'cross-reference target {target!r} not found among any '
                           f'headword or sub-headword -- possible typo in the '
                           f'reference or its target, or the entry may not exist '
                           f'in this edition'),
                'source': 'detect_lahu_candidates.py:cross-ref',
                'context': t[max(0, pos - 15):pos + len(target) + 40],
            })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('flat_csv', nargs='?', default='generated/lahu-flat.csv')
    ap.add_argument('-o', '--output', default='generated/proofreading-candidates-lahu.csv')
    args = ap.parse_args()

    with open(args.flat_csv, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    candidates = find_subentry_root_candidates(rows) + find_crossref_candidates(rows)

    fieldnames = ['entry_id', 'field', 'old_text', 'new_text', 'reason', 'source', 'context']
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(candidates)

    print(f'{len(candidates)} candidates written to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
