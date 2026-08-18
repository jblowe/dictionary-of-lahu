<?xml version="1.0" encoding="UTF-8"?>
<!--
  lahu-latex.xsl
  XSLT 1.0 stylesheet: TEI Lex-0 (generated/tei/lahu.xml) to XeLaTeX source.

  Usage: see README-tei.md. Adapted from the Jaschke Tibetan-English
  Dictionary project's xslt/jaschke-latex.xsl (same workspace): same
  overall approach (a body-font parameter, a two-column layout, a
  handful of \newcommand entry-formatting macros, XSLT 1.0's
  substring-based latex-escape helper), simplified because Lahu is a
  single Latin-based script (no separate Tibetan font machinery needed)
  and extended for usg, multiple example/translation pairs, and
  sense/@n numbering.

  Requires XeLaTeX (not pdfLaTeX) for Unicode support.
  Default body font: DejaVu Serif, chosen for broad Unicode coverage of
  IPA Extensions and combining diacritical marks (Lahu's tone marks are
  combining accents over vowels and consonants, e.g. g with combining
  diaeresis for g̈), and because it ships with most complete TeX Live
  installations (so it should already be available via fontspec without
  a separate download on most systems, including a standard MacTeX
  install). If XeLaTeX reports the font isn't found, either install
  DejaVu Serif, or override the body-font stylesheet parameter at
  render time (see README-tei.md) with any Unicode font you have that
  covers combining diacritics well, e.g. "Charis SIL" (a font built
  specifically for this kind of linguistic data; see
  https://software.sil.org/charis/) or "Doulos SIL".
-->
<xsl:stylesheet
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei="http://www.tei-c.org/ns/1.0"
  xmlns:xml="http://www.w3.org/XML/1998/namespace"
  exclude-result-prefixes="tei">

  <xsl:output method="text" encoding="UTF-8"/>

  <!-- Parameters -->
  <xsl:param name="body-font">DejaVu Serif</xsl:param>
  <!-- Set to 1 to include editorial notes from the pipeline; 0 to suppress -->
  <xsl:param name="show-editorial-notes">0</xsl:param>


  <!-- ══════════════════════════════════════════════════════════════════════
       ROOT: emit the full LaTeX document
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="/">
    <xsl:text>\documentclass[10pt,twoside]{article}

%% Packages
\usepackage{fontspec}
\usepackage{multicol}
\usepackage{geometry}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{enumitem}

%% Page geometry
\geometry{
  a4paper,
  top=2cm, bottom=2.5cm,
  inner=2cm, outer=1.5cm,
  headsep=0.5cm
}

%% Font
\setmainfont{</xsl:text>
    <xsl:value-of select="$body-font"/>
    <xsl:text>}[Ligatures=TeX, Renderer=OpenType]

%% Dictionary entry macros
%%
%% Hanging indent, two levels deep, via \leftskip/\hangindent rather
%% than a fixed \hspace on the first line: an entry's own wrapped lines
%% indent by \dictindent (the column where sub-entries' headwords
%% start); a sub-entry's first line starts at \dictindent, and ITS
%% wrapped lines indent one further \dictindent, to 2*\dictindent. Each
%% macro below sets \leftskip and \hangindent itself at the start of
%% its own paragraph, so nothing leaks from one paragraph to the next.
%%
%% \headword{Lahu}              -- bold Lahu headword (top level)
%% \graminfo{text}              -- grammatical information in small italic
%% \usgetym{text}               -- loanword flag
%% \usglabel{text}              -- bracketed register/dialect/cross-ref label
%% \sensenum{n}                 -- sense number
%% \examplecit{Lahu}{Eng}       -- example + translation (top level; translation
%%                                  is not quoted, just set off by a quad space;
%%                                  Lahu text set 2pt smaller than body text;
%%                                  indented one level deeper than the entry
%%                                  it appears with, starts at \dictindent,
%%                                  wraps to 2*\dictindent, same as \notetext)
%% \notetext{text}              -- lexicographic note (top level), rendered
%%                                  "/ text /", indented one level deeper than
%%                                  the entry it annotates (starts at
%%                                  \dictindent, wraps to 2*\dictindent)
%% \subentry{Lahu}{content}     -- sub-entry headword (bold, 2pt smaller than
%%                                  \headword) + gram + senses
%% \subexamplecit{Lahu}{Eng}    -- example + translation (inside a sub-entry;
%%                                  Lahu text set 2pt smaller, as \examplecit;
%%                                  indented one level deeper than the
%%                                  sub-entry, starts at 2*\dictindent, wraps
%%                                  to 3*\dictindent, same as \subnotetext)
%% \subnotetext{text}           -- lexicographic note (inside a sub-entry),
%%                                  "/ text /", indented one level deeper than
%%                                  the sub-entry it annotates (starts at
%%                                  2*\dictindent, wraps to 3*\dictindent)
%% \editorialnote{text}         -- pipeline diagnostic (gray, review mode only)
%%
%% Declared here (must be in the preamble); the actual width is set
%% in \small below, once we're in the font size it will be used in --
%% "em" is resolved at the point \setlength runs, not dynamically.
\newlength{\dictindent}

\newcommand{\headword}[1]{%
  \par\vspace{2pt}%
  \leftskip=0pt \hangindent=\dictindent \hangafter=1
  \noindent\textbf{#1}\enspace%
}
\newcommand{\graminfo}[1]{%
  {\small\textit{#1}}\enspace%
}
\newcommand{\usgetym}[1]{%
  {\small\textit{[#1]}}\enspace%
}
\newcommand{\usglabel}[1]{%
  {\small\textit{[#1]}}\enspace%
}
\newcommand{\sensenum}[1]{%
  \textbf{#1.}\enspace%
}
\newcommand{\examplecit}[2]{%
  \par
  \leftskip=\dictindent \hangindent=\dictindent \hangafter=1
  \noindent{\fontsize{7pt}{8.4pt}\selectfont\textit{#1}}\quad #2%
}
\newcommand{\notetext}[1]{%
  \par
  \leftskip=\dictindent \hangindent=\dictindent \hangafter=1
  \noindent / #1 /%
}
\newcommand{\subentry}[2]{%
  \par\vspace{1pt}%
  \leftskip=\dictindent \hangindent=\dictindent \hangafter=1
  \noindent{\fontsize{7pt}{8.4pt}\selectfont\textbf{#1}}\enspace#2%
}
\newcommand{\subexamplecit}[2]{%
  \par
  \leftskip=2\dictindent \hangindent=\dictindent \hangafter=1
  \noindent{\fontsize{7pt}{8.4pt}\selectfont\textit{#1}}\quad #2%
}
\newcommand{\subnotetext}[1]{%
  \par
  \leftskip=2\dictindent \hangindent=\dictindent \hangafter=1
  \noindent / #1 /%
}
\newcommand{\editorialnote}[1]{%
  \par{\small\color{gray}[Editorial note: #1]}%
}

%% Column separator
\setlength{\columnsep}{1.2em}
\setlength{\columnseprule}{0.4pt}

%% Hyperref
\hypersetup{colorlinks=true, linkcolor=black, urlcolor=blue}

\begin{document}

\title{\textbf{The Dictionary of Lahu}\\
  \normalsize James A. Matisoff (1988)\\
  \small TEI Lex-0 Digital Edition}
\author{}
\date{}
\maketitle
\thispagestyle{empty}

\begin{multicols}{2}
\raggedright
\small
\setlength{\dictindent}{1.3em}
</xsl:text>

    <xsl:apply-templates select="//tei:div[@type='dictionary']/tei:entry"/>

    <xsl:text>
\end{multicols}
\end{document}
</xsl:text>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       ENTRY
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:entry">
    <xsl:text>
</xsl:text>
    <xsl:text>\headword{</xsl:text>
    <xsl:call-template name="latex-escape">
      <xsl:with-param name="text" select="tei:form/tei:orth"/>
    </xsl:call-template>
    <xsl:text>}</xsl:text>

    <xsl:if test="tei:gramGrp/tei:gram">
      <xsl:text>\graminfo{</xsl:text>
      <xsl:call-template name="latex-escape">
        <xsl:with-param name="text" select="tei:gramGrp/tei:gram"/>
      </xsl:call-template>
      <xsl:text>}</xsl:text>
    </xsl:if>

    <xsl:apply-templates select="tei:usg"/>
    <xsl:apply-templates select="tei:sense"/>
    <xsl:apply-templates select="tei:note[not(@type='editorial')]"/>
    <xsl:if test="$show-editorial-notes='1'">
      <xsl:apply-templates select="tei:note[@type='editorial']"/>
    </xsl:if>
    <xsl:apply-templates select="tei:cit[@type='example']"/>
    <xsl:apply-templates select="tei:re"/>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       USAGE LABEL
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:usg[@type='etym']">
    <xsl:text>\usgetym{</xsl:text>
    <xsl:call-template name="latex-escape">
      <xsl:with-param name="text" select="."/>
    </xsl:call-template>
    <xsl:text>}</xsl:text>
  </xsl:template>

  <xsl:template match="tei:usg[@type='label']">
    <xsl:text>\usglabel{</xsl:text>
    <xsl:call-template name="latex-escape">
      <xsl:with-param name="text" select="."/>
    </xsl:call-template>
    <xsl:text>}</xsl:text>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       SENSE
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:sense">
    <xsl:if test="@n">
      <xsl:text>\sensenum{</xsl:text>
      <xsl:value-of select="@n"/>
      <xsl:text>}</xsl:text>
    </xsl:if>
    <xsl:call-template name="latex-escape">
      <xsl:with-param name="text" select="tei:def"/>
    </xsl:call-template>
    <xsl:text> </xsl:text>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       NOTE (top-level \notetext, or \subnotetext inside a sub-entry)
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:note[not(@type='editorial')]">
    <xsl:choose>
      <xsl:when test="parent::tei:re">
        <xsl:text>\subnotetext{</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>\notetext{</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:call-template name="latex-escape">
      <xsl:with-param name="text" select="."/>
    </xsl:call-template>
    <xsl:text>}</xsl:text>
  </xsl:template>

  <xsl:template match="tei:note[@type='editorial']">
    <xsl:text>\editorialnote{</xsl:text>
    <xsl:call-template name="latex-escape">
      <xsl:with-param name="text" select="."/>
    </xsl:call-template>
    <xsl:text>}</xsl:text>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       EXAMPLE + TRANSLATION (top-level \examplecit, or \subexamplecit
       inside a sub-entry)
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:cit[@type='example']">
    <xsl:choose>
      <xsl:when test="parent::tei:re">
        <xsl:text>\subexamplecit{</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>\examplecit{</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:call-template name="latex-escape">
      <xsl:with-param name="text" select="tei:quote"/>
    </xsl:call-template>
    <xsl:text>}{</xsl:text>
    <xsl:if test="tei:cit[@type='translation']">
      <xsl:call-template name="latex-escape">
        <xsl:with-param name="text" select="tei:cit[@type='translation']/tei:quote"/>
      </xsl:call-template>
    </xsl:if>
    <xsl:text>}</xsl:text>
  </xsl:template>


  <!-- ══════════════════════════════════════════════════════════════════════
       RELATED ENTRY (sub-entry / compound form)

       \subentry{}{} carries only the headword-line content (gram/usg/
       sense), exactly mirroring how \headword's paragraph carries the
       top-level entry's headword line; note and example are applied
       afterward as their own paragraphs (via the context-aware
       templates above), exactly mirroring the top-level entry template.
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template match="tei:re">
    <xsl:variable name="hw" select="tei:form/tei:orth"/>
    <xsl:text>
\subentry{</xsl:text>
    <xsl:call-template name="latex-escape">
      <xsl:with-param name="text" select="$hw"/>
    </xsl:call-template>
    <xsl:text>}{</xsl:text>
    <xsl:if test="tei:gramGrp/tei:gram">
      <xsl:text>\graminfo{</xsl:text>
      <xsl:call-template name="latex-escape">
        <xsl:with-param name="text" select="tei:gramGrp/tei:gram"/>
      </xsl:call-template>
      <xsl:text>}</xsl:text>
    </xsl:if>
    <xsl:apply-templates select="tei:usg"/>
    <xsl:apply-templates select="tei:sense"/>
    <xsl:text>}</xsl:text>
    <xsl:apply-templates select="tei:note[not(@type='editorial')]"/>
    <xsl:if test="$show-editorial-notes='1'">
      <xsl:apply-templates select="tei:note[@type='editorial']"/>
    </xsl:if>
    <xsl:apply-templates select="tei:cit[@type='example']"/>
  </xsl:template>

  <!-- Suppress teiHeader -->
  <xsl:template match="tei:teiHeader"/>


  <!-- ══════════════════════════════════════════════════════════════════════
       UTILITY: LaTeX character escaping (same recursive substring-based
       approach as jaschke-latex.xsl's latex-escape/str-replace, since
       XSLT 1.0 has no built-in string-replace function)
       ══════════════════════════════════════════════════════════════════════ -->
  <xsl:template name="latex-escape">
    <xsl:param name="text"/>
    <xsl:variable name="step1">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$text"/>
        <xsl:with-param name="from">\</xsl:with-param>
        <xsl:with-param name="to">\textbackslash{}</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="step2">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step1"/>
        <xsl:with-param name="from">&amp;</xsl:with-param>
        <xsl:with-param name="to">\&amp;</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="step3">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step2"/>
        <xsl:with-param name="from">%</xsl:with-param>
        <xsl:with-param name="to">\%</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="step4">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step3"/>
        <xsl:with-param name="from">$</xsl:with-param>
        <xsl:with-param name="to">\$</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="step5">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step4"/>
        <xsl:with-param name="from">#</xsl:with-param>
        <xsl:with-param name="to">\#</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="step6">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step5"/>
        <xsl:with-param name="from">_</xsl:with-param>
        <xsl:with-param name="to">\_</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="step7">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step6"/>
        <xsl:with-param name="from">{</xsl:with-param>
        <xsl:with-param name="to">\{</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="step8">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step7"/>
        <xsl:with-param name="from">}</xsl:with-param>
        <xsl:with-param name="to">\}</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <!-- '^' and '~' are TeX active characters outside math mode ('^'
         especially: a bare caret triggers "Missing $ inserted" and
         aborts the compile). Both occur literally in a few dozen
         comparative-linguistics notes (e.g. "ga^" for a syllable later
         meant to carry a circumflex, or "~" marking free variation), so
         these must be escaped too, not just the classic LaTeX special
         seven. Introduced as their own step, after the backslash step,
         so the backslash inside \textasciicircum{}/\textasciitilde{}
         doesn't get re-escaped. -->
    <xsl:variable name="step9">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step8"/>
        <xsl:with-param name="from">^</xsl:with-param>
        <xsl:with-param name="to">\textasciicircum{}</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="step10">
      <xsl:call-template name="str-replace">
        <xsl:with-param name="text" select="$step9"/>
        <xsl:with-param name="from">~</xsl:with-param>
        <xsl:with-param name="to">\textasciitilde{}</xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <xsl:value-of select="$step10"/>
  </xsl:template>

  <!-- Recursive string replace (XSLT 1.0) -->
  <xsl:template name="str-replace">
    <xsl:param name="text"/>
    <xsl:param name="from"/>
    <xsl:param name="to"/>
    <xsl:choose>
      <xsl:when test="contains($text, $from)">
        <xsl:value-of select="substring-before($text, $from)"/>
        <xsl:value-of select="$to"/>
        <xsl:call-template name="str-replace">
          <xsl:with-param name="text" select="substring-after($text, $from)"/>
          <xsl:with-param name="from" select="$from"/>
          <xsl:with-param name="to" select="$to"/>
        </xsl:call-template>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$text"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

</xsl:stylesheet>
