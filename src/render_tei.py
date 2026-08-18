#!/usr/bin/env python3
"""
render_tei.py — Apply an XSLT stylesheet to an XML document.

Usage (paths relative to the project root):
    python3 src/render_tei.py --tei generated/lahudico-lexware.xml --xsl src/lahu-to-tei.xsl --out generated/tei/lahu.xml
    python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-html.xsl  --out generated/latex/lahu.html
    python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-latex.xsl --out generated/latex/lahu.tex \
        [--param show-editorial-notes 1] [--param body-font "Charis SIL"]

Generic: works with any XSLT 1.0 stylesheet and any well-formed input,
not just TEI -- the --tei flag is just named for the common case. Uses
lxml (no xsltproc dependency). Reports any XSLT messages/errors.

One thing this script does beyond a bare lxml.etree.XSLT call: it
strips a handful of XML-illegal C0 control bytes (0x00-0x08, 0x0B, 0x0C,
0x0E-0x1F) before parsing. These are leftover WordStar formatting-toggle
bytes that neither the original nor our ported Lex2XML.pl/lex2xml.py
filter out (see README-lex2xml.md) -- passing raw bytes through is not
a bug there (it preserves the fidelity of that port to the original
Perl's real behavior), but it does mean the *files themselves* aren't
guaranteed well-formed XML, so this loader sanitizes on the way in
rather than requiring every downstream consumer to know that.
"""
import argparse
import os
import re
import sys
from lxml import etree

# See docstring above: illegal in XML 1.0's Char production, safe to
# strip (carries no textual content -- same judgment already applied
# throughout this project's pipeline to other stray control bytes).
_ILLEGAL_XML_CHAR_RE = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]')


def load_xml(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    cleaned = _ILLEGAL_XML_CHAR_RE.sub('', text)
    if cleaned != text:
        n = len(text) - len(cleaned)
        print(f"[render] stripped {n} illegal XML control byte(s) from {path}", file=sys.stderr)
    return etree.fromstring(cleaned.encode('utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tei", required=True, help="input XML (TEI or otherwise)")
    ap.add_argument("--xsl", required=True, help="XSLT stylesheet")
    ap.add_argument("--out", required=True, help="output file")
    ap.add_argument("--param", nargs=2, action="append", metavar=("NAME", "VALUE"),
                     default=[], help="XSLT stylesheet parameter (repeatable)")
    args = ap.parse_args()

    for p in (args.tei, args.xsl):
        if not os.path.isfile(p):
            sys.exit(f"[render] ERROR: missing file: {p}")

    src = load_xml(args.tei)
    xslt = etree.parse(args.xsl)
    transform = etree.XSLT(xslt)

    params = {name: etree.XSLT.strparam(value) for name, value in args.param}
    result = transform(src, **params)

    for entry in transform.error_log:
        print(f"[render] xslt: {entry.message}", file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(bytes(result))
    print(f"[render] wrote {args.out} ({os.path.getsize(args.out):,} bytes)")


if __name__ == "__main__":
    main()
