#!/usr/bin/env python3
"""build_search_db.py -- build the client-side search database for the
static Dictionary of Lahu website (docs/).

Source: generated/tei/lahu.xml, the same TEI Lex-0 file
src/extract_flat_file.py reads. This script shares that script's
structural-walk assumptions (see its module docstring for the details
confirmed by inspection: <tei:re> subentries don't nest, letter-section
<tei:milestone>s can land inside a <tei:re> and must be tracked in
document order, etc.) but is otherwise independent, per the project
convention of not entangling one-off scripts (see
process_front_and_back_matter.py's docstring for the same reasoning).

Unlike extract_flat_file.py's CSV (which deliberately excludes example
sentences), this database DOES carry examples -- the website's
paragraph view is meant to resemble the LaTeX rendering, which includes
them, and the project owner asked for them to be searchable too.

Output: a single SQLite file (default docs/lahu-dictionary.sqlite3)
with two tables:

  articles(id, headword, pos, loan_marker, loan_source, usg_label,
           definition, notes, examples_json, letter_section,
           search_headword, search_pos, search_definition,
           search_notes, search_loan_source, search_all)

  subentries(id, article_id, headword, pos, loan_marker, loan_source,
             usg_label, definition, notes, examples_json,
             search_headword, search_pos, search_definition,
             search_notes, search_loan_source, search_all)

`id` is assigned in document order, which is already correct Lahu
collation order (the TEI file IS the sorted dictionary) -- so no need
to re-derive src/lahu_collate.py's sort key here; the browser just
`ORDER BY id`.

The search_* columns are NFC-normalized + casefolded twins of the
human-readable columns, for substring matching in the browser. Unlike
stedt-static's diacritic-stripping sortkey() (fine for STEDT's roman
cross-language forms), tone diacritics are NOT stripped here: á/à/â/ā
are different Lahu syllables, and collapsing them would make search
confuse real words. Case-folding only.

loan_source is extracted from the etymology note the same way
src/extract_loans.py (an earlier one-off script for a loanword
spreadsheet) did it: match the dictionary's own "< LANGUAGE" citation
convention against the abbreviation key in
originals/DLOtherFiles/ABBREVS2.TXE. That extraction logic is
duplicated here (not imported) since extract_loans.py is a throwaway
script rooted in generated/, not a project library -- see this
project's convention of small single-purpose scripts.

Usage:
    python3 src/build_search_db.py [path/to/lahu.xml] [-o output.sqlite3]

Run with no arguments from the project root to use the defaults
(generated/tei/lahu.xml -> docs/lahu-dictionary.sqlite3). This script
is standalone -- NOT wired into regenerate-all-files.sh -- run it by
hand whenever you want to publish an updated website.
"""

import argparse
import json
import re
import sqlite3
import sys
import unicodedata

from lxml import etree

TEI_NS = 'http://www.tei-c.org/ns/1.0'
XML_NS = 'http://www.w3.org/XML/1998/namespace'
NS = {'t': TEI_NS}


# ---------------------------------------------------------------------------
# TEI structural helpers (same approach as extract_flat_file.py)
# ---------------------------------------------------------------------------

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
    return text_of(container.find('t:gramGrp/t:gram', NS))


def get_loan_marker(container):
    for usg in container.findall('t:usg', NS):
        if usg.get('type') == 'etym':
            return text_of(usg)
    return ''


def get_usage_labels(container):
    labels = [text_of(u) for u in container.findall('t:usg', NS) if u.get('type') == 'label']
    return '; '.join(l for l in labels if l)


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


def get_examples(container):
    """Returns a list of [lahu, english] pairs from direct <cit type="example"> children."""
    out = []
    for cit in container.findall('t:cit', NS):
        if cit.get('type') != 'example':
            continue
        lahu = text_of(cit.find('t:quote', NS))
        eng = ''
        trans = cit.find('t:cit[@type="translation"]', NS)
        if trans is not None:
            eng = text_of(trans.find('t:quote', NS))
        if lahu or eng:
            out.append([lahu, eng])
    return out


# ---------------------------------------------------------------------------
# Loanword source-language extraction (ported from src/extract_loans.py)
# ---------------------------------------------------------------------------

