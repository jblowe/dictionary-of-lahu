#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
order_files.py -- determine the correct collation order of the 135
originals/DLWordStarFiles/base/BASE.* files, by reading each file's
Lexware output (generated/DLWordStarFiles/base-lexware/lex.*.txt),
extracting the top-level headwords (".hw" band, not the "..hw"
sub-headword band), and sorting by the authoritative Lahu collation key
(lahu_collate.py).

Writes (into src/, alongside the scripts that consume them -- these are
treated as checked-in script parameters, not throwaway generated output,
since concat_master.sh reads file-order.txt as an input on every run):
  src/file-order.csv  order, initial, first_headword, classifying_headword,
                      note, last_headword, entry_count, base_filename,
                      lex_filename, plaintext_filename
  src/file-order.txt  just the BASE.* filenames, one per line, in order
                      (consumed by concat_master.sh)

Usage:
  python3 order_files.py [project-root]     (defaults to '.')
"""
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lahu_collate import sort_key, initial_label, ParseFailure, parse_initial_syllable, first_word  # noqa: E402


def top_level_headwords(lex_path):
    """Return (all_top_level_headwords, count) among ".hw" bands (not "..hw")."""
    hws = []
    with open(lex_path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                continue
            band, _, val = line.partition('\t')
            if band == '.hw':
                hws.append(val)
    return hws, len(hws)


def first_parseable(hws):
    """Some files' very first entries are bare-consonant/onomatopoeic
    headwords with no vowel (e.g. 'ʔ', 'ch-ch', 'm.', 'š') that can't be
    given a normal consonant+vowel+tone collation key -- they're real
    dictionary entries, just not syllable-initial ones we can sort on.
    Walk forward to the first entry that DOES parse, and use that to
    classify which section of the alphabet this file belongs to."""
    for i, hw in enumerate(hws):
        try:
            parse_initial_syllable(first_word(hw))
            return hw, i
        except ParseFailure:
            continue
    return None, -1


def main(base_dir):
    lex_dir = os.path.join(base_dir, 'generated', 'DLWordStarFiles', 'base-lexware')
    lex_files = sorted(glob.glob(os.path.join(lex_dir, 'lex.*.txt')))
    lex_files = [f for f in lex_files if not os.path.basename(f).startswith('LOG.')]

    rows = []
    failures = []
    for lex_path in lex_files:
        fname = os.path.basename(lex_path)
        corename = fname[len('lex.'):-len('.txt')]  # e.g. LH-A1.TXE
        base_filename = 'BASE.' + corename
        plaintext_filename = base_filename + '.txt'

        hws, count = top_level_headwords(lex_path)
        if not hws:
            failures.append((base_filename, 'no top-level .hw entries found'))
            continue

        rep_hw, rep_i = first_parseable(hws)
        if rep_hw is None:
            failures.append((base_filename, 'no top-level headword in this file parses at all'))
            continue

        key = sort_key(rep_hw)
        label = initial_label(rep_hw)
        note = '' if rep_i == 0 else f'(skipped {rep_i} non-syllabic entr{"y" if rep_i == 1 else "ies"} to classify)'

        rows.append({
            'sort_key': key,
            'initial': label,
            'first_headword': hws[0],
            'classifying_headword': rep_hw,
            'note': note,
            'last_headword': hws[-1],
            'entry_count': count,
            'base_filename': base_filename,
            'lex_filename': fname,
            'plaintext_filename': plaintext_filename,
        })

    rows.sort(key=lambda r: r['sort_key'])

    out_csv = os.path.join(base_dir, 'src', 'file-order.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['order', 'initial', 'first_headword', 'classifying_headword', 'note',
                     'last_headword', 'entry_count', 'base_filename', 'lex_filename',
                     'plaintext_filename'])
        for i, r in enumerate(rows, start=1):
            w.writerow([i, r['initial'], r['first_headword'], r['classifying_headword'], r['note'],
                        r['last_headword'], r['entry_count'], r['base_filename'], r['lex_filename'],
                        r['plaintext_filename']])

    out_txt = os.path.join(base_dir, 'src', 'file-order.txt')
    with open(out_txt, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(r['base_filename'] + '\n')

    print(f"Ordered {len(rows)} files; wrote {out_csv} and {out_txt}")
    if failures:
        print(f"\n{len(failures)} file(s) had trouble parsing their first headword:")
        for fn, msg in failures:
            print(f"  {fn}: {msg}")

    # distinct initials, and which ones span multiple files
    from collections import defaultdict
    by_initial = defaultdict(list)
    for r in rows:
        by_initial[r['initial']].append(r['base_filename'])
    multi = {k: v for k, v in by_initial.items() if len(v) > 1}
    print(f"\n{len(by_initial)} distinct (consonant+vowel) initials across {len(rows)} files.")
    print(f"{len(multi)} initials are split across more than one file:")
    for k in sorted(multi, key=lambda k: [r['sort_key'] for r in rows if r['initial'] == k][0]):
        print(f"  {k:10s} -> {', '.join(multi[k])}")

    return rows


if __name__ == '__main__':
    base_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    main(base_dir)
