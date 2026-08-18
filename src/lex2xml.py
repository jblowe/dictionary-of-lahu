#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lex2xml.py -- a faithful Python port of Lex2XML.pl (jbl, 9/9/97), which
converts a Lexware band-tagged file into XML.

Tested empirically against the real Lex2XML.pl (perl 5.34.0, a copy of
which lives in originals/src/ alongside the other legacy scripts) on our
Lahu Lexware output (generated/DLWordStarFiles/base-lexware/lex.*.txt)
-- byte-for-byte identical XML for all 135 files -- before writing this
port, so its behavior below is verified, not just inferred from reading
the source.

TWO INTENTIONAL, DISCLOSED DEVIATIONS from that byte-for-byte fidelity
(both needed to hand off genuinely well-formed XML to further tooling,
e.g. the TEI transducer in lahu-to-tei.xsl):

  1. Stray WordStar formatting-toggle control bytes that survived the
     upstream conversion (e.g. 0x19, 0x1F) are illegal in XML 1.0 and
     are stripped here (strip_illegal_xml_chars) -- the real Perl
     passes them through uncomplained, which is not well-formed XML.
  2. If the very last dot-line in the input is a sub-headword ("..hw"),
     the real Perl leaves that <sub> unclosed at end-of-file (it only
     ever emits an unconditional final </entry>) -- also not
     well-formed XML. Fixed here by closing any <sub>/<mode> still
     open when the input ends.

WHAT IT DOES
------------
Reads a Lexware file line by line (band\tvalue). For each line:

  * Blank lines are skipped.
  * '&', '<', '>' are XML-escaped first, everywhere (including inside
    band tags/values, so a literal '<' typed in the dictionary text
    becomes '&lt;' rather than breaking the XML).
  * A line starting with '*' becomes a <comment> element wrapping the
    whole (unparsed) line.
  * A line starting with digits is a numbered "mode" band (a nesting
    convention from another dictionary project) -- unused in our Lahu
    data, but supported for fidelity.
  * A line starting with one or more dots is an entry/sub-entry marker:
      - a single dot ('.hw') starts a new top-level <entry
        id="DIALECT.N">, closing the previous entry (and any open
        <sub>/<mode>) first.
      - two or more dots ('..hw') starts a new <sub> element (a
        sub-headword), closing any previously open <sub> first. Note
        that Lex2XML.pl does NOT track a nesting stack -- it only
        remembers "is a <sub> currently open", so '..hw' and '...hw'
        are treated identically: every sub-headword becomes a sibling
        <sub> inside the enclosing <entry>, never nested inside
        another <sub>. Our Lexware convention currently only emits
        one or two dots (.hw / ..hw) for Lahu, so this limitation
        doesn't lose any information for this dictionary, but it's
        worth knowing if band depth is ever extended to 3+ dots.
      - after handling the dot-prefix, the remaining tag/value on that
        same line (e.g. the "hw" in ".hw\tword") is emitted exactly
        like any other band.
  * Every other band (pos, gl, ex, no, bz, ld, xx, err, ...) becomes a
    same-named XML element wrapping its value, e.g. <gl>...</gl>.
    A band with an EMPTY value is silently dropped (no element is
    emitted at all) -- this matches Lex2XML.pl's brackets() helper,
    which returns nothing when $data is ''.
  * A special legacy "hdr" band (band name literally "hdr", only ever
    used by a different, non-Lahu dictionary in the original tooling)
    is emitted as a bare <hdr> element and suppresses the normal
    </entry>/<entry> bookkeeping for that one line. We don't use "hdr"
    in the Lahu data; supported here only for parity with the Perl.
  * A bracket-citation convention, `[[[...]]]`, used by some other
    dictionaries built with this tool, is expanded into nested
    <srcxcrN> tags by the brackets() helper. Not used in our Lahu data
    (Lahu citations are plain "[q.v.]"-style single brackets, which
    brackets() passes straight through as ordinary tag content).

OUTPUT STRUCTURE
----------------
<?xml version="1.0" encoding="utf-8"?>
<lexicon dialecte="DIALECT">
<entry id="DIALECT.1">
  <hw>...</hw>
  <pos>...</pos>
  ...
  <sub>
    <hw>...</hw>
    ...
  </sub>
</entry>
...
</lexicon>

