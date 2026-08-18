<?xml version="1.0" encoding="UTF-8"?>
<!--
  lahu-html.xsl
  XSLT 1.0 stylesheet: TEI Lex-0 (generated/tei/lahu.xml) to HTML5.

  Usage: see README-tei.md. Adapted from the Jaschke Tibetan-English
  Dictionary project's xslt/jaschke-html.xsl (same workspace): same
  overall approach (two-column CSS "page" look, an xsl:param to toggle
  pipeline editorial notes), simplified for Lahu's single Latin-based
  script (no dual Tibetan/roman orth line needed) and extended for the
  TEI elements this dictionary's data actually uses: usg (loanword flag
  and bracketed register/dialect labels), multiple cit/quote example-
  translation pairs per entry, and sense/@n numbering.
-->
<xsl:stylesheet
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei="http://www.tei-c.org/ns/1.0"
  xmlns:xml="http://www.w3.org/XML/1998/namespace"
  exclude-result-prefixes="tei">

  <xsl:output
    method="html"
    version="5"
    encoding="UTF-8"
    indent="yes"
    doctype-system="about:legacy-compat"/>

  <!-- Set to 1 to show pipeline editorial notes in gray; 0 to suppress -->
  <xsl:param name="show-editorial-notes">0</xsl:param>


  <!-- ══════════════════════════════════════════════════════════════════════
       ROOT
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>The Dictionary of Lahu &#8212; J. A. Matisoff (1988)</title>

        <style>
/* ── Base ──────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

:root {
  /* One indent unit; sub-entries sit one unit deeper than entries, and
     each level's own wrapped (hanging-indent) lines sit one further
     unit beyond where that level's first line starts. */
  --indent: 1.3em;
}

body {
  /* A conventional system serif with solid Unicode coverage (IPA
     Extensions, Latin Extended, combining diacritical marks) rather
     than a webfont -- Lahu's tone marks are combining accents over
     both vowels and consonants (e.g. g with a combining diaeresis,
     g̈), and some historically common serif webfonts render those
     combining sequences poorly (missing glyphs, misplaced marks).
     DejaVu Serif is the same font used for the PDF edition (see
     lahu-latex.xsl) and is commonly preinstalled on Linux; Georgia
     and Times New Roman are reliable, widely available fallbacks with
     decent (if not perfect) coverage on macOS/Windows. */
  font-family: 'DejaVu Serif', Georgia, 'Times New Roman', serif;
  font-size: 10.5pt;
  line-height: 1.4;
  color: #1a1a1a;
  background: #faf8f4;
  margin: 0;
  padding: 0;
}

