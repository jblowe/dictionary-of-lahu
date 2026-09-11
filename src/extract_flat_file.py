#!/usr/bin/env python3
"""extract_flat_file.py -- flatten the Dictionary of Lahu TEI edition into a
single CSV, one row per headword and one row per subheadword.

Source: generated/tei/lahu.xml, the clean TEI Lex-0 rendering of the
dictionary body (see README-tei.md). This is preferred over the
intermediate band-tagged generated/lahudico-lexware.txt or the raw
WordStar originals because it's already a well-formed, validated tree
with one <tei:orth> per <tei:form>, one <tei:gram> per <tei:gramGrp>,
and no example material mixed into <tei:note>/<tei:sense> -- so this
script can be a straight structural walk with no text-parsing
heuristics of its own.

Structure assumed (confirmed by inspection of generated/tei/lahu.xml
before writing this script):
  - Top-level <tei:entry> = a headword; <tei:re> = a subheadword.
    <tei:re> never nests inside another <tei:re> (checked: 0 cases).
  - <tei:milestone unit="letter" n="X"/> marks the start of Lahu
    collation-order section X (one of 33: a, i, u, e, o, ... l). Each
    milestone is the LAST direct child of whichever <tei:entry> or
    <tei:re> precedes the letter transition in the original source,
    NOT a sibling of <tei:entry> -- so tracking "current letter" means
    walking each entry's direct children in document order (not just
    reading milestones between top-level entries), which is what the
    two-level walk below does.
  - Examples (<tei:cit type="example"> and their nested translations)
    are read past and never emitted, per the project owner's request
    for a flat file "including everything except the examples."

Output columns:
  entry_id        -- TEI xml:id (e.g. "Lahu.9", "Lahu.2.1")
  parent_id       -- blank for a headword row; the parent entry's
                     entry_id for a subheadword row
  letter_section  -- which of the 33 collation sections this row
                     falls under
  headword        -- always filled in, even on a subheadword's own row
  subheadword     -- blank on the headword's own row
  part_of_speech
  loan_marker     -- LOAN / LOAN? / blank
  usage_label     -- bracketed usage tags, e.g. "[RL]", "[q.v.]",
                     "[neolog.]" -- joined with "; " if more than one
  definition      -- all senses joined; renumbered "1. ...; 2. ..."
                     if the entry has more than one sense
  notes           -- all <tei:note> text for this entry/subentry,
                     joined with "; " (etymology, cross-references,
                     dialect remarks, etc.)

Usage:
    python3 src/extract_flat_file.py [path/to/lahu.xml] [-o output.csv]

Run with no arguments from the project root to use the defaults
(generated/tei/lahu.xml -> generated/lahu-flat.csv).
"""

import argparse
import csv
import sys

from lxml import etree

TEI_NS = 'http://www.tei-c.org/ns/1.0'
XML_NS = 'http://www.w3.org/XML/1998/namespace'
NS = {'t': TEI_NS}


def local(tag):
    return etree.QName(tag).localname


def xml_id(el):
    return el.get(f'{{{XML_NS}}}id', '')


def text_of(el):
    if el is None:
        return ''
    return ' '.join(''.join(el.itertext()).split())


def get_orth(container):
    form = container.find('t:form', NS)
    if form is None:
        return ''
    return text_of(form.find('t:orth', NS))


def get_pos(container):
    gram = container.find('t:gramGrp/t:gram', NS)
    return text_of(gram)


def get_loan_marker(container):
    for usg in container.findall('t:usg', NS):
        if usg.get('type') == 'etym':
            return text_of(usg)
    return ''


def get_usage_labels(container):
    labels = [text_of(u) for u in container.findall('t:usg', NS)
              if u.get('type') == 'label']
    labels = [l for l in labels if l]
    return '; '.join(labels)


def get_definition(container):
    senses = container.findall('t:sense', NS)
    multi = len(senses) > 1
    parts = []
    for s in senses:
        defs = [text_of(d) for d in s.findall('t:def', NS)]
        txt = '; '.join(d for d in defs if d)
        if not txt:
            continue
        n = s.get('n')
        parts.append(f'{n}. {txt}' if (multi and n) else txt)
    return '; '.join(parts)


def get_notes(container):
    notes = [text_of(n) for n in container.findall('t:note', NS)]
    return '; '.join(n for n in notes if n)


def make_row(el, entry_id, parent_id, letter_section, headword, subheadword):
    return {
        'entry_id': entry_id,
        'parent_id': parent_id,
        'letter_section': letter_section,
        'headword': headword,
        'subheadword': subheadword,
        'part_of_speech': get_pos(el),
        'loan_marker': get_loan_marker(el),
        'usage_label': get_usage_labels(el),
        'definition': get_definition(el),
        'notes': get_notes(el),
    }


def extract_rows(tei_path):
    tree = etree.parse(tei_path)
    root = tree.getroot()
    body = root.find('.//t:body', NS)
    if body is None:
        raise SystemExit(f'no <tei:body> found in {tei_path}')

    rows = []
    current_letter = ''

    for entry in body.iter(f'{{{TEI_NS}}}entry'):
        eid = xml_id(entry)
        headword = get_orth(entry)
        rows.append(make_row(entry, eid, '', current_letter, headword, ''))

        # Walk this entry's direct children in document order so a
        # letter-transition milestone nested inside one of its own
        # <re> subentries takes effect for the *later* subentries of
        # this same entry, not just for the next top-level entry.
        for child in entry:
            tag = local(child.tag)
            if tag == 'milestone' and child.get('unit') == 'letter':
                current_letter = child.get('n', current_letter)
            elif tag == 're':
                sub_id = xml_id(child)
                sub_headword = get_orth(child)
                rows.append(make_row(child, sub_id, eid, current_letter,
                                      headword, sub_headword))
                for grandchild in child:
                    gtag = local(grandchild.tag)
                    if gtag == 'milestone' and grandchild.get('unit') == 'letter':
                        current_letter = grandchild.get('n', current_letter)

    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tei_xml', nargs='?', default='generated/tei/lahu.xml',
                     help='path to the TEI XML file (default: generated/tei/lahu.xml)')
    ap.add_argument('-o', '--output', default='generated/lahu-flat.csv',
                     help='output CSV path (default: generated/lahu-flat.csv)')
    args = ap.parse_args()

    rows = extract_rows(args.tei_xml)

    fieldnames = ['entry_id', 'parent_id', 'letter_section', 'headword',
                  'subheadword', 'part_of_speech', 'loan_marker',
                  'usage_label', 'definition', 'notes']
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    n_head = sum(1 for r in rows if not r['parent_id'])
    n_sub = sum(1 for r in rows if r['parent_id'])
    print(f'Wrote {len(rows)} rows ({n_head} headwords, {n_sub} subheadwords) '
          f'to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