TOKEN_PATTERNS = [
    (r'N\.?\s*Thai', 'Northern Thai'),
    (r'No\.?\s*Thai', 'Northern Thai'),
    (r'N\.?\s*Tai', 'Northern Thai'),
    (r'Brit\.?\s*Eng\.?', 'English (British)'),
    (r'Written Burmese', 'Burmese (Written)'),
    (r'Written Tibetan', 'Tibetan (Written)'),
    (r'Proto-Lolo-Burmese', 'Proto-Lolo-Burmese (reconstructed)'),
    (r'Proto-Loloish', 'Proto-Loloish (reconstructed)'),
    (r'Proto-Tai', 'Proto-Tai (reconstructed)'),
    (r'Proto-Tibeto-Burman', 'Proto-Tibeto-Burman (reconstructed)'),
    (r'PLB', 'Proto-Lolo-Burmese (reconstructed)'),
    (r'PLoloish', 'Proto-Loloish (reconstructed)'),
    (r'PTB', 'Proto-Tibeto-Burman (reconstructed)'),
    (r'PT\b', 'Proto-Tai (reconstructed)'),
    (r'PL\b', 'Proto-Loloish (reconstructed)'),
    (r'TN\b', 'Tai Nuea'),
    (r'Tai Nuea', 'Tai Nuea'),
    (r'Shan', 'Shan'),
    (r'Siamese', 'Siamese/Thai'),
    (r'Si\.', 'Siamese/Thai'),
    (r'Thai', 'Thai'),
    (r'Tai', 'Tai (general)'),
    (r'Bs\.', 'Burmese'),
    (r'Burmese', 'Burmese'),
    (r'WB\b', 'Written Burmese'),
    (r'WT\b', 'Written Tibetan'),
    (r'Mand\.', 'Mandarin Chinese'),
    (r'Mandarin', 'Mandarin Chinese'),
    (r'Chin\.', 'Chinese'),
    (r'Chinese', 'Chinese'),
    (r'Ch\.', 'Chinese'),
    (r'Eng\.', 'English'),
    (r'English', 'English'),
    (r'Skt\.', 'Sanskrit'),
    (r'Sanskrit', 'Sanskrit'),
    (r'Pali', 'Pali'),
    (r'Jg\.', 'Jingpho'),
    (r'Jingpho', 'Jingpho'),
    (r'Jse\.', 'Japanese'),
    (r'Japanese', 'Japanese'),
    (r'Khmer', 'Khmer'),
    (r'Hindi', 'Hindi'),
    (r'Latin', 'Latin'),
    (r'Greek', 'Greek'),
    (r'Yid\.', 'Yiddish'),
    (r'Fr\.', 'French'),
    (r'French', 'French'),
]
_TOKEN_RE = re.compile('|'.join(f'(?P<t{i}>{pat})' for i, (pat, _) in enumerate(TOKEN_PATTERNS)))
_NAMES = [name for _, name in TOKEN_PATTERNS]
_FILLER_RE = re.compile(
    r'^(?:\s*(?:prob\.?|ult\.?|perhaps|also|the|same|possibly|apparently|first\s+syll\.?|'
    r'1st\.?\s*syll\.?|2nd\.?\s*syll\.?|last\s+element|missionary)\s*)*',
    re.IGNORECASE,
)


def loan_source_from_notes(notes_text):
    """Best-effort extraction of the proximate source language named in an
    etymology note, e.g. '< Shan s\\'oo' -> 'Shan'. Returns '' if the note
    doesn't name one the abbreviation key recognizes (this does NOT mean
    the word isn't a loan -- see docs/index.html's help text)."""
    if not notes_text:
        return ''
    for m in re.finditer(r'<', notes_text):
        rest = notes_text[m.end():m.end() + 60]
        fm = _FILLER_RE.match(rest)
        rest2 = rest[fm.end():] if fm else rest
        tm = _TOKEN_RE.match(rest2.strip())
        if tm:
            idx = [g for g in tm.groupdict() if tm.group(g)][0]
            return _NAMES[int(idx[1:])]
    return ''


# ---------------------------------------------------------------------------
# Normalization for search columns: NFC + casefold. Deliberately NOT
# stripping combining marks -- Lahu tone diacritics are contrastive.
# ---------------------------------------------------------------------------

def norm(text):
    if not text:
        return ''
    return unicodedata.normalize('NFC', text).casefold()


# ---------------------------------------------------------------------------
# Row assembly
# ---------------------------------------------------------------------------

def make_row(el, row_id, article_id, headword):
    pos = get_pos(el)
    loan_marker = get_loan_marker(el)
    usg_label = get_usage_labels(el)
    definition = get_definition(el)
    notes = get_notes(el)
    examples = get_examples(el)
    loan_source = loan_source_from_notes(notes) if loan_marker else ''
    examples_text = ' '.join(f'{lhu} {eng}' for lhu, eng in examples)

    search_all = ' '.join(filter(None, [
        headword, pos, loan_marker, loan_source, usg_label, definition, notes, examples_text,
    ]))

    return {
        'id': row_id,
        'article_id': article_id,
        'headword': headword,
        'pos': pos,
        'loan_marker': loan_marker,
        'loan_source': loan_source,
        'usg_label': usg_label,
        'definition': definition,
        'notes': notes,
        'examples_json': json.dumps(examples, ensure_ascii=False),
        'search_headword': norm(headword),
        'search_pos': norm(pos),
        'search_definition': norm(definition),
        'search_notes': norm(notes),
        'search_loan_source': norm(loan_source),
        'search_all': norm(search_all),
    }


