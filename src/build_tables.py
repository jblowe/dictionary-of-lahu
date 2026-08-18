#!/usr/bin/env python3
"""
Parses the two legacy Perl scripts (STEDT5-U4Map-7.plx, LahuParse.pl) and
derives, programmatically, a single DL-ASCII -> Unicode mapping table for
the Lahu phonetic substitute characters, skipping the STEDT-font
intermediate stage entirely.

This is a one-time table-building / auditing step -- it shows exactly how
the LAHU_UNICODE table baked into dl_convert.py was derived from the two
original scripts, and can be re-run to double-check it (or regenerate it
if either source script is ever revised).

Usage:
    python3 build_tables.py [directory-containing-the-two-legacy-files]

Defaults to originals/src/ (relative to this script's own location,
i.e. src/../originals/src), which is where STEDT5-U4Map-7.plx and
LahuParse.pl live in the project's originals/generated/src layout; pass
an explicit directory to point at a copy elsewhere. Writes
merged_table.py (a throwaway audit artifact, not used by the rest of the
pipeline) into the current working directory.
"""
import os
import re
import sys

# ---------------------------------------------------------------
# 1. Parse STEDT5-U4Map-7.plx  __DATA__  section
#    columns: DEC  HEX  USV(s)  UNAME  COMB
#    COMB: 0 = unchanged base char, 1 = diacritic (combining), 2 = base char that remaps
# ---------------------------------------------------------------
def parse_stedt_map(path):
    text = open(path, encoding='utf-8').read()
    data = text.split('__DATA__\n', 1)[1]
    stedt = {}  # int (0-255) -> (unicode_str, comb:int)
    for line in data.splitlines():
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) != 5:
            continue
        dec, hexcode, usv_field, uname, comb = parts
        byte = int(hexcode, 16)
        usvs = re.findall(r'\[U\+([0-9A-Fa-f]{1,6})\]', usv_field)
        uni_str = ''.join(chr(int(u, 16)) for u in usvs)
        stedt[byte] = (uni_str, int(comb))
    return stedt


# ---------------------------------------------------------------
# 2. Parse LahuParse.pl  $stedt_char{'X'} = "\xNN\xNN...";  assignments
#    and the $unchanged string.
# ---------------------------------------------------------------
def parse_stedt_char_table(path):
    lines = open(path, encoding='latin-1').readlines()
    # drop commented-out lines (e.g. the backspace entry is intentionally disabled)
    text = ''.join(l for l in lines if not l.lstrip().startswith('#'))
    table = {}  # dl_ascii_char -> list[int] of STEDT byte(s)
    # match:  $stedt_char{'X'} = "....";   (X may itself be an escaped quote/backslash)
    pat = re.compile(r"""\$stedt_char\{'((?:\\.|[^'\\])+)'\}\s*=\s*"((?:\\.|[^"\\])*)"\s*;""")
    for m in pat.finditer(text):
        keyraw, valraw = m.group(1), m.group(2)
        key = perl_unescape_single(keyraw)
        bytelist = perl_unescape_double_to_bytes(valraw)
        table[key] = bytelist
    return table


def perl_unescape_single(s):
    # single-quoted perl string: only \\ and \' are escapes
    return s.replace(r"\\", "\\").replace(r"\'", "'")


def perl_unescape_double_to_bytes(s):
    """Turn a perl double-quoted string body into a list of byte values.
    Handles \\xHH hex escapes and literal characters (assumed latin-1 / ASCII)."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            nxt = s[i+1]
            if nxt == 'x':
                hexdigits = s[i+2:i+4]
                out.append(int(hexdigits, 16))
                i += 4
                continue
            elif nxt == '\\':
                out.append(ord('\\'))
                i += 2
                continue
            elif nxt == '"':
                out.append(ord('"'))
                i += 2
                continue
            else:
                out.append(ord(nxt))
                i += 2
                continue
        else:
            out.append(ord(c))
            i += 1
    return out


def parse_unchanged(path):
    text = open(path, encoding='latin-1').read()
    # $unchanged =  '...' . '...' . '...' . "w*rs\'&z/\x19";
    m = re.search(r"\$unchanged\s*=\s*(.+?);\n", text, re.S)
    assert m, "couldn't find $unchanged"
    expr = m.group(1)
    # split on . (concatenation) at top level, respecting quotes
    parts = re.findall(r"'((?:\\.|[^'\\])*)'|\"((?:\\.|[^\"\\])*)\"", expr)
    chars = []
    for sq, dq in parts:
        if sq:
            chars.extend(perl_unescape_single(sq))
        else:
            for b in perl_unescape_double_to_bytes(dq):
                chars.append(chr(b))
    return chars


def compose_unicode(bytelist, stedt):
    """Compose a STEDT byte-sequence (diacritic-BEFORE-base, per STEDT font
    convention) into a Unicode string with the diacritic AFTER the base
    character (Unicode combining-mark convention)."""
    if len(bytelist) == 1:
        uni, comb = stedt[bytelist[0]]
        return uni
    if len(bytelist) == 2:
        u0, c0 = stedt[bytelist[0]]
        u1, c1 = stedt[bytelist[1]]
        if c0 == 1 and c1 != 1:
            return u1 + u0          # swap: base then diacritic
        if c1 == 1 and c0 != 1:
            return u0 + u1          # already base then diacritic
        # neither/both diacritics -- just concatenate, flag for review
        return u0 + u1
    # longer sequences: naive concatenation (none observed in practice)
    return ''.join(stedt[b][0] for b in bytelist)


if __name__ == '__main__':
    default_legacy_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'originals', 'src')
    legacy_dir = sys.argv[1] if len(sys.argv) > 1 else default_legacy_dir
    stedt_path = os.path.join(legacy_dir, 'STEDT5-U4Map-7.plx')
    lahuparse_path = os.path.join(legacy_dir, 'LahuParse.pl')

    stedt = parse_stedt_map(stedt_path)
    print(f"STEDT map: {len(stedt)} byte entries")

    table = parse_stedt_char_table(lahuparse_path)
    print(f"stedt_char table: {len(table)} DL-ASCII entries")

    unchanged = parse_unchanged(lahuparse_path)
    print(f"$unchanged has {len(unchanged)} chars: {''.join(unchanged)!r}")

    missing = set()
    for k, bl in table.items():
        for b in bl:
            if b not in stedt:
                missing.add(b)
    print("Bytes referenced but missing from STEDT map:", [hex(b) for b in sorted(missing)])

    print("\n--- Merged DL-ASCII -> Unicode table ---")
    merged = {}
    for k in sorted(table):
        uni = compose_unicode(table[k], stedt)
        merged[k] = uni
        names = ' + '.join(f"U+{ord(c):04X}" for c in uni)
        print(f"  {k!r:6s} -> {uni!r:12s} ({names})")

    # write out as a python literal for re-use
    with open('merged_table.py', 'w', encoding='utf-8') as f:
        f.write("# Auto-generated by build_tables.py -- DO NOT EDIT BY HAND\n")
        f.write("DL_ASCII_TO_UNICODE = {\n")
        for k in sorted(merged):
            f.write(f"    {k!r}: {merged[k]!r},\n")
        f.write("}\n")
        f.write(f"\nUNCHANGED_CHARS = {''.join(unchanged)!r}\n")
    print("\nWrote merged_table.py")
