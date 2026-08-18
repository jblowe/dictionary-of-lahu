#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stedt_convert.py -- a faithful Python port of STEDT5-U4Map-7.plx (Richard
Cook / Dominic Yu), which converts text in the Mac "STEDTFont 5.1" custom
font to Unicode 4.0. Ported to run directly on the authentic 1994
LahuParse.pl output found in originals/DLLexwareFiles/ (single-byte
STEDT-font encoding, CR line endings), producing modern Unicode .txt
files in generated/DLLexwareFiles-plaintext/.

WHY A SEPARATE SCRIPT FROM dl_convert.py
-----------------------------------------
dl_convert.py reconstructs Lexware output FROM SCRATCH from the raw
WordStar files, using a DL-ASCII -> Unicode table that skips the STEDT
font as an intermediate step entirely. The files in
originals/DLLexwareFiles/ are a different, independent artifact: the
*actual* Lexware output produced by the real 1994 LahuParse.pl, already
in STEDT-font encoding. Converting *that* faithfully requires this
script -- a port of the *other* original Perl script,
STEDT5-U4Map-7.plx -- not dl_convert.py's DL-ASCII table. Having both
conversions of the same underlying dictionary is a useful cross-check.

WHAT THE ORIGINAL SCRIPT DOES (byte-level, before final Unicode remapping)
----------------------------------------------------------------------------
STEDTFont 5.1 is a single-byte (Mac Roman-like) font. Its combining
diacritics are stored BEFORE the base character (a artifact of the
original CP/M "type base char, backspace, type diacritic" keystroke
sequence). Converting this to Unicode (where combining marks follow the
base character) takes several ordered passes, all performed on the RAW
BYTES first (each byte treated as one "character", Latin-1 style) before
anything is mapped to real Unicode:

  1. Collapse immediately-duplicated diacritic bytes (typos).
  2. If the line contains any "high diacritic" byte (0x9F, 0xFF, 0xFC,
     0xCE, 0xE1, 0xAB, 0xCF -- these must sort after ordinary diacritics
     within a run), stable-sort every diacritic run in the line so
     ordinary diacritics come first and high diacritics come last.
  3. Insert a space between a diacritic byte and a following tab/end of
     line (so a "bare" trailing diacritic doesn't fuse with nothing).
  4. Reorder: a run of diacritic bytes immediately followed by a
     non-diacritic byte is swapped to non-diacritic-then-diacritics (the
     actual before-to-after reordering).
  5. Only now, remap every diacritic/remapping byte to its real Unicode
     string, via the STEDTFont 5.1 <-> Unicode 4.0 table.
  6. Two small Unicode-level cleanups: dotless-i is no longer needed once
     a real Unicode combining mark can sit cleanly over a normal "i", so
     "ı" + tone-mark reverts to "i" + tone-mark; and a bare diacritic that
     ended up preceded by a space (step 3) is rendered as the
     corresponding free-standing "modifier letter" glyph instead of an
     unattached combining mark.

Usage:
  python3 stedt_convert.py <STEDT5-U4Map-7.plx-path> <input-directory> [output-directory]

  e.g. from the project root:
    python3 src/stedt_convert.py originals/src/STEDT5-U4Map-7.plx \\
        originals/DLLexwareFiles generated/DLLexwareFiles-plaintext

Writes "<filename>.txt" for every non-.txt file in <input-directory> into
<output-directory> (defaults to <input-directory> itself, for backward
compatibility, but the standard invocation above keeps generated output
out of originals/ entirely).
"""
import os
import re
import sys
import unicodedata


def parse_stedt_map(plx_path):
    """Parse the __DATA__ table of STEDT5-U4Map-7.plx into
    byte_as_latin1_char -> (unicode_replacement_string, comb_class)."""
    text = open(plx_path, encoding='utf-8').read()
    data = text.split('__DATA__\n', 1)[1]
    stedt = {}
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
        stedt[chr(byte)] = (uni_str, int(comb))
    return stedt


class SteddtFont:
    def __init__(self, plx_path):
        self.map = parse_stedt_map(plx_path)
        self.diac_chars = sorted(c for c, (u, comb) in self.map.items() if comb == 1)
        self.hash_chars = sorted(c for c, (u, comb) in self.map.items() if comb in (1, 2))
        self.high_diac = set('\x9f\xff\xfc\xce\xe1\xab\xcf')

        d_class = ''.join(re.escape(c) for c in self.diac_chars)
        h_class = ''.join(re.escape(c) for c in self.hash_chars)
        self._dup_re = re.compile('([' + d_class + '])\\1')
        self._diac_run_re = re.compile('[' + d_class + ']+')
        self._trailing_re = re.compile('([' + d_class + '])(\t|$)', re.M)
        self._reorder_re = re.compile('([' + d_class + ']+)([^' + d_class + '])')
        self._hash_re = re.compile('[' + h_class + ']')

    # -- byte-level passes (operate on a Latin-1 "byte string") --

    def _dedup(self, line):
        while True:
            new = self._dup_re.sub(r'\1', line)
            if new == line:
                return line
            line = new

    def _sort_high_diac(self, line):
        if not any(c in self.high_diac for c in line):
            return line

        def repl(m):
            run = m.group(0)
            # stable sort: ordinary diacritics first, high diacritics last
            return ''.join(sorted(run, key=lambda c: c in self.high_diac))
        return self._diac_run_re.sub(repl, line)

    def _space_before_trailing(self, line):
        return self._trailing_re.sub(r'\1 \2', line)

    def _reorder_diac_before_base(self, line):
        return self._reorder_re.sub(lambda m: m.group(2) + m.group(1), line)

    def _remap(self, line):
        return self._hash_re.sub(lambda m: self.map[m.group(0)][0], line)

    # -- unicode-level cleanup, applied after remapping --

    _DOTLESS_I_RE = re.compile(
        'ı(̱)?([̄́̃̀̈̌̂̆])')
    _STANDALONE = [
        (' ̄', 'ˉ'),  # space+combining macron -> modifier letter macron
        (' ́', 'ˊ'),  # space+combining acute -> modifier letter acute
        (' ̀', 'ˋ'),  # space+combining grave -> modifier letter grave
        (' ̌', 'ˇ'),  # space+combining caron -> caron
        (' ̂', 'ˆ'),  # space+combining circumflex -> modifier letter circumflex
        (' ̱', 'ˍ'),  # space+combining macron below -> modifier letter low macron
    ]

    def _unicode_cleanup(self, line):
        line = self._DOTLESS_I_RE.sub(lambda m: 'i' + (m.group(1) or '') + m.group(2), line)
        for pat, repl in self._STANDALONE:
            line = line.replace(pat, repl)
        return line

    def convert_line(self, line):
        line = self._dedup(line)
        line = self._sort_high_diac(line)
        line = self._space_before_trailing(line)
        line = self._reorder_diac_before_base(line)
        line = self._remap(line)
        line = self._unicode_cleanup(line)
        return line

    def convert_text(self, raw_bytes: bytes) -> str:
        # STEDTFont is a single-byte encoding; decode 1 byte <-> 1 char (Latin-1)
        text = raw_bytes.decode('latin-1')
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')
        converted = [self.convert_line(line) for line in lines]
        result = '\n'.join(converted)
        return unicodedata.normalize('NFC', result)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <STEDT5-U4Map-7.plx> <input-directory> [output-directory]",
              file=sys.stderr)
        sys.exit(1)
    plx_path, directory = sys.argv[1], sys.argv[2]
    out_directory = sys.argv[3] if len(sys.argv) > 3 else directory
    os.makedirs(out_directory, exist_ok=True)

    font = SteddtFont(plx_path)

    files = sorted(f for f in os.listdir(directory)
                   if os.path.isfile(os.path.join(directory, f)) and not f.endswith('.txt'))
    n = 0
    for fn in files:
        src = os.path.join(directory, fn)
        raw = open(src, 'rb').read()
        text = font.convert_text(raw)
        dst = os.path.join(out_directory, fn + '.txt')
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(text)
        n += 1
    print(f"Converted {n} files from {directory} into {out_directory}")


if __name__ == '__main__':
    main()