def extract(tei_path):
    tree = etree.parse(tei_path)
    root = tree.getroot()
    body = root.find('.//t:body', NS)
    if body is None:
        raise SystemExit(f'no <tei:body> found in {tei_path}')

    articles = []
    subentries = []
    current_letter = ''
    next_id = 1

    for entry in body.iter(f'{{{TEI_NS}}}entry'):
        headword = get_orth(entry)
        aid = next_id
        next_id += 1
        row = make_row(entry, aid, None, headword)
        row['letter_section'] = current_letter
        articles.append(row)

        for child in entry:
            tag = local(child.tag)
            if tag == 'milestone' and child.get('unit') == 'letter':
                current_letter = child.get('n', current_letter)
            elif tag == 're':
                sid = next_id
                next_id += 1
                sub_headword = get_orth(child)
                subentries.append(make_row(child, sid, aid, sub_headword))
                for grandchild in child:
                    gtag = local(grandchild.tag)
                    if gtag == 'milestone' and grandchild.get('unit') == 'letter':
                        current_letter = grandchild.get('n', current_letter)

    return articles, subentries


# ---------------------------------------------------------------------------
# SQLite output
# ---------------------------------------------------------------------------

ARTICLE_COLS = ['id', 'headword', 'pos', 'loan_marker', 'loan_source', 'usg_label',
                'definition', 'notes', 'examples_json', 'letter_section',
                'search_headword', 'search_pos', 'search_definition',
                'search_notes', 'search_loan_source', 'search_all']

SUBENTRY_COLS = ['id', 'article_id', 'headword', 'pos', 'loan_marker', 'loan_source',
                 'usg_label', 'definition', 'notes', 'examples_json',
                 'search_headword', 'search_pos', 'search_definition',
                 'search_notes', 'search_loan_source', 'search_all']


def build_db(articles, subentries, out_path):
    import os
    if os.path.exists(out_path):
        os.remove(out_path)
    conn = sqlite3.connect(out_path)
    cur = conn.cursor()

    cur.execute(f"""
        CREATE TABLE articles (
            {', '.join(c + (' INTEGER PRIMARY KEY' if c == 'id' else ' TEXT') for c in ARTICLE_COLS)}
        )
    """)
    cur.execute(f"""
        CREATE TABLE subentries (
            {', '.join(c + (' INTEGER PRIMARY KEY' if c == 'id' else (' INTEGER' if c == 'article_id' else ' TEXT')) for c in SUBENTRY_COLS)}
        )
    """)
    cur.execute('CREATE INDEX idx_subentries_article ON subentries(article_id)')
    for col in ('search_headword', 'search_pos', 'search_definition', 'search_notes',
                'search_loan_source', 'search_all'):
        cur.execute(f'CREATE INDEX idx_articles_{col} ON articles({col})')
        cur.execute(f'CREATE INDEX idx_subentries_{col} ON subentries({col})')

    cur.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)')

    cur.executemany(
        f"INSERT INTO articles ({','.join(ARTICLE_COLS)}) VALUES ({','.join('?' * len(ARTICLE_COLS))})",
        [tuple(a[c] for c in ARTICLE_COLS) for a in articles],
    )
    cur.executemany(
        f"INSERT INTO subentries ({','.join(SUBENTRY_COLS)}) VALUES ({','.join('?' * len(SUBENTRY_COLS))})",
        [tuple(s[c] for c in SUBENTRY_COLS) for s in subentries],
    )

    import datetime
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('built_at', datetime.datetime.now().isoformat()))
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('article_count', str(len(articles))))
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('subentry_count', str(len(subentries))))

    conn.commit()
    conn.execute('VACUUM')
    conn.close()


def write_db_meta(out_path, meta_path, article_count, subentry_count):
    """A tiny sidecar JSON file the website fetches before the (large,
    GitHub-Pages-gzipped) database itself, so it knows the true
    decompressed byte size to show download progress against. GitHub
    Pages always serves a gzip Content-Encoding for files this size, so
    the browser's own Content-Length header is the compressed wire
    size, not the size docs/app.js needs for a meaningful progress bar
    -- same problem, same fix, as ~/GitHub/stedt-static/web/src/search.js
    documents in its fetchDbBytes comment (window.STEDT_DB_BYTES there;
    a separate fetched JSON file here, to avoid templating index.html)."""
    import os
    import datetime
    meta = {
        'bytes': os.path.getsize(out_path),
        'built_at': datetime.datetime.now().isoformat(),
        'article_count': article_count,
        'subentry_count': subentry_count,
    }
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tei_xml', nargs='?', default='generated/tei/lahu.xml')
    ap.add_argument('-o', '--output', default='docs/lahu-dictionary.sqlite3')
    args = ap.parse_args()

    articles, subentries = extract(args.tei_xml)
    build_db(articles, subentries, args.output)

    import os
    meta_path = os.path.join(os.path.dirname(args.output) or '.', 'db-meta.json')
    write_db_meta(args.output, meta_path, len(articles), len(subentries))

    n_loans = sum(1 for a in articles if a['loan_marker']) + sum(1 for s in subentries if s['loan_marker'])
    n_sourced = sum(1 for a in articles if a['loan_source']) + sum(1 for s in subentries if s['loan_source'])
    print(f'Wrote {len(articles)} articles + {len(subentries)} subentries to {args.output}', file=sys.stderr)
    print(f'  {n_loans} rows tagged LOAN/LOAN?, {n_sourced} with an extracted source language', file=sys.stderr)
    print(f'  wrote {meta_path}', file=sys.stderr)


if __name__ == '__main__':
    main()
