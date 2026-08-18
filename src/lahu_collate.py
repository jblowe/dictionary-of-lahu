#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lahu_collate.py -- sort-key logic for Lahu headwords, per the authoritative
collation order confirmed by the project owner (decoded from the
".FO" running-footer line in originals/DLOtherFiles/HEADER):

    a  a-acute  a-circumflex  a-grave  a-macron  a-circumflex-glottal  a-grave-glottal
    (i.e. the 7 tones: mid, high-rising, high-falling, low-falling, very-low,
     high-checked, low-checked -- illustrated on the vowel "a")

    a i u e o ɛ ɔ ɨ ə                                    (the 9 vowels, in order)

    q qh k kh g ŋ c ch j t th d n p ph b m h g̈ š y f v l  (the consonants, in order;
                                                            "no consonant" i.e.
                                                            vowel-initial sorts first)

A Lahu syllable is parsed as: [consonant] vowel [tone-diacritic] [glottal-stop].
Precomposed Latin vowel+diacritic (á, à, â, ā ...) are decomposed (NFD) first
so every vowel -- Latin or IPA-extension -- is handled the same way: a bare
vowel letter optionally followed by a combining diacritic.
"""
import re
import unicodedata

# Consonants in collation order. Longer (digraph) entries MUST be checked
# before any single-letter entry they'd otherwise collide with (qh before q,
# kh before k, ch before c, th before t, ph before p), and the two
# diacritic-bearing consonants (g-umlaut "g̈", s-hacheck "š") must be checked
# in their full (NFD, 2-codepoint) form before the bare letter they start
# with (plain "g" would otherwise wrongly match the first codepoint of "g̈").
_CONSONANTS_NFD = [
    'qh', 'kh', 'ch', 'th', 'ph',                 # digraphs, longest-match-first
    'g' + '̈',                                # g̈ (voiced velar fricative)
    's' + '̌',                                # š (esh)
    'ŋ',                                      # ŋ (eng) -- single codepoint
    'q', 'k', 'g', 'c', 'j', 't', 'd', 'n', 'p', 'b', 'm', 'h', 'y', 'f', 'v', 'l',
]
_CONSONANT_INDEX = {
    'q': 0, 'qh': 1, 'k': 2, 'kh': 3, 'g': 4, 'ŋ': 5, 'c': 6, 'ch': 7,
    'j': 8, 't': 9, 'th': 10, 'd': 11, 'n': 12, 'p': 13, 'ph': 14, 'b': 15,
    'm': 16, 'h': 17, 'g' + '̈': 18, 's' + '̌': 19,
    'y': 20, 'f': 21, 'v': 22, 'l': 23,
}
NO_CONSONANT = -1  # vowel-initial sorts before every consonant

VOWELS = ['a', 'i', 'u', 'e', 'o', 'ɛ', 'ɔ', 'ɨ', 'ə']
# ɛ=0x25B  ɔ=0x254  ɨ=0x268  ə=0x259
_VOWEL_INDEX = {v: i for i, v in enumerate(VOWELS)}

# tone diacritic (combining mark) + checked(glottal) flag -> tone index
_TONE_INDEX = {
    (None, False): 0,        # mid (unmarked)
    ('́', False): 1,    # high-rising (acute)
    ('̂', False): 2,    # high-falling (circumflex)
    ('̀', False): 3,    # low-falling (grave)
    ('̄', False): 4,    # very-low (macron)
    ('̂', True): 5,     # high-checked (circumflex + glottal)
    ('̀', True): 6,     # low-checked (grave + glottal)
}
_KNOWN_COMBINING = {'́', '̂', '̀', '̄'}
GLOTTAL = 'ʔ'  # ʔ


class ParseFailure(Exception):
    pass


def parse_initial_syllable(word: str):
    """Parse the leading syllable of a (NFC) Lahu word. Returns
    (consonant_index_or_NO_CONSONANT, vowel_index, tone_index, matched_text).
    Raises ParseFailure if the word doesn't start with a recognizable
    Lahu consonant/vowel (e.g. it's a citation form, punctuation, etc.)."""
    nfd = unicodedata.normalize('NFD', word)

    consonant_index = NO_CONSONANT
    rest = nfd
    for cand in _CONSONANTS_NFD:
        if nfd.startswith(cand):
            consonant_index = _CONSONANT_INDEX[cand]
            rest = nfd[len(cand):]
            break

    if not rest:
        raise ParseFailure(f"nothing after consonant in {word!r}")
    vowel = rest[0]
    if vowel not in _VOWEL_INDEX:
        raise ParseFailure(f"no recognizable vowel in {word!r} (rest={rest!r})")
    vowel_index = _VOWEL_INDEX[vowel]
    rest = rest[1:]

    comb = None
    if rest and rest[0] in _KNOWN_COMBINING:
        comb = rest[0]
        rest = rest[1:]
    checked = bool(rest and rest[0] == GLOTTAL)
    if checked:
        rest = rest[1:]

    tone_index = _TONE_INDEX.get((comb, checked))
    if tone_index is None:
        # unexpected tone/glottal combination -- still return a key (put it
        # at the end of the tone range) rather than failing outright
        tone_index = 7

    matched_len = len(nfd) - len(rest)
    matched_text = unicodedata.normalize('NFC', nfd[:matched_len])
    return consonant_index, vowel_index, tone_index, matched_text


def first_word(headword: str) -> str:
    """Extract the first Lahu 'word' out of a headword field, which may
    contain compound elements, alternate forms (~), cross-references, etc.
    We only need the very first syllable-bearing token."""
    # strip anything from the first separator onward: space, ~, =, hyphen
    # is a MORPHEME separator within a single word in this dictionary's
    # transcription (compounds are hyphenated), so keep hyphenated material
    # attached but stop at the first space or ~ or =.
    m = re.match(r"^\s*(\S+)", headword)
    token = m.group(1) if m else headword
    token = re.split(r'[~=]', token)[0]
    return token


def sort_key(headword: str):
    """Full collation sort key for a headword string, for use as a Python
    sort key (tuple of ints, plus the matched text and the full headword as
    final tie-breakers)."""
    token = first_word(headword)
    try:
        c, v, t, matched = parse_initial_syllable(token)
    except ParseFailure:
        # Fall back: sort unparsable headwords after everything else,
        # alphabetically among themselves, rather than crashing.
        return (999, 999, 999, headword, headword)
    return (c, v, t, matched, headword)


def initial_label(headword: str) -> str:
    """A short human-readable label for the initial syllable's consonant+
    vowel (ignoring tone) -- e.g. 'qh+a', '(none)+a' -- used to group files
    in the ordering spreadsheet."""
    token = first_word(headword)
    try:
        c, v, t, matched = parse_initial_syllable(token)
    except ParseFailure:
        return '?'
    cname = None
    for k, idx in _CONSONANT_INDEX.items():
        if idx == c:
            cname = unicodedata.normalize('NFC', k)
            break
    if c == NO_CONSONANT:
        cname = '(vowel)'
    return f"{cname}{VOWELS[v]}"


if __name__ == '__main__':
    # quick self-test against a few known forms
    tests = ['qə-lə', 'qə̀', 'qə̂ʔ-lə̂ʔ', 'nɛ', 'g̈û-nɛ', 'šɔ̄=qə̂ʔ-lə̂ʔ', 'a-kɛ́']
    for t in tests:
        print(t, '->', sort_key(t), initial_label(t))
