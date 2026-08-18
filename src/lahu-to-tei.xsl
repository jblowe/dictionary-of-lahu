<?xml version="1.0" encoding="UTF-8"?>
<!--
  lahu-to-tei.xsl
  XSLT 1.0 stylesheet: our ad hoc Lexware-band XML
  (generated/lahudico-lexware.xml, produced by lex2xml.py), transduced
  to TEI Lex-0.

  Usage: see README-tei.md for the exact command line (it goes through
  render_tei.py, a small generic runner that also cleans up a couple of
  minor XML well-formedness quirks in generated/lahudico-lexware.xml
  before parsing it; see README-lex2xml.md).

  See README-tei.md for the full band-tag to TEI element mapping table,
  the rationale behind each choice, and known simplifications. See
  src/lahu-tei-lex0.xml for an annotated reference copy of the TEI
  header this stylesheet emits, plus hand-written example entries.

  Source element reference (all elements below are in NO namespace;
  generated/lahudico-lexware.xml is plain XML, not TEI):
    lexicon         root
    entry           top-level dictionary article (id attribute "Lahu.N")
    sub             sub-headword ("..hw" in the original Lexware bands)
    hw              headword text (child of entry or sub)
    pos             part of speech
    ld              loanword flag ("LOAN" / "LOAN?")
    bz              bracketed register/dialect/cross-ref annotation,
                    e.g. "[RL]", "[poetic]", "[q.v.]"
    gl              gloss: either a sense definition, or (when it
                    immediately follows an ex element) that example's
                    translation
    ex              Lahu example sentence
    no              lexicographic note
    xx              raw fallback content the classifier couldn't
                    confidently type; kept as a visible, untyped note
                    (type="unclassified") since most of it is genuine
                    dictionary text, not pipeline noise; see
                    README-tei.md.
    err             pipeline diagnostic messages; see README-lex2xml.md.
                    Kept as an editorial note, suppressed by default in
                    the render stylesheets.
    srcxcrN         rare artifact of lex2xml.py's bracket-citation
                    helper firing on an unrelated stray '[' character;
                    folded into the same editorial-note bucket as err.
    comment, mode, hdr  never occur in the real Lahu data (legacy
                    bands from a different dictionary project); templates
                    provided only for robustness, and produce nothing.
