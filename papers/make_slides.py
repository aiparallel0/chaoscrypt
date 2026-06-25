"""Build extensive English UBMK presentation decks for both papers.

Loads the official UBMK presentation template (so the conference banner, logos, theme, and fonts are
inherited), clears its placeholder slides, and rebuilds two decks following the template's section
structure (Title, Introduction, Method, Models/Formulas/Techniques, Experimental Setup, Findings &
Discussion, Conclusions & Future Research, References, Appendix). Figures are embedded as PNGs.

Inputs (session assets, set the two paths below):
  * TEMPLATE - the official UBMK presentation .pptx (provides the theme, conference banner, and logos).
  * IMG - a directory of 13 PNGs: the 11 paper figures plus 2 schematics. Regenerate with:
      # figures -> PNG
      for f in papers/paper1-chaos-cpa/figures/{break_grid,cipher_hist,correlation_scatter,
               diffusion_diff,keystream_ridgeline}.pdf; do pdftoppm -png -r 300 -singlefile "$f" \
               $IMG/p1_$(basename $f .pdf); done
      for f in papers/paper2-ids-selective/figures/{risk_coverage,reliability_rf,ece_shift,
               openset_detection,benign_manifold,novelty_auroc}.pdf; do pdftoppm -png -r 300 \
               -singlefile "$f" $IMG/p2_$(basename $f .pdf); done
      # the two TikZ schematics (LLEO pipeline, abstention pipeline) compiled standalone -> p1_schema.png,
      #   p2_pipeline.png (the tikz source is the fig:schema / fig:pipeline picture in each main.tex).

Usage: python papers/make_slides.py  (writes presentation.pptx into each paper directory).
"""
from __future__ import annotations
from pathlib import Path
import re
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.ns import qn

HERE = Path(__file__).parent
TEMPLATE = Path("/root/.claude/uploads/12438de2-6e29-57ba-95f0-c12f8bed9348/5099950c-UBMK2025SunumTaslak.pptx")
IMG = Path("/tmp/claude-0/-home-user/12438de2-6e29-57ba-95f0-c12f8bed9348/scratchpad/slides_img")

SW, SH = Inches(13.333), Inches(7.5)
NAVY = RGBColor(0x1F, 0x33, 0x55)
ACCENT = RGBColor(0xD5, 0x5E, 0x00)
GREY = RGBColor(0x55, 0x55, 0x55)
L_TITLE, L_TITLECONTENT, L_TITLEONLY, L_BLANK = 0, 1, 5, 6


# ----------------------------------------------------------------------------- text normalization
# PowerPoint's default theme font renders only a limited glyph set; math/exotic Unicode (subscripts,
# superscripts, ceiling brackets, double-struck Z, arrows, etc.) shows as missing-glyph boxes. Convert
# such characters to robust ASCII so the slide text renders everywhere. Plain typographic characters
# (en/em dash, curly quotes, middle dot, multiplication sign) are kept -- they render in every font.
_SUB = {c: d for c, d in zip("₀₁₂₃₄₅₆₇₈₉", "0123456789")}
_SUP = {c: d for c, d in zip("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")}
_REPL = {"ℤ": "Z", "⌈": "ceil(", "⌉": ")", "≈": "~", "≲": "<=", "≤": "<=", "≥": ">=",
         "→": " -> ", "−": "-", "χ": "chi", "Δ": "Delta ", "≠": "!="}
_SUBRE = re.compile("[" + "".join(_SUB) + "]+")
_SUPRE = re.compile("[" + "".join(re.escape(c) for c in _SUP) + "]+")


def ascii_safe(t: str) -> str:
    t = _SUBRE.sub(lambda m: "_" + "".join(_SUB[c] for c in m.group()), t)
    t = _SUPRE.sub(lambda m: "^" + "".join(_SUP[c] for c in m.group()), t)
    for a, b in _REPL.items():
        t = t.replace(a, b)
    return re.sub(r"\s+->\s+", " -> ", t)


# ----------------------------------------------------------------------------- low-level helpers
def clear_slides(prs):
    """Remove the template's placeholder slides: drop each slide relationship (so the orphaned slide
    parts are not written on save) and remove its sldId reference."""
    ids = prs.slides._sldIdLst
    for sldId in list(ids):
        prs.part.drop_rel(sldId.get(qn("r:id")))
        ids.remove(sldId)


def _title(slide, text, size=30):
    t = slide.shapes.title
    t.text = ascii_safe(text)
    for p in t.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = NAVY
    return t


def _content_ph(slide):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 1:
            return ph
    return None


def _drop_empty_placeholders(slide, keep_title=True):
    """Remove the content placeholder so it doesn't show 'Click to add text' on figure slides."""
    for ph in list(slide.placeholders):
        if ph.placeholder_format.idx != 0:
            ph._element.getparent().remove(ph._element)