/* ── Page layout ────────────────────────────────────────────────────────── */
.page-title {
  text-align: center;
  padding: 2rem 1rem 1rem;
  border-bottom: 1px solid #ccc;
  margin-bottom: 1.5rem;
}
.page-title h1 { font-size: 1.4rem; margin: 0 0 0.2rem; }
.page-title .subtitle { font-style: italic; font-size: 1rem; }
.page-title .author { font-size: 0.9rem; color: #555; margin-top: 0.3rem; }

.dictionary {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 1rem 3rem;
  column-count: 2;
  column-gap: 2.5rem;
  column-rule: 1px solid #ddd;
}

@media (max-width: 700px) {
  .dictionary { column-count: 1; }
}

/* ── Dictionary entry ───────────────────────────────────────────────────── */
/* Hanging indent, two levels deep: a top-level entry's own wrapped
   lines indent to --indent (the same column where its sub-entries'
   headwords start); a sub-entry's first line starts at --indent, and
   ITS wrapped lines indent one further unit, to 2 * --indent. This
   applies to the headword/sense line itself. Notes and examples are
   both indented one further level than the headword/sense line they
   belong to -- see the .note and .example rules below. */
.entry {
  padding-left: var(--indent);
  text-indent: calc(-1 * var(--indent));
  margin: 0 0 0.7rem;
  break-inside: avoid-column;
}
.entry > .example { margin: 0.15em 0 0 0; }
.entry > .note { margin: 0.15em 0 0 0; }

.hw {
  font-weight: bold;
  font-size: 1.05em;
  margin-right: 0.35em;
}

.gram {
  font-style: italic;
  font-size: 0.92em;
  color: #333;
  margin-right: 0.35em;
}

.usg {
  font-style: italic;
  font-size: 0.92em;
  margin-right: 0.35em;
}
.usg::before { content: '['; }
.usg::after { content: ']'; }

.sense-num {
  font-weight: bold;
  margin-right: 0.2em;
}
.sense {
  display: inline;
}
.sense + .sense::before { content: ' '; }

.def { display: inline; }

/* A note or example is indented one full level deeper than the
   headword/sense line it belongs to, not flush with it: at the
   top level that line starts at 0 and wraps to --indent, so its
   notes/examples start at --indent (where its sub-entries start)
   and wrap to 2 * --indent; a sub-entry's own line starts at
   --indent and wraps to 2 * --indent, so ITS notes/examples start at
   2 * --indent and wrap to 3 * --indent (see the sub-entry rules
   below). */
.note {
  display: block;
  font-size: 0.92em;
  color: #444;
}
.entry > .note {
  padding-left: calc(2 * var(--indent));
  text-indent: calc(-1 * var(--indent));
}
.note::before { content: '/ '; }
.note::after { content: ' /'; }

.example {
  display: block;
  font-size: 0.95em;
}
.entry > .example {
  padding-left: calc(2 * var(--indent));
  text-indent: calc(-1 * var(--indent));
}
/* The Lahu portion of an example is set 2pt smaller still, same
   "-2pt from the surrounding context" treatment as the sub-entry
   headword rule above -- keeps it visually distinct from the English
   translation sharing the same line. */
.example .lahu { font-style: italic; font-size: calc(1em - 2pt); }
.example .gloss { color: #333; }
.example .gloss::before { content: ' '; }

/* Sub-entry (related entry / compound form): one indent unit deeper
   than its parent entry, with its own (deeper) hanging indent for
   wrapped lines. */
.sub-entry {
  margin-left: var(--indent);
  padding-left: var(--indent);
  text-indent: calc(-1 * var(--indent));
}
.sub-entry > .note {
  margin-left: var(--indent);
  padding-left: calc(2 * var(--indent));
  text-indent: calc(-1 * var(--indent));
}
.sub-entry > .example {
  margin-left: var(--indent);
  padding-left: calc(2 * var(--indent));
  text-indent: calc(-1 * var(--indent));
}
.sub-entry { margin-top: 0.2rem; }
.sub-entry > .note, .sub-entry > .example { margin-top: 0.15em; }
.sub-entry .hw { font-weight: bold; font-style: normal; font-size: calc(1.05em - 2pt); }

/* Letter divider ("PUT x HERE" in the original typesetting instructions):
   a full-width ornamental break announcing a new letter-section.
   column-span: all pulls it out of whichever column it happens to fall
   in -- even nested inside .entry/.sub-entry, since it's still an
   in-flow block-level descendant of .dictionary -- and splits the two
   columns at that point. */
.letter-divider {
  column-span: all;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin: 1.6rem 0 1.2rem;
  padding-left: 0;
  text-indent: 0;
  break-inside: avoid;
}
.letter-divider::before,
.letter-divider::after {
  content: '';
  flex: 1 1 auto;
  height: 1px;
  background: #bba;
}
.letter-divider .divider-letter {
  flex: 0 0 auto;
  font-family: Georgia, 'Times New Roman', serif;
  font-weight: bold;
  font-style: italic;
  font-size: 2.4rem;
  line-height: 1;
  color: #6b5636;
  padding: 0 0.2em;
}

/* Editorial notes (pipeline artifacts, shown only in review mode) */
.editorial-note {
  display: block;
  font-size: 0.8em;
  color: #888;
  background: #f0f0f0;
  border-left: 3px solid #ccc;
  padding: 0.2em 0.5em;
  margin: 0.2em 0;
}
.editorial-note::before { content: none; }
        </style>
      </head>

      <body>
        <div class="page-title">
          <h1>The Dictionary of Lahu</h1>
          <div class="subtitle">James A. Matisoff (1988)</div>
          <div class="author">TEI Lex-0 digital edition</div>
        </div>

        <div class="dictionary">
          <xsl:apply-templates select="//tei:div[@type='dictionary']/tei:entry"/>
        </div>
      </body>
    </html>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       ENTRY
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:entry">
    <div class="entry">
      <xsl:attribute name="id">
        <xsl:value-of select="@xml:id"/>
      </xsl:attribute>

      <span class="hw"><xsl:value-of select="tei:form/tei:orth"/></span>

      <xsl:if test="tei:gramGrp/tei:gram">
        <span class="gram"><xsl:value-of select="tei:gramGrp/tei:gram"/></span>
      </xsl:if>

      <xsl:apply-templates select="tei:usg"/>
      <xsl:apply-templates select="tei:sense"/>
      <xsl:apply-templates select="tei:note[not(@type='editorial')]"/>
      <xsl:if test="$show-editorial-notes='1'">
        <xsl:apply-templates select="tei:note[@type='editorial']"/>
      </xsl:if>
      <xsl:apply-templates select="tei:cit[@type='example']"/>
      <xsl:apply-templates select="tei:re"/>
      <xsl:apply-templates select="tei:milestone"/>
    </div>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       USAGE LABEL (etym = loanword flag; label = bracketed register/
       dialect/cross-ref annotation)
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:usg[@type='etym']">
    <span class="usg etym"><xsl:value-of select="."/></span>
  </xsl:template>
  <xsl:template match="tei:usg[@type='label']">
    <span class="usg"><xsl:value-of select="."/></span>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       SENSE
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:sense">
    <span class="sense">
      <xsl:if test="@n">
        <span class="sense-num"><xsl:value-of select="@n"/>.</span>
      </xsl:if>
      <span class="def"><xsl:value-of select="tei:def"/></span>
    </span>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       NOTE
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:note[not(@type='editorial')]">
    <span class="note"><xsl:value-of select="."/></span>
  </xsl:template>

  <xsl:template match="tei:note[@type='editorial']">
    <span class="editorial-note"><xsl:value-of select="."/></span>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       EXAMPLE + TRANSLATION
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:cit[@type='example']">
    <span class="example">
      <span class="lahu"><xsl:value-of select="tei:quote"/></span>
      <xsl:if test="tei:cit[@type='translation']">
        <span class="gloss"><xsl:value-of select="tei:cit[@type='translation']/tei:quote"/></span>
      </xsl:if>
    </span>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       RELATED ENTRY (sub-entry / compound form)
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:re">
    <div class="sub-entry">
      <xsl:attribute name="id">
        <xsl:value-of select="@xml:id"/>
      </xsl:attribute>

      <span class="hw"><xsl:value-of select="tei:form/tei:orth"/></span>

      <xsl:if test="tei:gramGrp/tei:gram">
        <span class="gram"><xsl:value-of select="tei:gramGrp/tei:gram"/></span>
      </xsl:if>

      <xsl:apply-templates select="tei:usg"/>
      <xsl:apply-templates select="tei:sense"/>
      <xsl:apply-templates select="tei:note[not(@type='editorial')]"/>
      <xsl:if test="$show-editorial-notes='1'">
        <xsl:apply-templates select="tei:note[@type='editorial']"/>
      </xsl:if>
      <xsl:apply-templates select="tei:cit[@type='example']"/>
      <xsl:apply-templates select="tei:milestone"/>
    </div>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       LETTER DIVIDER
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:milestone[@unit='letter']">
    <div class="letter-divider">
      <span class="divider-letter"><xsl:value-of select="@n"/></span>
    </div>
  </xsl:template>

  <!-- Suppress teiHeader -->
  <xsl:template match="tei:teiHeader"/>

</xsl:stylesheet>
