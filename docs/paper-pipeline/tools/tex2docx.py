#!/usr/bin/env python3
r"""Build the Word version of a paper from its filled LaTeX source, over the UBMK template.

    python3 tex2docx.py papers/<paper> UBMKtemplateA4.docx out.docx

The output is the template package with a new ``word/document.xml``: every paragraph carries
one of the template's own style ids, so the spacing, indents, fonts and numbering come from
``word/styles.xml`` rather than from anything asserted here.  That is the point -- the
committee's corrections are all statements about those styles, so a document written in terms
of them cannot drift from the template the way hand-set formatting does.

Numbering in particular is left to Word.  ``Balk1`` carries numId 4 (I., II., ...), ``Balk2``
its A., B. sublevel, ``figurecaption`` numId 2 (``Fig. 1.``), ``tablehead`` numId 9
(``TABLE I.``) and ``references`` numId 8 (``[1]``).  Cross-references in the body are written
out as literal numbers taken from source order; ``docx_check.py`` compares the result against
both the LaTeX source and the PDF built from it.

Figures become PNGs rasterised to about 600 dpi at their final placed width; LibreOffice has no
PDF import filter here, so vector EMF is not available.  Maths is transcribed to Unicode with
Word's own subscript/superscript run properties, which keeps it selectable and editable rather
than freezing it into pictures.

Anything the converter does not recognise -- an unknown control sequence in text or maths, a
float it cannot render, a citation key with no bibliography entry -- raises Unsupported and
aborts the build.  A converter that silently drops what it cannot handle produces a document
that looks complete and is not, which is exactly the failure mode this pipeline keeps hitting.
"""
from __future__ import annotations

import argparse
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

EMU_PER_INCH = 914400
TWIP_PER_INCH = 1440

# Page geometry, matching the LaTeX \geometry: A4, 2cm top, 2.5cm bottom, 1.6cm sides.
PAGE_W, PAGE_H = 11906, 16838
MAR_TOP, MAR_BOT, MAR_SIDE = 1134, 1418, 907
COL_GAP = 360
TEXT_W = PAGE_W - 2 * MAR_SIDE
COL_W = (TEXT_W - COL_GAP) // 2

TARGET_DPI = 600


class Unsupported(Exception):
    """Something in the source has no faithful representation yet. Never swallowed."""


# --------------------------------------------------------------------------- maths


GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π",
    "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}

MATH_SYMBOL = {
    "pm": "±", "mp": "∓", "times": "×", "div": "÷", "cdot": "·", "ast": "∗",
    "star": "⋆", "circ": "∘", "bullet": "∙", "oplus": "⊕", "otimes": "⊗",
    "to": "→", "gets": "←", "rightarrow": "→", "leftarrow": "←", "mapsto": "↦",
    "leftrightarrow": "↔", "Rightarrow": "⇒", "Leftarrow": "⇐", "uparrow": "↑",
    "downarrow": "↓", "approx": "≈", "simeq": "≃", "sim": "∼", "cong": "≅",
    "equiv": "≡", "neq": "≠", "ne": "≠", "le": "≤", "leq": "≤", "ge": "≥",
    "geq": "≥", "ll": "≪", "gg": "≫", "lesssim": "≲", "gtrsim": "≳",
    "propto": "∝", "in": "∈", "notin": "∉", "ni": "∋", "subset": "⊂",
    "subseteq": "⊆", "supset": "⊃", "supseteq": "⊇", "cup": "∪", "cap": "∩",
    "setminus": "∖", "emptyset": "∅", "forall": "∀", "exists": "∃",
    "neg": "¬", "wedge": "∧", "vee": "∨", "perp": "⊥", "parallel": "∥",
    "infty": "∞", "partial": "∂", "nabla": "∇", "surd": "√", "angle": "∠",
    "sum": "∑", "prod": "∏", "int": "∫", "bigcup": "⋃", "bigcap": "⋂",
    "lceil": "⌈", "rceil": "⌉", "lfloor": "⌊", "rfloor": "⌋",
    "langle": "⟨", "rangle": "⟩", "|": "|", "backslash": "\\",
    "ldots": "…", "dots": "…", "cdots": "⋯", "vdots": "⋮", "ddots": "⋱",
    "prime": "′", "degree": "°", "pounds": "£", "dagger": "†",
    "{": "{", "}": "}", "%": "%", "$": "$", "&": "&", "#": "#", "_": "_",
}

# Function names set upright, as LaTeX does.
MATH_OPERATOR = {
    "log", "ln", "lg", "exp", "sin", "cos", "tan", "sec", "csc", "cot",
    "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "min", "max",
    "inf", "sup", "lim", "limsup", "liminf", "det", "dim", "ker", "deg",
    "arg", "gcd", "hom", "Pr",
}

# Thin/medium/thick spaces and their negatives; LaTeX uses them for optical spacing only.
MATH_SPACE = {",": "\u2009", ";": "\u2005", ":": "\u2005", "!": "", " ": " ",
              "quad": "\u2003", "qquad": "\u2003\u2003", "thinspace": "\u2009"}

BLACKBOARD = {"Z": "ℤ", "R": "ℝ", "N": "ℕ", "Q": "ℚ", "C": "ℂ", "F": "𝔽",
              "E": "𝔼", "P": "ℙ", "H": "ℍ", "1": "𝟙"}