def _bullets(tf, items, base=20, clear=True):
    if clear:
        tf.clear()
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    for i, (txt, lvl) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 and clear else tf.add_paragraph()
        p.text = ascii_safe(txt)
        p.level = lvl
        p.space_after = Pt(4)
        sz = base - 2 * lvl
        for r in p.runs:
            r.font.size = Pt(sz)
            r.font.color.rgb = NAVY if lvl == 0 else GREY
    return tf


def _textbox(slide, left, top, width, height, items, base=18, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    for i, (txt, lvl) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = ascii_safe(txt)
        p.level = lvl
        p.alignment = align
        p.space_after = Pt(4)
        for r in p.runs:
            r.font.size = Pt(base - 2 * lvl)
            r.font.color.rgb = NAVY if lvl == 0 else GREY
    return tb


def _fit(img_path, box_l, box_t, box_w, box_h):
    """Return (left, top, width, height) fitting the image in the box, preserving aspect, centered."""
    w, h = Image.open(img_path).size
    ar = w / h
    box_ar = box_w / box_h
    if ar > box_ar:
        nw = box_w; nh = int(box_w / ar)
    else:
        nh = box_h; nw = int(box_h * ar)
    return int(box_l + (box_w - nw) / 2), int(box_t + (box_h - nh) / 2), nw, nh


def _picture(slide, img_path, box_l, box_t, box_w, box_h):
    l, t, w, h = _fit(str(img_path), box_l, box_t, box_w, box_h)
    return slide.shapes.add_picture(str(img_path), l, t, w, h)


def _caption(slide, text, left, top, width):
    tb = slide.shapes.add_textbox(left, top, width, Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = ascii_safe(text)
    r.font.size = Pt(12); r.font.italic = True; r.font.color.rgb = GREY
    return tb


# ----------------------------------------------------------------------------- slide builders
def title_slide(prs, title, subtitle_lines):
    s = prs.slides.add_slide(prs.slide_layouts[L_TITLEONLY])
    _title(s, title, size=30)
    s.shapes.title.top = Inches(2.2); s.shapes.title.left = Inches(0.8)
    s.shapes.title.width = Inches(11.7); s.shapes.title.height = Inches(2.2)
    _textbox(s, Inches(0.8), Inches(4.6), Inches(11.7), Inches(2.0),
             [(t, 0) for t in subtitle_lines], base=18, align=PP_ALIGN.CENTER)
    return s


def bullet_slide(prs, title, items, base=18):
    s = prs.slides.add_slide(prs.slide_layouts[L_TITLECONTENT])
    _title(s, title)
    ph = _content_ph(s)
    # set ALL four (setting only top/height would default left/width to 0 -> zero-width text box)
    ph.left = Inches(0.7); ph.top = Inches(1.95); ph.width = Inches(11.95); ph.height = Inches(4.5)
    _bullets(ph.text_frame, items, base=base)
    return s


def figure_slide(prs, title, img, caption=None, bullets=None, img_frac=0.62):
    """Title + a figure. If bullets, figure left / bullets right; else figure centered.
    Content is kept above ~6.4" to clear the master's footer banner and logos (top ≈ 6.69")."""
    s = prs.slides.add_slide(prs.slide_layouts[L_TITLEONLY])
    _title(s, title)
    _drop_empty_placeholders(s)
    top = Inches(1.6); bottom = Inches(6.35); cap_h = Inches(0.32)
    img_bottom = bottom - (cap_h if caption else 0)
    if bullets:
        fw = int(Inches(13.0) * img_frac)
        _picture(s, img, Inches(0.35), top, fw, img_bottom - top)
        _textbox(s, Inches(0.4) + fw, Inches(1.75), Inches(12.9) - fw, Inches(4.6), bullets, base=16)
        if caption:
            _caption(s, caption, Inches(0.35), img_bottom, fw)
    else:
        _picture(s, img, Inches(0.7), top, Inches(11.9), img_bottom - top)
        if caption:
            _caption(s, caption, Inches(0.7), img_bottom, Inches(11.9))
    return s


def two_figure_slide(prs, title, imgL, imgR, bullets, capL=None, capR=None):
    s = prs.slides.add_slide(prs.slide_layouts[L_TITLEONLY])
    _title(s, title)
    _drop_empty_placeholders(s)
    top = Inches(1.6); fig_h = Inches(3.05)
    _picture(s, imgL, Inches(0.5), top, Inches(6.1), fig_h)
    _picture(s, imgR, Inches(6.8), top, Inches(6.1), fig_h)
    capy = top + fig_h
    if capL:
        _caption(s, capL, Inches(0.5), capy, Inches(6.1))
    if capR:
        _caption(s, capR, Inches(6.8), capy, Inches(6.1))
    _textbox(s, Inches(0.6), Inches(5.15), Inches(12.2), Inches(1.25), bullets, base=15)
    return s


def closing_slide(prs, big, small):
    s = prs.slides.add_slide(prs.slide_layouts[L_TITLEONLY])
    _title(s, big, size=40)
    s.shapes.title.top = Inches(2.6); s.shapes.title.height = Inches(1.5)
    _textbox(s, Inches(0.8), Inches(4.2), Inches(11.7), Inches(1.2), [(small, 0)],
             base=18, align=PP_ALIGN.CENTER)
    return s


# ----------------------------------------------------------------------------- deck assembly
def build(content, out_path):
    prs = Presentation(str(TEMPLATE))
    clear_slides(prs)
    for item in content:
        kind, args = item[0], item[1:]
        if kind == "title":
            title_slide(prs, *args)
        elif kind == "bul":
            bullet_slide(prs, *args)
        elif kind == "fig":
            figure_slide(prs, *args)
        elif kind == "fig2":
            two_figure_slide(prs, *args)
        elif kind == "end":
            closing_slide(prs, *args)
    prs.save(str(out_path))
    print(f"wrote {out_path} ({len(content)} slides)")


def im(name):
    return IMG / name


# ============================================================================ PAPER 1 content
P1 = [
    ("title",
     "An Equivalent-Key Chosen-Plaintext Break of a 2025 Chaos-Based Image Cipher",
     ["Good statistics are not security: a 2025 cipher broken in 4 chosen plaintexts",
      "UBMK’25 · International Conference on Computer Science and Engineering",
      "Track: Computer and Data Security",
      "Author(s) and affiliation withheld for review"]),

    ("bul", "Introduction: chaos image ciphers keep breaking the same way", [
        ("Chaos-based image ciphers scramble a picture using chaotic (random-looking) math. Most follow a "
         "permutation–diffusion design: first shuffle the pixels around (confusion), then mask their "
         "values with a keystream — a long random-looking sequence the cipher mixes in (diffusion).", 0),
        ("Recurring lesson: if that keystream depends only on the secret key (never on the image), the "
         "whole cipher is one fixed transformation — so an equivalent key (a stand-in that decrypts any "
         "image without being the real key) can be recovered from a few chosen plaintexts (images the "
         "attacker picks and has the cipher encrypt).", 0),
        ("Second problem (method): schemes are judged by statistics — entropy (a randomness score), "
         "neighbouring-pixel correlation, NPCR/UACI — and near-ideal values are treated as proof of "
         "security.", 0),
        ("But none of those scores tests resistance to a chosen-plaintext attack.", 1),
        ("Why this matters operationally: image ciphers protect real data — medical scans, sealed "
         "evidence, access-controlled documents. A break is not a per-image slip but a standing ability "
         "to decrypt every future ciphertext of that size, so security must rest on an attack model, "
         "not a statistics table.", 0),
        ("We apply both lessons to a 2025 scheme — “LLEO” (Jain et al., Optik, 2025).", 0),
    ]),

    ("fig", "The target: LLEO (Jain et al., Optik 2025)", im("p1_schema.png"),
     "LLEO encryption (top) and the equivalent-key attack (bottom).", [
        ("Two chaotic maps (simple formulas whose output looks random — Lorenz and logistic) make the "
         "keystream that masks each pixel (multiply by K).", 0),
        ("Then two Fisher–Yates shuffles (a standard way to randomly reorder a list) rearrange 16 "
         "row-blocks, then 16 column-blocks.", 0),
        ("Every key element comes from the secret key alone — nothing depends on the image X.", 0),
        ("Called “asymmetric,” but the same keys both encrypt and decrypt: it is really symmetric.", 0),
     ], 0.66),

    ("bul", "Key insight: LLEO is one fixed “multiply-and-reorder” map", [
        ("Write the image as a list of n = M×N pixels. Every step is just multiply-and-reorder using "
         "arithmetic that wraps around at 256 (like hours on a clock), and is fixed once the key is set.", 0),
        ("Masking multiplies pixel p by a fixed odd number K[p] (odd, so it can always be divided back "
         "out); the two shuffles combine into one fixed reordering of positions.", 0),
        ("So  C[j] = K[s(j)] · X[s(j)]  (mod 256): each output pixel is exactly one input pixel times a "
         "fixed number — a “monomial” map.", 0),
        ("Two gifts to the attacker: no added constant, and no diffusion (each output pixel depends on "
         "only one input pixel).", 0),
    ]),

    ("bul", "Four images recover the full map", [
        ("(a) The multiplier — 1 query: encrypt an all-ones image; the output directly reveals K at "
         "every position.", 0),
        ("(b) The reordering — a few queries: encrypt images whose pixels carry their own position "
         "number, then divide out the known K to read off where each pixel came from (the map s).", 0),
        ("The pair (s, K) is the equivalent key — it inverts any ciphertext:  X[s(j)] = K[s(j)]⁻¹ · C[j].", 0),
        ("Total cost: 1 + ⌈log₂₅₆ MN⌉ chosen plaintexts = just 4 for a 512×512 image — no matter how "
         "long the advertised key is.", 0),
        ("This matches the known best-possible bound for shuffle-only ciphers; adding more rounds or "
         "maps doesn't change the form, so the same attack still works.", 0),
    ]),

    ("bul", "Experimental setup", [
        ("Reconstructed LLEO from its published description — reimplemented from scratch, no code "
         "reused.", 0),
        ("Four standard 512×512 grayscale images (Cameraman, Moon, Gravel, Brick); one fixed secret "
         "key.", 0),
        ("Verified the reconstruction reproduces LLEO's reported statistics before attacking.", 0),
        ("All timings single-core wall-clock.", 0),
    ]),

    ("fig", "Result: every image recovered pixel-exactly, without the key", im("p1_break_grid.png"),
     "Original → LLEO ciphertext → key-free recovery (bit-identical), four images.", [
        ("Only 4 chosen plaintexts per image.", 0),
        ("Recovery is bit-identical to the original.", 0),
        ("Decryption in 0.037 s at 512x512 (single core) — no key used.", 0),
     ], 0.7),

    ("fig2", "Good statistics are not security",
     im("p1_cipher_hist.png"), im("p1_correlation_scatter.png"), [
        ("Entropy (a randomness score, maximum 8) rises 7.23 → 7.99; neighbouring pixels go from very "
         "alike to almost unrelated (correlation ≈ 0); the spread of pixel values is flat.", 0),
        ("By every usual yardstick LLEO looks strong — yet it is broken in 4 queries.", 0),
     ], "Flat histogram of cipher pixel values", "Neighbouring-pixel pattern: structure → uniform"),

    ("fig", "The “differential” score (NPCR) is illusory", im("p1_diffusion_diff.png"),
     "Difference image |C₀−C₁|: dark = unchanged, bright = changed (one fixed key).", [
        ("NPCR = the percent of pixels that change when you flip a single input pixel. A good cipher "
         "should change almost all of them (~99.6%), and LLEO reports ~99.6%.", 0),
        ("But with no diffusion, flipping one input pixel changes exactly one output pixel — so the "
         "true value is 100/MN ≈ 0.0004%, five orders of magnitude smaller.", 0),
        ("The 99.6% is really just the difference between two unrelated images (here 99.88%), which any "
         "near-uniform cipher reaches and which says nothing about security.", 0),
     ], 0.6),

    ("fig", "Even the chaotic keystreams are not evenly random", im("p1_keystream_ridgeline.png"),
     "How often each byte value appears: logistic and Lorenz vs. a truly uniform source.", [
        ("A chi-square test (a standard check for whether values are evenly spread) strongly rejects "
         "“evenly random” for both chaotic streams (logistic χ² ≈ 5.3×10⁵).", 0),
        ("A secure keystream would be flat, like the uniform reference row at the bottom.", 0),
     ], 0.6),

    ("fig", "The contribution: a reusable structural audit", im("p1_oracle_corpus.png"),
     "Recoverability R per scheme on an archetype corpus (red = broken, green = resists); chosen plaintexts at 512x512.", [
        ("We package the attack as a black-box test: given only the ability to encrypt chosen images, it "
         "decides whether a cipher is one fixed plaintext-independent map and, if so, recovers an "
         "equivalent key -- knowing nothing about the scheme inside, and CERTIFYING each verdict by "
         "predicting fresh ciphertext exactly (a check we prove sound).", 0),
        ("On 8 structural archetypes it breaks all 5 fully key-only ones at R = 1 in <= 5 chosen plaintexts "
         "(chaos, permutation, additive, affine, even a modern AES-CTR key stream); 2 image-/nonce-bound "
         "schemes correctly resist; a 6th, with non-invertible multipliers, degrades GRACEFULLY (R = 0.52, "
         "PARTIAL) -- the deliberate boundary.", 0),
        ("The chaos was never the point -- a reused, image-independent keystream is. This is a reusable "
         "audit, not a one-paper break.", 0),
     ], 0.6),

    ("fig", "Run on four real published 2023–2025 ciphers", im("p1_published_audit.png"),
     "The audit in its two signals (avalanche vs. recoverability) on real schemes rebuilt from their papers.", [
        ("We reconstructed four real, open-access chaos image ciphers from their equations and ran the "
         "audit. Each reproduces the originals' near-ideal entropy (~7.99) and inter-image NPCR (~99.6%) -- "
         "so the rebuilds behave like the published ciphers where it counts.", 0),
        ("Seeding decides the verdict. LSCM-CA (Sun et al. 2025) is key-only -> BROKEN (R = 1.0, 12 chosen "
         "plaintexts) -- but only after a GF(2)-affine 'bitlinear' extension to peel its per-pixel "
         "cellular-automata layer, which the plain affine/XOR model misses. The other three bind the "
         "keystream to the plaintext (SHA-256 / block sum) -> correctly RESIST.", 0),
        ("Honest limits: two 'resists' are thin (one injects only a 256-way scalar; one collapses if a "
         "64-pixel seed block is fixed), and the two cheap signals cannot tell genuine binding from a "
         "near-miss -- we mark this, not hide it. Reconstructions are paper-only; LLEO is the one "
         "fully-validated break.", 0),
     ], 0.6),

    ("bul", "Discussion: good statistics are not security", [
        ("A flat histogram, ideal entropy, near-zero correlation, and a large inter-image NPCR all hold "
         "for our fixed, key-only map -- yet it is broken in 4 queries.", 0),
        ("The single deciding question is binary: does any key material depend on the image? The oracle "
         "answers it automatically for any scheme.", 0),
        ("The break is sound by construction: LLEO forces its multipliers odd (always invertible), and the "
         "equivalent key predicts fresh ciphertexts exactly -- the falsifiable check that the cipher truly "
         "ignores the image.", 0),
        ("(The scheme's 'asymmetric' label is also a misnomer -- same keys encrypt and decrypt -- but that "
         "is cosmetic.)", 0),
    ]),

    ("bul", "Conclusions, remedies, and disclosure", [
        ("LLEO is completely broken by an equivalent-key chosen-plaintext attack in 4 queries and a "
         "fraction of a second, despite near-ideal statistics.", 0),
        ("More than one break: the audit flags every fully key-only scheme in an 8-archetype corpus and, on "
         "four real published 2023-2025 ciphers, breaks the one key-only design (LSCM-CA) and clears three "
         "plaintext-bound ones -- one break needing a GF(2)-affine extension.", 0),
        ("Remedies (standard): (i) tie the keystream to the image (seed the chaos from a SHA-256 hash of "
         "the image); (ii) add real diffusion (a chaining rule). The identical attack then recovers 100% "
         "of pixels against the key-only cipher but only 0.25% (chance) once the keystream is "
         "image-seeded.", 0),
        ("Statistical scores should support -- not replace -- an explicit chosen-plaintext argument. "
         "Authors of both broken schemes (LLEO and LSCM-CA) emailed at submission; no response yet "
         "(responsible disclosure).", 0),
    ]),

    ("bul", "Appendix: why the break is sound (invertibility & fidelity)", [
        ("Odd multipliers: LLEO inverts its substitution by a modular conjugate, which forces every "
         "multiplier odd (always invertible mod 256). On the reconstruction all are odd and E(0)=0 holds "
         "exactly; if even multipliers were allowed the oracle degrades gracefully (about half the "
         "positions recovered) rather than returning a wrong inverse.", 0),
        ("Fidelity: matching entropy/correlation proves nothing -- the load-bearing check is that the "
         "recovered key predicts fresh ciphertexts exactly, which only a plaintext-independent cipher can.", 0),
        ("Generality & scale: a very different XOR-and-chain (CBC-like) cipher also falls in 3-4 chosen "
         "plaintexts; cost grows only logarithmically with image size (3-4 plaintexts up to 1024x1024).", 0),
    ]),

    ("bul", "Selected references", [
        ("J. Jain et al., “… image encryption …,” Optik 327:172304, 2025  (target scheme).", 0),
        ("C. Li et al., “When an attacker meets a cipher-image …,” survey of chaos-cipher breaks, 2019.", 0),
        ("G. Alvarez and S. Li, “Some basic cryptographic requirements for chaos-based cryptosystems,” 2006.", 0),
        ("C.-Y. Li and C.-C. Lo, optimal known/chosen-plaintext bound for permutation-only ciphers, 2011.", 0),
        ("Y. Wu et al., NPCR and UACI randomness tests for image encryption, 2011.", 0),
    ]),

    ("end", "Thank you", "Questions?  ·  Reproduction and attack code released for verification."),
]


# ============================================================================ PAPER 2 content
P2 = [
    ("title",
     "Knowing When to Abstain: Calibration and Selective Prediction for ML Network Intrusion Detection",
     ["The much-cited 'detection collapse' on unknown attacks is mostly a thresholding artifact",
      "UBMK’25 · International Conference on Computer Science and Engineering",
      "Track: Computer and Data Security",
      "Author(s) and affiliation withheld for review"]),

    ("fig", "Introduction: detectors that fail silently", im("p2_pipeline.png"),
     "The selective-prediction (“reject-option”) wrapper we evaluate.", [
        ("A detector that outputs a single hard label (“attack” or “normal”) gives no signal of when to "
         "trust it — and stays silent on attacks it never saw in training.", 0),
        ("Why it matters: a missed novel attack reaches production before any analyst reviews it — "
         "exactly the case a single hard label handles worst.", 0),
        ("Better: let it abstain — say “I’m not sure” on low-confidence inputs and pass them to an "
         "analyst or a backup check. This is called selective prediction.", 0),
        ("Question: do ordinary, off-the-shelf detectors know when they are wrong?", 0),
        ("We propose no new detector; we test the ones people already use.", 1),
     ], 0.62),

    ("bul", "Contributions: a dissociation between two failure modes", [
        ("Over-confidence is task-dependent: detectors are badly miscalibrated under NSL-KDD's shift and "
         "NO post-hoc fix (Platt, isotonic, or temperature scaling) transfers -- yet on two modern flow "
         "datasets the same task is well calibrated.", 0),
        ("The benign-mimicry blind spot is an operating-point failure, not a representational one, and it "
         "recurs across all three datasets. R2L is nearly missed at the default threshold (recall 0.06) "
         "yet its score is discriminative (AUROC 0.87); a per-family threshold recovers much of it (0.49). "
         "Class balancing does not help -- so the cause is the threshold, not class frequency.", 0),
        ("Selective prediction is useful but bounded: it helps only when confidence ranks errors; and on "
         "the benign-mimicking blind spot the lever is the OPERATING POINT -- a budget-tuned threshold "
         "recovers most of what argmax misses, while stacking abstention+novelty adds no gain at matched "
         "cost.", 0),
    ]),

    ("bul", "Method", [
        ("Calibration -- does a model's stated confidence match how often it is right? We measure the gap "
         "with expected calibration error (ECE) -- and the Brier score, a proper scoring rule, agrees -- "
         "then try three standard fixes (Platt, isotonic, and temperature scaling), each fit only on "
         "held-out training data so no test information leaks in.", 0),
        ("Selective prediction -- confidence = the model's top class probability. The risk-coverage curve "
         "plots error against the fraction answered; the area under it (AURC) summarizes it (lower is "
         "better).", 0),
        ("Open-set (LOFO): drop one attack family from training, retrain, and measure detection on the "
         "unseen family. To separate a threshold artifact from true indistinguishability we also report "
         "threshold-free per-family detection AUROC.", 0),
        ("Honesty checks: a bootstrap over the (fixed) test set -- the seed-only intervals understate "
         "uncertainty about 5x -- and conformal prediction, which promises a hit-rate as long as new data "
         "looks like the old.", 0),
    ]),

    ("bul", "Models, confidence signals, and novelty detectors", [
        ("Detectors: logistic regression (a simple linear model), a random forest, and gradient "
         "boosting (both built from many decision trees) — deliberately ordinary; the subject is their "
         "confidence, not the architecture.", 0),
        ("A neural MLP is added as a supplementary fourth family in the model summary, to check the "
         "confidence-ranking finding generalizes beyond trees and the linear model.", 1),
        ("Confidence signals compared: the top class probability (max-softmax), how much the forest’s "
         "trees disagree, and two “distance-from-normal” scores (Mahalanobis and nearest-neighbour).", 0),
        ("Novelty detectors — trained only on normal traffic to flag anything unusual: Isolation Forest "
         "and a one-class SVM.", 0),
    ]),

    ("bul", "Experimental setup: datasets", [
        ("NSL-KDD — a public benchmark of network connections (~126k train / 22.5k test, 41 measured "
         "features each); attacks fall into four families (DoS, Probe, R2L, U2R). Its test set deliberately "
         "includes attack types missing from training — a built-in unknown-attack test.", 0),
        ("CIC-IDS-2017 — a newer dataset of network “flows” (per-connection summaries, 78 features), over "
         "three days (DDoS, PortScan, Web attacks).", 0),
        ("CSE-CIC-IDS-2018 — a different network and year, used to test transfer on the 27 features the "
         "two datasets share by name.", 0),
        ("Each result averages many random repeats; the official test sets are kept fixed.", 0),
    ]),

    ("fig", "Finding 1: the blind spot is a threshold failure, not indistinguishability",
     im("p2_perfamily_auroc.png"),
     "Per-family detection AUROC (threshold-free), family seen vs. held out of training.", [
        ("The most attackable reading -- 'R2L is just an unbalanced classifier at the default cut' -- is "
         "wrong about the cause. The attack score separates R2L from normal well above chance "
         "(AUROC 0.87 seen, 0.80 unknown).", 0),
        ("At the global default threshold only 0.06 of R2L is flagged; class-balancing barely moves it "
         "(0.06); a per-family threshold recovers 0.49. So a single global operating point fails a "
         "minority, look-like-normal family.", 0),
        ("Threshold-free, holding a family out of training costs little AUROC (DoS -0.06, R2L -0.07) -- so "
         "the dramatic 'detection collapse' on unknown families is largely a thresholding artifact.", 0),
     ], 0.6),

    ("fig", "Finding 2: over-confident under shift, and no calibrator fixes it",
     im("p2_calibration_methods.png"),
     "Calibration error on the shifted test set under four post-hoc calibrators (per model).", [
        ("On data like the training set the models are nearly perfectly calibrated (error below 0.01); on "
         "the real shifted test set it jumps to about 0.16-0.22.", 0),
        ("No post-hoc fix removes it: Platt, isotonic, and temperature scaling all stay high (every marker "
         "clusters at the top) -- each is fit on the source distribution.", 0),
        ("Source-calibrated probabilities do not certify the deployed distribution -- which is why we turn "
         "to abstention (it needs only a usable confidence ranking).", 0),
     ], 0.6),

    ("fig", "Finding 3: abstaining helps — if confidence ranks errors", im("p2_risk_coverage.png"),
     "Error among answered cases vs. the fraction answered; ring = the 80%-answered point.", [
        ("Tree-based models: refusing the least-confident 20% cuts error 0.20 → 0.11 (area under the "
         "curve ≈ 0.05; lower is better).", 0),
        ("The linear model’s confidence barely ranks its mistakes (area ≈ 0.23) — so abstaining buys "
         "little.", 0),
        ("Abstaining is only as good as the confidence signal behind it.", 0),
     ], 0.6),

    ("fig", "Finding 4: why R2L is the blind spot", im("p2_benign_manifold.png"),
     "(a) how unusual each record looks to two “normal-only” detectors; (b) the same, per family.", [
        ("R2L’s records pile up right on top of the normal ones — inside the “looks-normal” region — "
         "for both independent novelty detectors.", 0),
        ("It mimics ordinary traffic, so neither abstaining nor a normal-only novelty check can cleanly "
         "flag it; DoS, Probe, and U2R clearly stand out.", 0),
     ], 0.66),

    ("fig", "Finding 5: a normal-only novelty stage partly closes the gap", im("p2_novelty_auroc.png"),
     "How well each attack family separates from normal traffic (1 = perfect, 0.5 = chance).", [
        ("Trained only on normal traffic, Isolation Forest / one-class SVM separate DoS, Probe, U2R well "
         "(score ≈ 0.90–0.99).", 0),
        ("R2L stays hardest (≈ 0.73–0.82) — it overlaps normal traffic the most.", 0),
        ("Abstaining and novelty detection catch different failures, so use both.", 0),
     ], 0.6),

    ("fig", "The recipe, re-baselined honestly", im("p2_combined_pipeline.png"),
     "Unknown (held-out) R2L at a matched review budget: argmax vs tuned threshold vs full stack.", [
        ("The earlier 0.003 -> 0.40 gain was measured against the argmax default -- a bad threshold for a "
         "minority family. We re-baseline against a single threshold TUNED to the same review budget.", 0),
        ("At matched cost: argmax 0.00; a tuned threshold 0.51; the full stack (argmax+abstention+novelty) "
         "only 0.40 -- BELOW the tuned threshold (paired gap -0.11).", 0),
        ("So the lever is the operating point, not the gates: stacking adds no net recall once the "
         "threshold is set to the budget. (Even so, about half of unknown R2L is still missed.)", 0),
     ], 0.6),

    ("fig", "Validating the fix: across budgets and a second corpus", im("p2_validatefix.png"),
     "Tuned threshold vs. the full stack at matched analyst budget, on unknown R2L and cross-corpus Infiltration.", [
        ("Is the re-baseline a one-point fluke? We sweep three review budgets (5/10/20%) and add a second "
         "corpus -- CIC-2018 Infiltration, the look-like-normal family there.", 0),
        ("The abstention+novelty stack beats a budget-tuned threshold in just 1 of 6 budget x corpus cells "
         "(CIC at 5%, +0.015); it loses the other five, decisively on unknown R2L (e.g. -0.39 at 20%).", 0),
        ("So at equal analyst cost the stack adds no recall a tuned threshold doesn't already give -- and we "
         "tune the stack FAVOURABLY, not as a strawman; a harder-tuned threshold only widens the gap. "
         "(Headline gap: seed-paired -0.11; bootstrap -0.06, 95% CI [-0.10, 0.00].)", 0),
     ], 0.6),

    ("bul", "Finding 6: calibration need is task-dependent; the blind spot recurs (3 datasets)", [
        ("CIC-IDS-2017: the within-day task is easy and already well-calibrated (accuracy ~1.0, "
         "calibration error ~0.0001) -- over-confidence is a property of the task, not a built-in flaw.", 0),
        ("Drift (train one day, test another): Web detection 0.98 -> 0.79, and abstaining catches 0.95 of "
         "unknown Web -- far more than R2L, because Web does not look like normal traffic.", 0),
        ("CIC-IDS-2018 (third dataset): Infiltration is the canonical look-like-normal family and repeats "
         "the R2L signature exactly -- well-calibrated (error 0.006), yet missed at the default cut "
         "(recall 0.25) while its score is discriminative (AUROC 0.71) and a per-family threshold recovers "
         "0.39.", 0),
    ]),

    ("bul", "Which confidence signal? Can we promise a hit-rate?", [
        ("Comparing the signals fairly (same data, paired): the cheap top-probability is statistically "
         "tied with the fancier ones; the distance score is slightly better at ranking errors but worse "
         "at spotting unknown attacks.", 0),
        ("So on this kind of tabular traffic data, plain confidence is a strong default -- the value is "
         "in the abstain framework, not the exact signal. (Classical signals only; energy/ODIN-style "
         "scores need a neural net we deliberately avoid.)", 0),
        ("Conformal prediction's promised 90% hit-rate holds on training-like data (0.93) but falls to "
         "0.61 once the traffic shifts -- the guarantee breaks exactly when deployment changes.", 0),
    ]),

    ("bul", "Discussion: a practical recipe", [
        ("Pick a model whose confidence is informative (good at ranking its own errors — a tree-based "
         "model, not the linear one).", 0),
        ("Choose how much to answer from the risk–coverage curve; send the refused cases to a human or a "
         "backup check.", 0),
        ("Watch the abstain rate as a cheap, label-free warning that the traffic is drifting.", 0),
        ("Add a normal-only novelty check for the look-like-normal attacks abstaining cannot catch.", 0),
    ]),

    ("bul", "Conclusions and future work", [
        ("Detectors are over-confident under NSL-KDD's shift and not fixable by post-hoc calibration, yet "
         "well-calibrated on two modern datasets -- calibration need is task-dependent.", 0),
        ("The second failure recurs on all three datasets but is an operating-point one: a single global "
         "threshold misses minority look-like-normal families whose score is in fact discriminable -- so "
         "the much-cited 'detection collapse' is mostly a thresholding artifact.", 0),
        ("Abstention lowers error where confidence ranks it; and simply tuning the operating point to the "
         "analyst budget recovers much of the look-like-normal traffic the argmax default hides -- a "
         "stacked novelty gate adds no further recall at matched cost.", 0),
        ("Future: a full time-ordered evaluation, the label-corrected CIC-2017, and a shared NetFlow "
         "feature format for transfer across networks.", 0),
    ]),

    ("bul", "Selected references", [
        ("M. Tavallaee et al., “A detailed analysis of the KDD Cup 99 / NSL-KDD data set,” 2009.", 0),
        ("C. Guo et al., “On calibration of modern neural networks,” 2017.", 0),
        ("Y. Geifman and R. El-Yaniv, selective prediction / risk–coverage, 2017; El-Yaniv & Wiener, 2010.", 0),
        ("D. Hendrycks and K. Gimpel, max-softmax baseline for misclassification/OOD, 2017.", 0),
        ("D. Arp et al., “Dos and Don'ts of machine learning in computer security,” 2022.", 0),
        ("A. Angelopoulos and S. Bates, conformal prediction, 2023.", 0),
    ]),

    ("bul", "Appendix: uncertainty signals on NSL-KDD", [
        ("AURC (lower is better): max-softmax 0.060, Mahalanobis 0.058, k-NN 0.068, RF disagreement 0.060.", 0),
        ("Mahalanobis is marginally better at error-ranking but significantly worse at unknown-attack "
         "separation than max-softmax.", 0),
        ("Split-conformal coverage: 0.93 in-distribution → 0.61 under the train–test shift "
         "(target 0.90).", 0),
        ("All metrics: means over K seeds with 95% confidence intervals.", 0),
    ]),

    ("end", "Thank you", "Questions?  ·  LOFO protocol and analysis code released for verification."),
]


if __name__ == "__main__":
    build(P1, HERE / "paper1-chaos-cpa" / "presentation.pptx")
    build(P2, HERE / "paper2-ids-selective" / "presentation.pptx")