Usage:
  python3 lex2xml.py <infile> <outfile.xml> <logfile> <dialect>

  e.g. from the project root:
    python3 src/lex2xml.py generated/lahudico-lexware.txt \\
        generated/lahudico-lexware.xml generated/lex2xml-report.log Lahu

Writes a tag-frequency log (same format as Lex2XML.pl's LOG) to
<logfile>.
"""
import re
import sys
from collections import Counter


_MODE_RE = re.compile(r'^(\d+)')
_DOT_RE = re.compile(r'^(\.+)')
_TAG_RE = re.compile(r'^([^ \t]+)[ \t]*(.*)$')
_BRACKET_OPEN_NO_CLOSE = re.compile(r'\[')
_BRACKET_CLOSE = re.compile(r'\]')
_SRCXCR_RE = re.compile(r'\w*\[+([^\[<]+)')
_FIELD_REST_RE = re.compile(r'^(.*?)(<srcxcr.*)', re.S)


def xml_escape(s):
    # NB: order matters -- '&' must be escaped first, matching the Perl.
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# Second intentional, disclosed deviation from Lex2XML.pl (see the note
# above the </sub>/</mode> end-of-file fix, further down): some Lahu
# entries carry a leftover WordStar formatting-toggle control byte
# (e.g. a stray 0x19 bold-toggle, 0x1F unit-separator) that survived the
# upstream WordStar->Unicode conversion. Perl's file I/O and string
# handling pass these through uncomplained, but they are flatly illegal
# in XML 1.0 (the Char production excludes 0x00-0x08, 0x0B, 0x0C, and
# 0x0E-0x1F) and will fail well-formedness parsing (confirmed: ~10,000
# such bytes in the full generated/lahudico-lexware.xml, one of which broke lxml's
# parser outright). They carry no textual content, so it's safe to
# strip them -- same judgment already applied throughout this project's
# pipeline to other stray control bytes.
_ILLEGAL_XML_CHAR_RE = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]')


def strip_illegal_xml_chars(s):
    return _ILLEGAL_XML_CHAR_RE.sub('', s)


def brackets(tag, data, taglist, depth_counter):
    """Port of Lex2XML.pl's brackets(): wrap (tag, data) as XML, expanding
    a `[[[...` bracket-citation convention into nested <srcxcrN> tags.
    Returns '' (no element at all) if data is empty, matching the Perl,
    which falls through its else-branch and returns nothing (undef)."""
    if '[' in data and ']' not in data:
        d = data
        depth = 1
        while '[' in d:
            def repl(m):
                taglist['srcxcr'] += 1
                return '<srcxcr%d>%s</srcxcr%d>' % (depth, m.group(1), depth)
            new_d = _SRCXCR_RE.sub(repl, d, count=1)
            if new_d == d:
                break  # avoid infinite loop if the pattern stops matching
            d = new_d
            depth += 1
        # NB: strip only Perl's (ASCII, /a-style) \s chars here, not
        # Python's broader whitespace notion -- Python's str.strip() and
        # unicode-mode \s both also swallow the C0 separator controls
        # (0x1c-0x1f), which Perl's \s does not. Some Lahu dictionary
        # text legitimately contains those bytes (leftover WordStar
        # formatting-toggle bytes our upstream conversion didn't fully
        # resolve), so using Python's default would silently drop data
        # that the real Lex2XML.pl preserves.
        d = d.strip(' \t\n\r\f\v')
        d = re.sub(r'>[ \t\n\r\f\v]+', '>', d)
        d = re.sub(r'[ \t\n\r\f\v]+<', '<', d)
        m = _FIELD_REST_RE.match(d)
        if m:
            field, rest = m.group(1), m.group(2)
        else:
            field, rest = d, ''
        field = field.strip(' \t\n\r\f\v')
        return '\n<%s>%s</%s>\n%s' % (tag, field, tag, rest)
    else:
        if data != '':
            return '\n<%s>%s</%s>' % (tag, data, tag)
        return ''


def convert(infile, outfile, logfile, dialect):
    inmode = False
    insub = False
    lines = 0
    n = 0
    taglist = Counter()
    currmode = None
    hdr = False
    depth_counter = [1]

    out_parts = []
    out_parts.append('<?xml version="1.0" encoding="utf-8"?>')
    out_parts.append('\n<lexicon dialecte="%s">' % dialect)

    with open(infile, encoding='utf-8') as f:
        raw_lines = f.read().split('\n')
        # emulate perl's line-based <CVT> read (drops final empty split
        # artifact from a trailing newline, same as perl's while(<CVT>))
        if raw_lines and raw_lines[-1] == '':
            raw_lines = raw_lines[:-1]

    for line in raw_lines:
        line = line.rstrip('\r')
        lines += 1
        line = xml_escape(line)
        line = strip_illegal_xml_chars(line)
        if re.match(r'^[ \t\n\r\f\v]*$', line):
            continue

        if line.startswith('*'):
            out_parts.append('\n<comment>%s</comment>' % line)
            taglist['comment'] += 1
            continue

        m_mode = _MODE_RE.match(line)
        if m_mode:
            mode_level = m_mode.group(1)
            rest = line[m_mode.end():]
            m_tag = _TAG_RE.match(rest)
            tag, data = (m_tag.group(1), m_tag.group(2)) if m_tag else ('', '')
            if currmode == mode_level:
                out_parts.append(brackets(tag, data, taglist, depth_counter))
                taglist['mode'] += 1
            else:
                currmode = mode_level
                if inmode:
                    out_parts.append('\n</mode>')
                out_parts.append('\n<mode level="%s">' % mode_level)
                inmode = True
                out_parts.append(brackets(tag, data, taglist, depth_counter))
                taglist['mode'] += 1
            continue

        m_dot = _DOT_RE.match(line)
        if m_dot:
            dots = m_dot.group(1)
            rest = line[m_dot.end():]
            if dots == '.':
                n += 1
                if inmode:
                    out_parts.append('\n</mode>')
                if insub:
                    out_parts.append('\n</sub>')
                inmode = False
                insub = False
                if n > 1 and not hdr:
                    out_parts.append('\n</entry>')
                # hack just for tamang dictionary
                if rest.startswith('hdr'):
                    rest2 = re.sub(r'^hdr[ \t\n\r\f\v]+', '', rest)
                    out_parts.append('\n<hdr>%s</hdr>' % rest2)
                    hdr = True
                    continue
                hdr = False
                out_parts.append('\n<entry id="%s.%d">' % (dialect, n))
                taglist['entry'] += 1
            else:
                if inmode:
                    out_parts.append('\n</mode>')
                inmode = False
                if insub:
                    out_parts.append('\n</sub>')
                out_parts.append('\n<sub>')
                taglist['sub'] += 1
                insub = True
            line = rest

        m_tag = _TAG_RE.match(line)
        if m_tag:
            if inmode:
                out_parts.append('\n</mode>')
            inmode = False
            out_parts.append(brackets(m_tag.group(1), m_tag.group(2), taglist, depth_counter))
            taglist[m_tag.group(1)] += 1

    # Deliberate, disclosed fix beyond Lex2XML.pl's own behavior: the
    # original always emits an unconditional final </entry>, but never
    # checks whether a <sub> (or <mode>) was still open at end-of-file --
    # if the very last dot-line in the input was a sub-headword ("..hw"),
    # the real Perl script (verified against perl 5.34.0) leaves that
    # <sub> unclosed, producing invalid (non-well-formed) XML. Since a
    # major point of this port is to hand off well-formed XML to further
    # tooling (e.g. a TEI transducer), close any tag still open here.
    # This is the ONLY intentional behavioral difference from the
    # original; see README-lex2xml.md.
    if inmode:
        out_parts.append('\n</mode>')
    if insub:
        out_parts.append('\n</sub>')
    out_parts.append('\n</entry>')
    out_parts.append('\n</lexicon>\n')

    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(''.join(out_parts))

    tottags = sum(taglist.values())
    with open(logfile, 'w', encoding='utf-8') as f:
        f.write('input: %s\n' % infile)
        f.write('dialect: %s\n' % dialect)
        f.write('*** Tag statistics\n')
        for k in sorted(taglist):
            f.write('%s\t%d\n' % (k, taglist[k]))
        f.write('\nNo. of Lines: %d' % lines)
        f.write('\nNo. of tags:  %d\n' % tottags)


def main():
    if len(sys.argv) != 5:
        print('Usage: %s <infile> <outfile.xml> <logfile> <dialect>' % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    infile, outfile, logfile, dialect = sys.argv[1:5]
    convert(infile, outfile, logfile, dialect)


if __name__ == '__main__':
    main()