CALLIGRAPHIC = {c: chr(0x1D49C + i) for i, c in enumerate(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
CALLIGRAPHIC.update({"B": "ℬ", "E": "ℰ", "F": "ℱ", "H": "ℋ", "I": "ℐ",
                     "L": "ℒ", "M": "ℳ", "R": "ℛ", "e": "ℯ", "g": "ℊ", "o": "ℴ"})

# Combining marks, applied after the accented character.
MATH_ACCENT = {"hat": "\u0302", "widehat": "\u0302", "bar": "\u0304",
               "overline": "\u0304", "dot": "\u0307", "ddot": "\u0308",
               "tilde": "\u0303", "widetilde": "\u0303", "vec": "\u20D7",
               "check": "\u030C", "acute": "\u0301", "grave": "\u0300"}

# Sizing and delimiter commands that carry no meaning once the maths is linear text.
MATH_IGNORE = {
    "left", "right", "big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl",
    "Bigr", "biggl", "biggr", "Biggl", "Biggr", "displaystyle", "textstyle",
    "scriptstyle", "limits", "nolimits", "relax", "boldmath", "unboldmath",
    "notag", "nonumber",
}

# Text-mode commands whose only job is layout, and which have no Word counterpart here.
TEXT_DROP = {
    "maketitle", "thispagestyle", "pagestyle", "centering", "selectfont",
    "boldmath", "unboldmath", "itshape", "normalfont", "footnotesize",
    "small", "scriptsize", "tiny", "normalsize", "large", "Large", "LARGE",
    "huge", "Huge", "noindent", "clearpage", "newpage", "hfill", "vfill",
    "relax", "protect", "leavevmode", "bibliographystyle", "linespread",
    "IEEEoverridecommandlockouts", "raggedright", "raggedleft", "hline",
    "toprule", "midrule", "bottomrule", "newblock", "BIBdecl",
    "BIBentrySTDinterwordspacing", "BIBentryALTinterwordspacing",
    "csname", "endcsname", "sloppy", "fussy", "smallskip", "medskip", "bigskip",
}

# Text-mode commands taking one argument that is simply dropped.
TEXT_DROP_ARG = {"label", "index", "vspace", "hspace", "setlength", "addtolength",
                 "setcounter", "renewcommand", "captionsetup", "phantom",
                 "bibinfo", "providecommand", "typeout"}

TEXT_ACCENT = {
    '"': {"o": "ö", "a": "ä", "u": "ü", "e": "ë", "i": "ï", "O": "Ö",
          "A": "Ä", "U": "Ü", "s": "ß"},
    "'": {"e": "é", "a": "á", "i": "í", "o": "ó", "u": "ú", "c": "ć",
          "s": "ś", "n": "ń", "y": "ý", "E": "É", "A": "Á", "O": "Ó"},
    "`": {"e": "è", "a": "à", "i": "ì", "o": "ò", "u": "ù", "E": "È"},
    "^": {"e": "ê", "a": "â", "i": "î", "o": "ô", "u": "û", "c": "ĉ"},
    "~": {"n": "ñ", "a": "ã", "o": "õ"},
    "c": {"c": "ç", "s": "ş", "C": "Ç", "S": "Ş"},
    "u": {"g": "ğ", "G": "Ğ", "a": "ă"},
    "v": {"s": "š", "c": "č", "z": "ž", "r": "ř", "S": "Š", "C": "Č"},
    "=": {"o": "ō", "a": "ā", "e": "ē"},
    ".": {"z": "ż", "I": "İ"},
    "H": {"o": "ő", "u": "ű"},
    "k": {"a": "ą", "e": "ę"},
    "r": {"a": "å", "A": "Å"},
}

TEXT_SYMBOL = {
    "%": "%", "&": "&", "_": "_", "#": "#", "$": "$", "{": "{", "}": "}",
    "ldots": "…", "dots": "…", "textendash": "–", "textemdash": "—",
    "ss": "ß", "aa": "å", "AA": "Å", "ae": "æ", "AE": "Æ", "oe": "œ",
    "o": "ø", "O": "Ø", "l": "ł", "L": "Ł", "i": "ı", "j": "ȷ",
    "textbullet": "•", "textdegree": "°", "textpm": "±", "texttimes": "×",
    "copyright": "©", "textregistered": "®", "S": "§", "P": "¶",
    "textquotedblleft": "\u201c", "textquotedblright": "\u201d",
    "textquoteleft": "\u2018", "textquoteright": "\u2019",
    " ": " ", "-": "", "/": "", "@": "",
    # The maths spacing commands are legal in text mode too and are used there for optical
    # kerning, as in "classifier\,$\cup$\,abstention".
    ",": "\u2009", ";": "\u2005", ":": "\u2005", "!": "",
    "quad": "\u2003", "qquad": "\u2003\u2003",
}


def run(text: str, **fmt) -> dict:
    r = {"t": text, "i": False, "b": False, "sc": False, "vert": None}
    r.update(fmt)
    return r


def brace_arg(s: str, i: int) -> tuple[str, int]:
    """Read a balanced {...} group starting at s[i]; return its body and the index after it."""
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s) or s[i] != "{":
        # A single-token argument, as in \hat x or \"o.
        if i < len(s):
            return s[i], i + 1
        raise Unsupported(f"expected an argument at offset {i}")
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{" and (j == i or s[j - 1] != "\\"):
            depth += 1
        elif s[j] == "}" and s[j - 1] != "\\":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise Unsupported("unbalanced braces")


def optional_arg(s: str, i: int) -> tuple[str | None, int]:
    """Read a [...] optional argument if one is present at s[i]."""
    if i < len(s) and s[i] == "[":
        j = s.index("]", i)
        return s[i + 1:j], j + 1
    return None, i


def math_runs(src: str, ctx: str, italic_default: bool = True) -> list[dict]:
    """Transcribe one maths fragment to Word runs.

    Single Latin letters become italic and everything else upright, which is what LaTeX does
    and what the reader expects; sub- and superscripts use Word's own vertAlign rather than
    Unicode subscript characters, so they survive editing and cover every character.
    """
    out: list[dict] = []
    i, n = 0, len(src)

    def emit(text, **fmt):
        if text:
            out.append(run(text, **fmt))

    while i < n:
        c = src[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", src[i:], re.S)
            if not m:
                raise Unsupported(f"stray backslash in maths: {src!r} ({ctx})")
            name = m.group(1)
            i += m.end()
            if name.isspace():
                name = " "
            if name in MATH_IGNORE:
                continue
            if name in MATH_SPACE:
                emit(MATH_SPACE[name])
                continue
            if name in MATH_ACCENT:
                arg, i = brace_arg(src, i)
                inner = math_runs(arg, ctx, italic_default)
                if inner:
                    inner[0]["t"] = inner[0]["t"][:1] + MATH_ACCENT[name] + inner[0]["t"][1:]
                out.extend(inner)
                continue
            if name in ("mathrm", "operatorname", "text", "textrm", "mbox", "textnormal"):
                arg, i = brace_arg(src, i)
                out.extend(math_runs(arg, ctx, italic_default=False))
                continue
            if name in ("mathbf", "boldsymbol", "bm", "pmb"):
                arg, i = brace_arg(src, i)
                for r in math_runs(arg, ctx, italic_default):
                    r["b"] = True
                    out.append(r)
                continue
            if name in ("mathit", "textit", "emph"):
                arg, i = brace_arg(src, i)
                for r in math_runs(arg, ctx, italic_default=True):
                    r["i"] = True
                    out.append(r)
                continue
            if name == "mathbb":
                arg, i = brace_arg(src, i)
                emit("".join(BLACKBOARD.get(ch, ch) for ch in arg))
                continue
            if name in ("mathcal", "mathscr"):
                arg, i = brace_arg(src, i)
                emit("".join(CALLIGRAPHIC.get(ch, ch) for ch in arg))
                continue
            if name in ("frac", "tfrac", "dfrac"):
                num, i = brace_arg(src, i)
                den, i = brace_arg(src, i)
                out.extend(math_runs(num, ctx, italic_default))
                emit("/")
                out.extend(math_runs(den, ctx, italic_default))
                continue
            if name == "sqrt":
                arg, i = brace_arg(src, i)
                emit("√(")
                out.extend(math_runs(arg, ctx, italic_default))
                emit(")")
                continue
            if name == "pmod":
                arg, i = brace_arg(src, i)
                emit(" (mod ", i=False)
                out.extend(math_runs(arg, ctx, italic_default))
                emit(")", i=False)
                continue
            if name in ("bmod", "mod"):
                emit(" mod ", i=False)
                continue
            if name in MATH_OPERATOR:
                emit(name, i=False)
                continue
            if name in GREEK:
                emit(GREEK[name], i=italic_default and len(GREEK[name]) == 1
                     and GREEK[name].islower())
                continue
            if name in MATH_SYMBOL:
                emit(MATH_SYMBOL[name], i=False)
                continue
            raise Unsupported(rf"unknown maths command \{name} in {src!r} ({ctx})")
        if c in "_^":
            i += 1
            arg, i = brace_arg(src, i)
            for r in math_runs(arg, ctx, italic_default):
                r["vert"] = "subscript" if c == "_" else "superscript"
                out.append(r)
            continue
        if c == "{":
            arg, i = brace_arg(src, i)
            out.extend(math_runs(arg, ctx, italic_default))
            continue
        if c == "}":
            raise Unsupported(f"unmatched }} in maths: {src!r} ({ctx})")
        if c.isalpha():
            j = i
            while j < n and src[j].isalpha():
                j += 1
            word = src[i:j]
            # A run of letters is a product of one-letter variables, so it stays italic; but a
            # multi-letter run that names a known function is set upright.
            emit(word, i=italic_default and word not in MATH_OPERATOR)
            i = j
            continue
        if c == "-":
            emit("\u2212")  # a minus sign, not a hyphen
            i += 1
            continue
        if c.isspace():
            i += 1
            continue
        emit(c, i=False)
        i += 1
    return collapse(out)


# --------------------------------------------------------------------------- text


def collapse(runs: list[dict]) -> list[dict]:
    """Normalise whitespace across a run sequence and merge neighbours that match.

    TeX treats any run of whitespace, newlines included, as a single space, so the newlines
    inherited from the source must not survive into the Word text -- ``xml:space="preserve"``
    would keep them as real line breaks inside a paragraph. Merging adjacent runs that share
    formatting then undoes the per-character splitting the maths transcriber produces, which
    otherwise scatters a number like "15" over two runs.
    """
    out: list[dict] = []
    for r in runs:
        if r.get("brk") or "footnote" in r:
            out.append(r)
            continue
        r = dict(r, t=re.sub(r"\s+", " ", r["t"]))
        if not r["t"]:
            continue
        if out and not (out[-1].get("brk") or "footnote" in out[-1]) and \
                all(out[-1].get(k) == r.get(k) for k in ("i", "b", "sc", "vert")):
            out[-1] = dict(out[-1], t=out[-1]["t"] + r["t"])
        else:
            out.append(r)
    while out and not (out[0].get("brk") or "footnote" in out[0]) and not out[0]["t"].strip():
        out.pop(0)
    if out and not (out[0].get("brk") or "footnote" in out[0]):
        out[0] = dict(out[0], t=out[0]["t"].lstrip())
    if out and not (out[-1].get("brk") or "footnote" in out[-1]):
        out[-1] = dict(out[-1], t=out[-1]["t"].rstrip())
    return [r for r in out if r.get("t") or r.get("brk") or "footnote" in r]


class Inline:
    """Turns text-mode LaTeX into Word runs, resolving citations and cross-references."""

    def __init__(self, doc: "Paper"):
        self.doc = doc

    def parse(self, src: str, ctx: str, **base) -> list[dict]:
        out: list[dict] = []
        i, n = 0, len(src)
        buf: list[str] = []
        fmt = {"i": base.get("i", False), "b": base.get("b", False),
               "sc": base.get("sc", False)}

        def flush():
            if buf:
                out.append(run("".join(buf), **fmt))
                buf.clear()

        while i < n:
            c = src[i]
            if c == "%" and (i == 0 or src[i - 1] != "\\"):
                i = src.find("\n", i)
                if i == -1:
                    break
                i += 1
                continue
            if c == "$":
                j = src.index("$", i + 1)
                flush()
                for r in math_runs(src[i + 1:j], ctx):
                    r["b"] = r["b"] or fmt["b"]
                    out.append(r)
                i = j + 1
                continue
            if c == "~":
                buf.append("\u00a0")
                i += 1
                continue
            if src.startswith("``", i):
                buf.append("\u201c")
                i += 2
                continue
            if src.startswith("''", i):
                buf.append("\u201d")
                i += 2
                continue
            if src.startswith("---", i):
                buf.append("\u2014")
                i += 3
                continue
            if src.startswith("--", i):
                buf.append("\u2013")
                i += 2
                continue
            if c == "`":
                buf.append("\u2018")
                i += 1
                continue
            if c == "'":
                buf.append("\u2019")
                i += 1
                continue
            if c == "{":
                arg, i = brace_arg(src, i)
                flush()
                out.extend(self.parse(arg, ctx, **fmt))
                continue
            if c == "}":
                raise Unsupported(f"unmatched }} in {ctx}: {src[:80]!r}")
            if c != "\\":
                buf.append(c)
                i += 1
                continue

            # re.S matters: "vs.\" at end of line is TeX's control space, the escape character
            # followed by the newline, and without DOTALL that reads as a stray backslash.
            m = re.match(r"\\([A-Za-z]+\*?|.)", src[i:], re.S)
            if not m:
                raise Unsupported(f"stray backslash in {ctx}: {src[max(0, i - 60):i + 40]!r}")
            name = m.group(1)
            i += m.end()
            if name.isspace():
                name = " "

            if name == "\\":
                _, i = optional_arg(src, i)
                flush()
                out.append(run("", brk=True))
                continue
            if name in TEXT_DROP:
                continue
            if name in TEXT_DROP_ARG:
                _, i = optional_arg(src, i)
                brace_arg(src, i)
                _, i = brace_arg(src, i)
                if name in ("renewcommand", "setlength", "addtolength", "setcounter",
                            "providecommand", "bibinfo"):
                    try:
                        _, i = brace_arg(src, i)
                    except Unsupported:
                        pass
                continue
            if name in ("emph", "textit"):
                arg, i = brace_arg(src, i)
                flush()
                out.extend(self.parse(arg, ctx, **{**fmt, "i": not fmt["i"]}))
                continue
            if name in ("textbf", "bf"):
                arg, i = brace_arg(src, i)
                flush()
                out.extend(self.parse(arg, ctx, **{**fmt, "b": True}))
                continue
            if name == "textsc":
                arg, i = brace_arg(src, i)
                flush()
                out.extend(self.parse(arg, ctx, **{**fmt, "sc": True}))
                continue
            if name in ("texttt", "textrm", "textnormal", "underline", "mbox", "text"):
                arg, i = brace_arg(src, i)
                flush()
                out.extend(self.parse(arg, ctx, **fmt))
                continue
            if name == "url":
                arg, i = brace_arg(src, i)
                buf.append(arg)
                continue
            if name == "cite":
                _, i = optional_arg(src, i)
                arg, i = brace_arg(src, i)
                buf.append(self.doc.cite(arg, ctx))
                continue
            if name in ("ref", "eqref", "autoref"):
                arg, i = brace_arg(src, i)
                num = self.doc.reference(arg.strip(), ctx)
                buf.append(f"({num})" if name == "eqref" else num)
                continue
            if name == "footnote":
                _, i = optional_arg(src, i)
                arg, i = brace_arg(src, i)
                flush()
                out.append({"footnote": self.doc.add_footnote(arg, ctx)})
                continue
            if name == "hskip":
                m2 = re.match(r"\s*[-\d.]+\s*[a-z]+(\s+(plus|minus)\s*[-\d.]+\s*[a-z]+)*",
                              src[i:])
                i += m2.end() if m2 else 0
                buf.append(" ")
                continue
            if name in TEXT_ACCENT:
                arg, i = brace_arg(src, i)
                table = TEXT_ACCENT[name]
                if arg not in table:
                    raise Unsupported(rf"unknown accent \{name}{{{arg}}} in {ctx}")
                buf.append(table[arg])
                continue
            if name in TEXT_SYMBOL:
                buf.append(TEXT_SYMBOL[name])
                continue
            raise Unsupported(rf"unknown command \{name} in {ctx}: {src[max(0,i-60):i+40]!r}")

        flush()
        return collapse(out)


# --------------------------------------------------------------------------- document


class Paper:
    """The parsed paper: title, authors, abstract, body blocks, floats and bibliography."""

    def __init__(self, paper_dir: Path):
        self.dir = paper_dir
        self.tex = (paper_dir / "main_filled.tex").read_text(encoding="utf8")
        self.inline = Inline(self)
        self.footnotes: list[list[dict]] = []
        self.blocks: list[dict] = []
        self.theorem_n: dict[str, int] = {}
        self.labels: dict[str, str] = {}
        self.bib_order: list[str] = []
        self.bib_text: dict[str, str] = {}
        self._read_bib()
        self._scan_labels()
        self._parse_body()

    # -- bibliography ------------------------------------------------------

    def _read_bib(self):
        bbl = self.dir / "main_filled.bbl"
        if not bbl.exists():
            raise Unsupported(f"no {bbl}; run the LaTeX build first")
        src = bbl.read_text(encoding="utf8")
        src = src[src.index(r"\BIBdecl") + len(r"\BIBdecl"):] if r"\BIBdecl" in src else src
        parts = re.split(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", src)
        for key, body in zip(parts[1::2], parts[2::2]):
            self.bib_order.append(key)
            self.bib_text[key] = body.split(r"\end{thebibliography}")[0].strip()

    def cite(self, keys: str, ctx: str) -> str:
        nums = []
        for k in (k.strip() for k in keys.split(",")):
            if k not in self.bib_text:
                raise Unsupported(f"citation {k!r} has no bibliography entry ({ctx})")
            nums.append(self.bib_order.index(k) + 1)
        nums.sort()
        # cite.sty compresses three or more consecutive numbers into a range.
        groups, start = [], 0
        for i in range(1, len(nums) + 1):
            if i == len(nums) or nums[i] != nums[i - 1] + 1:
                a, b = nums[start], nums[i - 1]
                groups.append(f"[{a}]" if a == b else
                              (f"[{a}], [{b}]" if b - a == 1 else f"[{a}]\u2013[{b}]"))
                start = i
        return ", ".join(groups)

    # -- cross references --------------------------------------------------

    def _scan_labels(self):
        """Assign the number Word will show for every label, from source order."""
        body = self.tex[self.tex.index(r"\begin{document}"):]
        counters = {"figure": 0, "table": 0, "equation": 0, "section": 0,
                    "subsection": 0, "proposition": 0}
        roman = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
                 "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]
        letters = " ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        kind = None
        for m in re.finditer(
            r"\\begin\{(figure\*?|table\*?|equation\*?|proposition)\}"
            r"|\\(section|subsection)\*?\{"
            r"|\\label\{([^}]+)\}", body
        ):
            if m.group(1):
                kind = m.group(1).rstrip("*")
                counters[kind] += 1
                if kind == "section":
                    counters["subsection"] = 0
            elif m.group(2):
                kind = m.group(2)
                counters[kind] += 1
                if kind == "section":
                    counters["subsection"] = 0
            elif m.group(3):
                label = m.group(3)
                if kind is None:
                    raise Unsupported(f"label {label!r} before anything numbered")
                if kind == "figure":
                    self.labels[label] = str(counters["figure"])
                elif kind == "table":
                    self.labels[label] = roman[counters["table"]]
                elif kind == "equation":
                    self.labels[label] = str(counters["equation"])
                elif kind == "section":
                    self.labels[label] = roman[counters["section"]]
                elif kind == "subsection":
                    self.labels[label] = (roman[counters["section"]] + "-"
                                          + letters[counters["subsection"]].strip())
                elif kind == "proposition":
                    self.labels[label] = str(counters["proposition"])

    def reference(self, label: str, ctx: str) -> str:
        if label not in self.labels:
            raise Unsupported(f"reference to unknown label {label!r} ({ctx})")
        return self.labels[label]

    def add_footnote(self, body: str, ctx: str) -> int:
        self.footnotes.append(self.inline.parse(body, f"footnote in {ctx}"))
        return len(self.footnotes)  # Word ids 0 and 1 are the separators

    # -- body --------------------------------------------------------------

    def _parse_body(self):
        t = self.tex
        self.title = self.inline.parse(
            brace_arg(t, t.index(r"\title{") + 6)[0], "title")
        author = brace_arg(t, t.index(r"\author{") + 7)[0]
        self.authors = [self.inline.parse(a, "author block")
                        for a in re.findall(r"\\IEEEauthorblock[NA]\{(.*?)\}\s*(?=\\IEEEauthorblock|$)",
                                            author, re.S)]
        self.abstract = self.inline.parse(
            re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.S).group(1),
            "abstract")
        kw = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", t, re.S)
        self.keywords = self.inline.parse(kw.group(1), "keywords") if kw else []

        body = t[t.index(r"\begin{IEEEkeywords}") if kw else t.index(r"\end{abstract}"):]
        body = body[body.index("\n", body.index(r"\end{IEEE" if kw else r"\end{abst")):]
        body = body.split(r"\bibliographystyle")[0]
        self._walk(body)

    def _walk(self, body: str):
        i, n = 0, len(body)
        para: list[str] = []

        def flush_para():
            text = "".join(para)
            para.clear()
            # A blank line ends a paragraph in LaTeX. Without this split the whole run of text
            # between two floats arrives as one block, and the bold lead-ins that open each
            # paragraph ("Calibration.", "Models.") silently run together into a wall of prose.
            for chunk in re.split(r"\n[ \t]*\n", strip_comments(text)):
                if not chunk.strip():
                    continue
                runs = self.inline.parse(chunk.strip(), "body paragraph")
                if runs:
                    self.blocks.append({"kind": "p", "runs": runs})

        while i < n:
            m = re.compile(
                r"\\(section|subsection|subsubsection)(\*?)\{"
                r"|\\begin\{(figure\*?|table\*?|equation\*?|itemize|enumerate"
                r"|proposition|corollary|proof)\}"
            ).search(body, i)
            if not m:
                para.append(body[i:])
                break
            para.append(body[i:m.start()])
            flush_para()
            i = m.start()

            if m.group(1):
                title, i = brace_arg(body, m.end() - 1)
                level = {"section": 1, "subsection": 2, "subsubsection": 3}[m.group(1)]
                self.blocks.append({"kind": f"h{level}",
                                    "runs": self.inline.parse(title, "heading"),
                                    "numbered": m.group(2) != "*"})
                continue

            env = m.group(3)
            close = rf"\end{{{env}}}"
            end = body.index(close, i)
            inner = body[m.end():end]
            i = end + len(close)
            base = env.rstrip("*")
            if base in ("figure", "table"):
                self._float(base, inner, wide=env.endswith("*"))
            elif base == "equation":
                # The label is removed by matching it, not by splitting the body on a marker:
                # \begin{equation}\label{...} puts the label first, so a split would take the
                # empty text before it and silently drop the entire equation.
                self.blocks.append({"kind": "eq",
                                    "runs": math_runs(
                                        re.sub(r"\\label\{[^}]*\}", "",
                                               strip_comments(inner)), "equation"),
                                    "number": self._equation_number(inner)})
            elif base in ("itemize", "enumerate"):
                self._list(base, inner)
            elif base in ("proposition", "corollary"):
                # The body cites these by number ("by Proposition 1"), so the heading has to
                # carry the same number rather than standing bare.
                self.theorem_n[base] = self.theorem_n.get(base, 0) + 1
                self.blocks.append({"kind": "theorem", "name": base.capitalize(),
                                    "number": self.theorem_n[base],
                                    "runs": self.inline.parse(inner, base)})
            elif base == "proof":
                opt, j = optional_arg(inner.lstrip(), 0)
                rest = inner.lstrip()[j:] if opt else inner
                self.blocks.append({"kind": "proof", "name": opt or "Proof",
                                    "runs": self.inline.parse(rest, "proof")})
        flush_para()

    def _equation_number(self, inner: str) -> str:
        m = re.search(r"\\label\{([^}]+)\}", inner)
        return self.labels[m.group(1)] if m and m.group(1) in self.labels else ""

    def _list(self, env: str, inner: str):
        items = [x for x in re.split(r"\\item\b", strip_comments(inner))[1:]]
        for k, it in enumerate(items, 1):
            self.blocks.append({"kind": "li", "ordered": env == "enumerate",
                                "n": k, "runs": self.inline.parse(it, f"{env} item")})

    def _float(self, base: str, inner: str, wide: bool):
        cap = re.search(r"\\caption\{", inner)
        if not cap:
            raise Unsupported(f"{base} float with no caption")
        caption, _ = brace_arg(inner, cap.end() - 1)
        label = re.search(r"\\label\{([^}]+)\}", inner)
        block = {"kind": base, "wide": wide,
                 "caption": self.inline.parse(caption, f"{base} caption"),
                 "label": label.group(1) if label else None}
        if base == "table":
            block["table"] = self._tabular(inner)
        else:
            block["graphic"] = self._graphic(inner)
        self.blocks.append(block)

    def _graphic(self, inner: str) -> dict:
        inc = re.search(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}", inner)
        if inc:
            frac = 1.0
            opt = inc.group(1) or ""
            fm = re.search(r"width\s*=\s*([\d.]*)\s*\\(columnwidth|textwidth|linewidth)", opt)
            if fm:
                frac = float(fm.group(1) or 1.0)
            else:
                raise Unsupported(f"includegraphics width I cannot read: {opt!r}")
            return {"type": "pdf", "path": self.dir / inc.group(2), "frac": frac,
                    "wide": "textwidth" in opt}
        tikz = re.search(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", inner, re.S)
        if tikz:
            size = re.search(r"\\(footnotesize|small|scriptsize|tiny)\b", inner)
            return {"type": "tikz", "code": tikz.group(0), "frac": 1.0,
                    "size": size.group(1) if size else "normalsize", "wide": False}
        raise Unsupported("figure float with neither includegraphics nor tikzpicture")

    def _tabular(self, inner: str) -> dict:
        m = re.search(r"\\begin\{tabular\}\s*\{([^}]*)\}(.*?)\\end\{tabular\}", inner, re.S)
        if not m:
            raise Unsupported("table float with no tabular")
        spec = [c for c in m.group(1) if c in "lcrp"]
        rows = []
        for raw in re.split(r"\\\\", strip_comments(m.group(2))):
            raw = raw.replace(r"\hline", "").strip()
            if not raw:
                continue
            cells = []
            for cell in split_cells(raw):
                span, text = 1, cell
                mc = re.match(r"\s*\\multicolumn\{(\d+)\}", cell)
                if mc:
                    span = int(mc.group(1))
                    _, j = brace_arg(cell, mc.end())      # the column spec
                    text, _ = brace_arg(cell, j)
                cells.append({"span": span,
                              "runs": self.inline.parse(text, "table cell")})
            rows.append(cells)
        if not rows:
            raise Unsupported("tabular with no rows")
        return {"cols": len(spec), "align": spec, "rows": rows}


def strip_comments(s: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", s)


def split_cells(row: str) -> list[str]:
    """Split a tabular row on unescaped & that are not inside braces."""
    out, depth, cur = [], 0, []
    i = 0
    while i < len(row):
        c = row[i]
        if c == "\\" and i + 1 < len(row):
            cur.append(row[i:i + 2])
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "&" and depth == 0:
            out.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    out.append("".join(cur))
    return out


# --------------------------------------------------------------------------- images


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[16:24]
    return struct.unpack(">II", data)


def render_graphic(g: dict, build: Path, index: int, preamble: str) -> Path:
    """Rasterise one float's artwork to PNG at roughly TARGET_DPI at its placed width."""
    out = build / f"fig{index}"
    if g["type"] == "pdf":
        src = g["path"]
        if not src.exists():
            raise Unsupported(f"missing figure file {src}")
    else:
        src = build / f"tikz{index}.tex"
        colw = COL_W / TWIP_PER_INCH * 72
        src.write_text(
            "\\documentclass[border=2pt]{standalone}\n"
            "\\usepackage{amsmath,amssymb}\n" + preamble +
            f"\\makeatletter\\setlength{{\\columnwidth}}{{{colw:.2f}pt}}\\makeatother\n"
            "\\begin{document}\n"
            f"\\{g['size']}\n{g['code']}\n\\end{{document}}\n", encoding="utf8")
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", src.name],
                           cwd=build, capture_output=True, text=True)
        src = build / f"tikz{index}.pdf"
        if not src.exists():
            raise Unsupported(f"tikz figure {index} did not compile:\n{r.stdout[-2000:]}")

    info = subprocess.run(["pdfinfo", str(src)], check=True, capture_output=True,
                          text=True).stdout
    w_pt, h_pt = (float(x) for x in re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info).groups())
    avail = TEXT_W if g["wide"] else COL_W
    placed_in = g["frac"] * avail / TWIP_PER_INCH
    dpi = max(200, min(900, round(TARGET_DPI * placed_in / (w_pt / 72))))
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile", str(src), str(out)],
                   check=True, capture_output=True)
    png = out.with_suffix(".png")
    if not png.exists():
        raise Unsupported(f"pdftoppm produced nothing for {src}")
    g["emu_w"] = int(placed_in * EMU_PER_INCH)
    g["emu_h"] = int(placed_in * (h_pt / w_pt) * EMU_PER_INCH)
    return png


# --------------------------------------------------------------------------- OOXML


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def xml_runs(runs: list[dict], base_props: str = "") -> str:
    out = []
    for r in runs:
        if r.get("brk"):
            out.append("<w:r><w:br/></w:r>")
            continue
        if "footnote" in r:
            out.append('<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr>'
                       f'<w:footnoteReference w:id="{r["footnote"] + 1}"/></w:r>')
            continue
        props = base_props
        if r.get("b"):
            props += "<w:b/><w:bCs/>"
        if r.get("i"):
            props += "<w:i/><w:iCs/>"
        if r.get("sc"):
            props += "<w:smallCaps/>"
        if r.get("vert"):
            props += f'<w:vertAlign w:val="{r["vert"]}"/>'
        rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
        out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{esc(r["t"])}</w:t></w:r>')
    return "".join(out)


def para(style: str, runs: list[dict], extra_ppr: str = "", base_props: str = "") -> str:
    ppr = f'<w:pStyle w:val="{style}"/>{extra_ppr}' if style else extra_ppr
    return f"<w:p>{f'<w:pPr>{ppr}</w:pPr>' if ppr else ''}{xml_runs(runs, base_props)}</w:p>"


NO_NUMBER = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
NO_INDENT = '<w:ind w:firstLine="0"/>'

# The committee corrected item 5 after the first round: the abstract and the keywords stay at
# single spacing and the 0.95 begins after them, which is what the template's own compiled PDF
# does. Only the 0.51cm first line of item 6 is applied here; the Abstract style indents by
# 272 twips and Keywords by 274, where the body uses 288. The 10pt gap between the two (item 2
# of the correction) is the Abstract style's own after=200 and is deliberately left alone.
FRONT_SPACING = '<w:ind w:firstLine="288"/>'

# Item 13 asks for centred figure captions; the template's own figurecaption style is
# justified, and numId 2 gives it a hanging indent that would centre the text inside an
# indented block. Both are overridden, which is one of only two places where the committee's
# list and the template's styles.xml disagree -- the other is the bold on Keywords.
FIG_CAPTION = '<w:ind w:left="0" w:right="0" w:firstLine="0"/><w:jc w:val="center"/>'
TIMES = ('<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
         'w:cs="Times New Roman"/>')


def sect_pr(cols: int, continuous: bool) -> str:
    c = f'<w:cols w:num="2" w:space="{COL_GAP}"/>' if cols == 2 else '<w:cols w:space="720"/>'
    return (f'<w:sectPr>{"<w:type w:val=" + chr(34) + "continuous" + chr(34) + "/>" if continuous else ""}'
            f'<w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}" w:code="9"/>'
            f'<w:pgMar w:top="{MAR_TOP}" w:right="{MAR_SIDE}" w:bottom="{MAR_BOT}" '
            f'w:left="{MAR_SIDE}" w:header="720" w:footer="720" w:gutter="0"/>'
            f'{c}<w:docGrid w:linePitch="360"/></w:sectPr>')


def drawing(rel_id: str, name: str, emu_w: int, emu_h: int, doc_id: int) -> str:
    return (
        f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{emu_w}" cy="{emu_h}"/><wp:docPr id="{doc_id}" name="{esc(name)}"/>'
        f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="0" name="{esc(name)}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{emu_w}" cy="{emu_h}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


BORDER = ('<w:tblBorders>' + "".join(
    f'<w:{e} w:val="single" w:sz="2" w:space="0" w:color="auto"/>'
    for e in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders>')


def xml_table(tbl: dict) -> str:
    cols = tbl["cols"]
    grid = "".join(f'<w:gridCol w:w="{TEXT_W // cols}"/>' for _ in range(cols))
    rows = []
    for ri, cells in enumerate(tbl["rows"]):
        tcs = []
        for cell in cells:
            span = (f'<w:gridSpan w:val="{cell["span"]}"/>' if cell["span"] > 1 else "")
            style = "tablecolhead" if ri == 0 else "tablecopy"
            tcs.append(
                f'<w:tc><w:tcPr>{span}<w:vAlign w:val="center"/></w:tcPr>'
                f'{para(style, cell["runs"], NO_NUMBER + NO_INDENT)}</w:tc>')
        rows.append(f'<w:tr>{"<w:trPr><w:tblHeader/></w:trPr>" if ri == 0 else ""}'
                    f'{"".join(tcs)}</w:tr>')
    return ('<w:tbl><w:tblPr><w:tblW w:type="pct" w:w="5000"/>'
            f'<w:jc w:val="center"/>{BORDER}<w:tblLayout w:type="autofit"/>'
            '<w:tblCellMar><w:left w:w="57" w:type="dxa"/><w:right w:w="57" w:type="dxa"/>'
            '</w:tblCellMar></w:tblPr>'
            f'<w:tblGrid>{grid}</w:tblGrid>{"".join(rows)}</w:tbl>')


def build_document(paper: Paper, media: list[tuple[str, str, dict]], root: str) -> str:
    """Emit word/document.xml. Floats are placed inline where the source defines them."""
    body: list[str] = []

    body.append(para("papertitle", paper.title))
    for k, a in enumerate(paper.authors):
        last = k == len(paper.authors) - 1
        body.append(para("Author", a,
                         sect_pr(1, continuous=False) if last else ""))

    # IEEEtran prints the "Abstract—" and "Keywords—" labels itself; in Word they are literal
    # text, so they are added here rather than left to a style that cannot supply them.
    body.append(para("Abstract", [run("Abstract—", b=True, i=True)] + paper.abstract,
                     FRONT_SPACING, base_props="<w:b/><w:bCs/>"))
    if paper.keywords:
        # Bold italic, both label and terms. The Keywords style inherits bold from Abstract and
        # adds the italic, which is exactly what the template's compiled PDF shows; the
        # committee asked for "9pt and italic" because the terms were upright, not because the
        # line was bold. The bold is therefore left inherited rather than switched off.
        body.append(para("Keywords", [run("Keywords—")] + paper.keywords,
                         FRONT_SPACING, base_props="<w:b/><w:bCs/><w:i/><w:iCs/>"))

    gi = 0
    two_col = True
    for blk in paper.blocks:
        kind = blk["kind"]
        wide = blk.get("wide")
        if kind in ("figure", "table") and wide and two_col:
            # A full-width float needs a one-column stretch of its own, the Word equivalent of
            # figure*/table*. Section properties describe the section that ENDS at the
            # paragraph carrying them, so the break is written before the float.
            body.append(f'<w:p><w:pPr>{sect_pr(2, True)}</w:pPr></w:p>')
            two_col = False

        if kind == "p":
            body.append(para("GvdeMetni", blk["runs"]))
        elif kind in ("h1", "h2", "h3"):
            style = {"h1": "Balk1", "h2": "Balk2", "h3": "Balk3"}[kind]
            body.append(para(style, blk["runs"],
                             "" if blk["numbered"] else NO_NUMBER + NO_INDENT))
        elif kind == "li":
            if blk["ordered"]:
                runs = [run(f'{blk["n"]}) ')] + blk["runs"]
                body.append(para("GvdeMetni", runs,
                                 '<w:ind w:left="288" w:firstLine="0"/>'))
            else:
                body.append(para("bulletlist", blk["runs"]))
        elif kind == "eq":
            runs = [run("\t")] + blk["runs"]
            if blk["number"]:
                runs += [run("\t"), run(f'({blk["number"]})')]
            # The template's "equation" style sets the Symbol font, for Word's old equation
            # editor. Symbol maps the Latin alphabet onto Greek glyphs, so C[j]=K[s(j)] comes
            # out as X[φ]=K[σ(φ)]. The runs are put back into the document font explicitly.
            body.append(para("equation", runs, base_props=TIMES))
        elif kind in ("theorem", "proof"):
            label = blk["name"] + (f' {blk["number"]}' if blk.get("number") else "")
            head = [run(f"{label}. ", b=(kind == "theorem"), i=(kind == "proof"))]
            body.append(para("GvdeMetni", head + blk["runs"]))
        elif kind == "table":
            body.append(para("tablehead", blk["caption"]))
            body.append(xml_table(blk["table"]))
            body.append(para("", []))
        elif kind == "figure":
            rid, name, g = media[gi]
            gi += 1
            # w:ind precedes w:jc; w:pPr is a sequence, not a bag, and Word and LibreOffice
            # both refuse to open the file outright when its children are out of order.
            body.append(f'<w:p><w:pPr>{NO_INDENT}<w:jc w:val="center"/></w:pPr>'
                        f'{drawing(rid, name, g["emu_w"], g["emu_h"], gi)}</w:p>')
            body.append(para("figurecaption", blk["caption"], FIG_CAPTION))

        if kind in ("figure", "table") and wide and not two_col:
            body.append(f'<w:p><w:pPr>{sect_pr(1, True)}</w:pPr></w:p>')
            two_col = True

    body.append(para("Balk1", [run("References")], NO_NUMBER + NO_INDENT))
    for key in paper.bib_order:
        entry = paper.inline.parse(paper.bib_text[key], f"bibliography entry {key}")
        body.append(para("references", entry))

    body.append(sect_pr(2, True))

    # The template's own <w:document> start tag is reused verbatim. Its namespace set is long
    # and order-sensitive in ways the consumers care about, and a hand-written substitute is
    # rejected outright -- the file simply will not open, with no indication of which
    # declaration was missing.
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'{root}<w:body>{"".join(body)}</w:body></w:document>')


def build_footnotes(paper: Paper, template_xml: str) -> str:
    """Append the paper's footnotes to the template's separator entries."""
    head, tail = template_xml.rsplit("</w:footnotes>", 1)[0], "</w:footnotes>"
    parts = []
    for k, runs in enumerate(paper.footnotes, start=2):
        ref = ('<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr>'
               '<w:footnoteRef/></w:r>')
        # w:framePr comes before w:numPr in the w:pPr sequence. The template's own footnote
        # style anchors a floating frame, which real Word footnotes do not want, so the frame
        # is neutralised here and the numbering left to Word's footnote counter.
        parts.append(
            f'<w:footnote w:id="{k}"><w:p><w:pPr><w:pStyle w:val="footnote"/>'
            f'<w:framePr w:wrap="auto" w:vAnchor="text" w:hAnchor="text"/>{NO_NUMBER}'
            f'<w:jc w:val="both"/></w:pPr>{ref}'
            f'<w:r><w:t xml:space="preserve"> </w:t></w:r>'
            f'{xml_runs(runs)}</w:p></w:footnote>')
    return head + "".join(parts) + tail


# --------------------------------------------------------------------------- package


def assemble(template: Path, out: Path, document: str, footnotes: str,
             media: list[tuple[str, str, dict]], pngs: dict[str, Path]):
    with zipfile.ZipFile(template) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}

    rels = data["word/_rels/document.xml.rels"].decode("utf8")
    added = "".join(
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/image" Target="media/{name}"/>'
        for rid, name, _ in media)
    data["word/_rels/document.xml.rels"] = rels.replace(
        "</Relationships>", added + "</Relationships>").encode("utf8")

    ct = data["[Content_Types].xml"].decode("utf8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Default Extension=", '<Default Extension="png" '
                        'ContentType="image/png"/><Default Extension=', 1)
    data["[Content_Types].xml"] = ct.encode("utf8")

    data["word/document.xml"] = document.encode("utf8")
    data["word/footnotes.xml"] = footnotes.encode("utf8")
    for name, path in pngs.items():
        data[f"word/media/{name}"] = path.read_bytes()

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, blob in data.items():
            z.writestr(n, blob)


def tikz_preamble(paper_dir: Path) -> str:
    src = (paper_dir / "main.tex").read_text(encoding="utf8")
    keep = [ln for ln in src.split("\n")
            if re.match(r"\\(usepackage\{(tikz|pgfplots)\}|usetikzlibrary|pgfplotsset)", ln)]
    return "\n".join(keep) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper_dir", type=Path)
    ap.add_argument("template", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--keep-build", action="store_true")
    args = ap.parse_args()

    paper = Paper(args.paper_dir)

    build = Path(tempfile.mkdtemp(prefix="tex2docx-"))
    media, pngs = [], {}
    preamble = tikz_preamble(args.paper_dir)
    fig_i = 0
    for blk in paper.blocks:
        if blk["kind"] != "figure":
            continue
        fig_i += 1
        g = blk["graphic"]
        g["wide"] = blk["wide"] or g.get("wide", False)
        png = render_graphic(g, build, fig_i, preamble)
        name = f"image{fig_i}.png"
        pngs[name] = png
        media.append((f"rIdImg{fig_i}", name, g))

    with zipfile.ZipFile(args.template) as z:
        tpl_doc = z.read("word/document.xml").decode("utf8")
        footnotes = build_footnotes(paper, z.read("word/footnotes.xml").decode("utf8"))
    root = re.search(r"<w:document\b[^>]*>", tpl_doc).group(0)
    document = build_document(paper, media, root)
    assemble(args.template, args.out, document, footnotes, media, pngs)

    if args.keep_build:
        print(f"build dir: {build}")
    else:
        shutil.rmtree(build, ignore_errors=True)
    print(f"wrote {args.out}  "
          f"({len(paper.blocks)} blocks, {fig_i} figures, "
          f"{sum(1 for b in paper.blocks if b['kind'] == 'table')} tables, "
          f"{len(paper.footnotes)} footnotes, {len(paper.bib_order)} references)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Unsupported as e:
        print(f"tex2docx: {e}", file=sys.stderr)
        raise SystemExit(1)
