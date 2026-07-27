#!/usr/bin/env python3
"""float_refs.py <main_filled.tex> — exit 1 if any float lacks a subject-position reference.

A reference counts as subject-position when the float name is the grammatical subject of a
reporting verb: it opens a clause AND is followed by a verb. Anything else is parenthetical.
"""
import re, sys, collections

VERBS = (r'shows?|reports?|lists?|plots?|gives?|states?|summaris(?:es|e)|summariz(?:es|e)|'
         r'sketch(?:es)?|compares?|contrasts?|records?|places?|makes?|presents?|displays?|'
         r'sets?|orders?|breaks?|traces?|confirms?|puts?|adds?|holds?|marks?|reveals?')

CMD = re.compile(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})*')  # \subsection{X}, \end{enumerate}
MATH = re.compile(r'\$[^$]*\$')

def opens_clause(pre: str) -> bool:
    p = MATH.sub('X', pre)
    prev = None
    while p != prev:                       # peel nested LaTeX commands/groups
        prev = p
        p = CMD.sub(' ', p)
        p = re.sub(r'\{[^{}]*\}', ' ', p)
    p = p.rstrip()
    if p == '' or p.endswith(('.', ';', ':', '!', '?')):
        return True
    if re.search(r'(?:^|[.;:,]\s*)(?:and|or|while|whereas|then)$', p):
        return True
    # sentence-initial adverbial: "Finally, Fig. 6 shows ..." / "In Section III, Table II lists ..."
    if p.endswith(','):
        head = p[:-1]
        cut = max(head.rfind('.'), head.rfind(';'), head.rfind(':'))
        lead = head[cut + 1:].strip()
        if lead and len(lead.split()) <= 4:
            return True
    return False

src  = re.sub(r'(?<!\\)%.*', '', open(sys.argv[1]).read())
body = re.sub(r'\\begin\{(figure\*?|table\*?|algorithm)\}.*?\\end\{\1\}', '', src, flags=re.S)
body = re.sub(r'[ \t]+', ' ', body)

labels = re.findall(r'\\begin\{(?:figure\*?|table\*?|algorithm)\}.*?\\label\{([^}]+)\}', src, flags=re.S)
subj, n_subj, n_paren = collections.Counter(), 0, 0

for m in re.finditer(r'(?:Fig|Table|Algorithm)s?\.?~?\s*\\ref\{([^}]+)\}', body):
    pre  = body[max(0, m.start()-120):m.start()]
    post = body[m.end():m.end()+60]
    if opens_clause(pre) and re.match(r'\s+(?:%s)\b' % VERBS, post):
        n_subj += 1; subj[m.group(1)] += 1
    else:
        n_paren += 1

if not labels:
    print("ERROR: no floats found - wrong file, or the float regex needs updating"); sys.exit(2)
missing = [l for l in labels if subj[l] == 0]
print(f"floats: {len(labels)}   subject-position: {n_subj}   parenthetical: {n_paren}")
print("floats with NO subject-position reference:", missing or "NONE")
sys.exit(1 if missing else 0)