-->
<xsl:stylesheet
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei="http://www.tei-c.org/ns/1.0">

  <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>

  <!-- ══════════════════════════════════════════════════════════════════════
       ROOT
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="/lexicon">
    <tei:TEI>
      <tei:teiHeader>
        <tei:fileDesc>
          <tei:titleStmt>
            <tei:title>The Dictionary of Lahu</tei:title>
            <tei:author>
              <tei:persName>
                <tei:forename>James A.</tei:forename>
                <tei:surname>Matisoff</tei:surname>
              </tei:persName>
            </tei:author>
            <tei:respStmt>
              <tei:resp>TEI Lex-0 transduction from Lexware</tei:resp>
            </tei:respStmt>
          </tei:titleStmt>
          <tei:editionStmt>
            <tei:edition>TEI Lex-0 digital edition, transduced from a
              Lexware (Shoebox/MDF-style) database reconstructed from the
              original 1988 WordStar/CP-M source files.</tei:edition>
          </tei:editionStmt>
          <tei:publicationStmt>
            <tei:p>See ../../README.md and ../../README-tei.md (paths
              relative to this file, generated/tei/lahu.xml) for the
              full pipeline and TEI mapping.</tei:p>
          </tei:publicationStmt>
          <tei:sourceDesc>
            <tei:p>Transduced from generated/lahudico-lexware.xml (see
              src/lahu-tei-lex0.xml, relative to the project root,
              for an annotated reference).</tei:p>
          </tei:sourceDesc>
        </tei:fileDesc>
        <tei:profileDesc>
          <tei:langUsage>
            <tei:language ident="lhu">Lahu (Matisoff's romanization)</tei:language>
            <tei:language ident="en">English</tei:language>
          </tei:langUsage>
        </tei:profileDesc>
      </tei:teiHeader>
      <tei:text>
        <tei:body>
          <tei:div type="dictionary" xml:lang="lhu">
            <!-- Only real dictionary articles; stray top-level xx/err
                 (running-header noise from original page boundaries,
                 e.g. "THE DICTIONARY OF LAHU" repeated about 131 times)
                 are not entries and carry no lexicographic content, so
                 they are intentionally dropped here; see README-tei.md. -->
            <xsl:apply-templates select="entry"/>
          </tei:div>
        </tei:body>
      </tei:text>
    </tei:TEI>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       ENTRY / SUB-ENTRY
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="entry">
    <tei:entry xml:lang="lhu">
      <xsl:attribute name="xml:id">
        <xsl:value-of select="@id"/>
      </xsl:attribute>
      <xsl:apply-templates select="*"/>
    </tei:entry>
  </xsl:template>

  <xsl:template match="sub">
    <tei:re>
      <xsl:attribute name="xml:id">
        <xsl:value-of select="concat(../@id, '.', count(preceding-sibling::sub) + 1)"/>
      </xsl:attribute>
      <xsl:apply-templates select="*"/>
    </tei:re>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       HEADWORD: form/orth. type="lemma" for a top-level entry's own
       headword, type="compound" for a sub-entry's.
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="hw[parent::entry]">
    <tei:form type="lemma">
      <tei:orth xml:lang="lhu"><xsl:value-of select="."/></tei:orth>
    </tei:form>
  </xsl:template>

  <xsl:template match="hw[parent::sub]">
    <tei:form type="compound">
      <tei:orth xml:lang="lhu"><xsl:value-of select="."/></tei:orth>
    </tei:form>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       PART OF SPEECH
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="pos">
    <tei:gramGrp>
      <tei:gram type="pos"><xsl:value-of select="."/></tei:gram>
    </tei:gramGrp>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       LOANWORD FLAG (Lexware "ld") and BRACKETED LABEL (Lexware "bz")
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="ld">
    <tei:usg type="etym"><xsl:value-of select="."/></tei:usg>
  </xsl:template>

  <xsl:template match="bz">
    <!-- Strip the brackets themselves; a bz can hold more than one
         bracketed group (e.g. "[RL] [poetic]"), so this just removes
         every literal '[' / ']' rather than assuming exactly one pair. -->
    <tei:usg type="label"><xsl:value-of select="translate(., '[]', '')"/></tei:usg>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       NOTE (Lexware "no")
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="no">
    <tei:note xml:lang="en"><xsl:value-of select="."/></tei:note>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       EXAMPLE + TRANSLATION (Lexware "ex" plus a following "gl", if any)
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="ex">
    <tei:cit type="example">
      <tei:quote xml:lang="lhu"><xsl:value-of select="."/></tei:quote>
      <xsl:if test="following-sibling::*[1][self::gl]">
        <tei:cit type="translation">
          <tei:quote xml:lang="en"><xsl:value-of select="following-sibling::*[1]"/></tei:quote>
        </tei:cit>
      </xsl:if>
    </tei:cit>
  </xsl:template>

  <!-- A gl immediately after an ex is that example's translation,
       already emitted above by the ex template; suppress it here so it
       isn't emitted a second time. -->
  <xsl:template match="gl[preceding-sibling::*[1][self::ex]]"/>


  <!-- ══════════════════════════════════════════════════════════════════════
       SENSE (Lexware "gl", when NOT an example translation)

       Matisoff numbers multiple senses inline in the gloss text itself
       ("1. ...", "2. ...", or "a. ...", "b. ..."). Split a short
       (2 characters or fewer) leading numeric or single-letter marker
       followed by ". " into sense/@n; if the text doesn't match that
       shape, the whole gloss becomes a single unnumbered sense rather
       than guessed at (see README-tei.md).
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="gl">
    <xsl:call-template name="gl-to-sense">
      <xsl:with-param name="text" select="."/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template name="gl-to-sense">
    <xsl:param name="text"/>
    <xsl:variable name="prefix" select="substring-before($text, '. ')"/>
    <xsl:variable name="is-digits"
      select="string-length($prefix) &gt; 0
              and string-length($prefix) &lt;= 2
              and translate($prefix, '0123456789', '') = ''"/>
    <xsl:variable name="is-letter"
      select="string-length($prefix) = 1
              and contains('abcdefghijklmnopqrstuvwxyz', $prefix)"/>
    <xsl:choose>
      <xsl:when test="$is-digits or $is-letter">
        <tei:sense n="{$prefix}">
          <tei:def xml:lang="en"><xsl:value-of select="substring-after($text, '. ')"/></tei:def>
        </tei:sense>
      </xsl:when>
      <xsl:otherwise>
        <tei:sense>
          <tei:def xml:lang="en"><xsl:value-of select="$text"/></tei:def>
        </tei:sense>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       xx: raw content the classifier couldn't confidently type. Most of
       what remains after src/dl_convert.py's gloss-continuation merge
       (see README.md) is genuinely unclassified rather than pipeline
       noise, so it's rendered as an ordinary (untyped) note, visible by
       default and not gated behind show-editorial-notes, rather than
       hidden as an editorial diagnostic.
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="xx">
    <xsl:if test="normalize-space(.) != ''">
      <!-- type="unclassified" (not "editorial") keeps this visible by
           default and rendered identically to a genuine "no" note, but
           still distinguishes it in the TEI source from Matisoff's own
           notes, in case a future reviewer wants to find/reclassify
           these specifically. -->
      <tei:note type="unclassified" xml:lang="en"><xsl:value-of select="."/></tei:note>
    </xsl:if>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       EDITORIAL / PIPELINE NOTES ("err", the classifier's own diagnostic
       messages, and the rare "srcxcrN" bracket-citation-helper artifact;
       see README-lex2xml.md). These are pipeline metadata about the
       conversion itself, not dictionary content, so they stay tagged
       distinctly and hidden by default (show-editorial-notes param).
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="err | *[starts-with(name(), 'srcxcr')]">
    <xsl:if test="normalize-space(.) != ''">
      <tei:note type="editorial" resp="pipeline"><xsl:value-of select="."/></tei:note>
    </xsl:if>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       Legacy bands from a different dictionary project, never used in
       our Lahu data; present only so the transducer doesn't choke if
       they ever show up.
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="comment | mode | hdr"/>

</xsl:stylesheet>
