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
import copy
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

HERE = Path(__file__).parent
TEMPLATE = Path("/root/.claude/uploads/12438de2-6e29-57ba-95f0-c12f8bed9348/5099950c-UBMK2025SunumTaslak.pptx")
IMG = Path("/tmp/claude-0/-home-user/12438de2-6e29-57ba-95f0-c12f8bed9348/scratchpad/slides_img")

SW, SH = Inches(13.333), Inches(7.5)
NAVY = RGBColor(0x1F, 0x33, 0x55)
ACCENT = RGBColor(0xD5, 0x5E, 0x00)
GREY = RGBColor(0x55, 0x55, 0x55)
L_TITLE, L_TITLECONTENT, L_TITLEONLY, L_BLANK = 0, 1, 5, 6


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
    t.text = text
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
    for i, (txt, lvl) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 and clear else tf.add_paragraph()
        p.text = txt
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
    for i, (txt, lvl) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = txt
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
    r = p.add_run(); r.text = text
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


def bullet_slide(prs, title, items, base=20):
    s = prs.slides.add_slide(prs.slide_layouts[L_TITLECONTENT])
    _title(s, title)
    ph = _content_ph(s)
    ph.top = Inches(1.95); ph.height = Inches(4.5)   # keep clear of the footer banner (top ~6.69")
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
        _textbox(s, Inches(0.4) + fw, Inches(1.75), Inches(12.9) - fw, Inches(4.4), bullets, base=17)
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
    _textbox(s, Inches(0.6), Inches(5.2), Inches(12.2), Inches(1.1), bullets, base=16)
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
     ["UBMK’25 · International Conference on Computer Science and Engineering",
      "Track: Computer and Data Security",
      "Author(s) and affiliation withheld for review"]),

    ("bul", "Introduction: chaos image ciphers keep breaking the same way", [
        ("Chaos-based image ciphers are published at a high rate; most follow a permutation–diffusion "
         "template (confusion + a chaotic keystream).", 0),
        ("Recurring lesson: when the keystream depends only on the key (not the image), the whole cipher "
         "is a fixed map — an equivalent key decrypts everything from a few chosen plaintexts.", 0),
        ("Second, methodological problem: schemes are validated with statistics (entropy, correlation, "
         "NPCR/UACI) and near-ideal values are treated as security.", 0),
        ("None of those scores measures chosen-plaintext resistance.", 1),
        ("We apply both lessons to a 2025 scheme — “LLEO” (Jain et al., Optik, 2025).", 0),
    ]),

    ("fig", "The target: LLEO (Jain et al., Optik 2025)", im("p1_schema.png"),
     "LLEO encryption (top) and the equivalent-key attack (bottom).", [
        ("Lorenz + logistic keystreams drive a per-pixel multiplicative substitution (×K).", 0),
        ("Then two Fisher–Yates block shuffles (16 rows, 16 columns).", 0),
        ("Every key element derives from the secret key — nothing depends on the image X.", 0),
        ("Called “asymmetric,” but the same keys encrypt and decrypt: it is symmetric.", 0),
     ], 0.66),

    ("bul", "Key insight: LLEO is a fixed monomial map", [
        ("Index the image as a length-n vector, n = M·N. Each step is linear over ℤ₂₅₆ "
         "and fixed by the key.", 0),
        ("Substitution multiplies pixel p by a fixed odd unit K[p]; the two shuffles compose into one "
         "permutation P.", 0),
        ("Therefore  C[j] = K[s(j)] · X[s(j)]  (mod 256),  with s = P⁻¹ — a fixed "
         "monomial map.", 0),
        ("No additive constant (E(0)=0); and no diffusion: each C[j] depends on exactly one input pixel.", 0),
    ]),

    ("bul", "Equivalent-key chosen-plaintext attack", [
        ("(a) Multiplier — one query: encrypt the all-ones image → C[j] = K[s(j)] (the multiplier "
         "at every output position).", 0),
        ("(b) Permutation — ⌈log₂₅₆ n⌉ queries: index-digit images; divide by the "
         "known K → recover the source map s.", 0),
        ("Equivalent key (s, K) inverts any ciphertext:  X[s(j)] = K[s(j)]⁻¹ · C[j].", 0),
        ("Cost: 1 + ⌈log₂₅₆ MN⌉ chosen plaintexts = 4 for a 512×512 image — "
         "independent of the advertised key length.", 0),
        ("Order-optimal vs. the Li–Lo permutation-only bound; extra rounds/maps leave the map's form "
         "unchanged.", 0),
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
        ("Decryption in a fraction of a second — no key used.", 0),
     ], 0.7),

    ("fig2", "Good statistics ≠ security",
     im("p1_cipher_hist.png"), im("p1_correlation_scatter.png"), [
        ("Cipher entropy 7.23 → 7.99 (near-ideal 8); adjacent-pixel correlation ≈ −0.007 "
         "(near zero); flat histogram.", 0),
        ("By the usual yardsticks LLEO looks strong — yet it is broken in 4 queries.", 0),
     ], "Flat cipher histogram", "Adjacent-pixel density: structure → uniform"),

    ("fig", "The differential metric (NPCR) is illusory", im("p1_diffusion_diff.png"),
     "|C₀−C₁|: dark = unchanged, bright = changed (one fixed key).", [
        ("LLEO reports NPCR ≈ 99.6% as differential-attack resistance.", 0),
        ("No diffusion → a one-pixel change alters exactly one ciphertext pixel: true NPCR = "
         "100/MN ≈ 0.0004%.", 0),
        ("The 99.6% is merely the gap between unrelated images (here 99.88%) — any near-uniform "
         "cipher attains it.", 0),
     ], 0.6),

    ("fig", "The chaotic keystreams are themselves non-uniform", im("p1_keystream_ridgeline.png"),
     "Byte-value densities: logistic and Lorenz vs. a uniform reference.", [
        ("A chi-square test rejects uniformity for the logistic (χ² ≈ 5.3×10⁵) and "
         "Lorenz keystreams.", 0),
        ("A secure stream cipher would match the flat uniform row.", 0),
     ], 0.6),

    ("bul", "Discussion: two persistent failure modes", [
        ("Good statistics are not security: flat histogram, ideal entropy, near-zero correlation, and a "
         "large inter-image NPCR all hold for our fixed, key-only map — broken in 4 queries.", 0),
        ("Naming is not architecture: labelling a symmetric construction “asymmetric” adds no "
         "security.", 0),
        ("The single deciding question: does any key material depend on the image?", 0),
    ]),

    ("bul", "Conclusions, remedies, and disclosure", [
        ("LLEO is completely broken by an equivalent-key chosen-plaintext attack in 4 queries and a "
         "fraction of a second, despite near-ideal statistics.", 0),
        ("Remedies (standard): (i) make the keystream plaintext-dependent (e.g., seed the chaos from "
         "SHA-256 of the image); (ii) add genuine diffusion (a chaining rule).", 0),
        ("Positive control: the identical attack recovers 100% of pixels against the key-only cipher, but "
         "only 0.25% (chance) once the keystream is SHA-256-seeded.", 0),
        ("Statistical scores should accompany — not replace — an explicit chosen-plaintext "
         "argument. Responsible disclosure to the authors before camera-ready.", 0),
    ]),

    ("bul", "Appendix: the attack is not specific to LLEO", [
        ("A canonical CBC-like XOR diffusion chain (different algebra) is affine over GF(2); recovered "
         "exactly in 3 chosen plaintexts at 128×128.", 0),
        ("Cost scales logarithmically: 3 chosen plaintexts at 128²/256², 4 at 512²/1024², "
         "each under 0.3 s.", 0),
        ("The same procedure fails against a plaintext-hash-seeded version — confirming that what "
         "matters is the keystream's dependence on the image, not the algebra or round count.", 0),
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
     ["UBMK’25 · International Conference on Computer Science and Engineering",
      "Track: Computer and Data Security",
      "Author(s) and affiliation withheld for review"]),

    ("fig", "Introduction: detectors that fail silently", im("p2_pipeline.png"),
     "The selective-prediction (reject-option) wrapper we evaluate.", [
        ("A detector that emits one hard label gives no signal of when to trust it — and fails "
         "silently on attacks absent from training.", 0),
        ("A reject option — abstain on low-confidence inputs, defer to an analyst or a novelty "
         "stage — would be more useful.", 0),
        ("Question: do off-the-shelf detectors know when they are wrong?", 0),
        ("We propose no new detector; we evaluate existing ones.", 1),
     ], 0.62),

    ("bul", "Contributions (finding-first)", [
        ("A controlled leave-one-family-out (LOFO) open-set protocol: detection collapses on held-out "
         "families; a confidence reject option covers only part; benign-mimicking R2L is a structural "
         "blind spot — missed by abstention and a benign-only novelty stage alike.", 0),
        ("Selective prediction cuts selective risk substantially — but only for models whose "
         "confidence ranks their errors (tree ensembles, not the linear model); conformal coverage erodes "
         "under shift.", 0),
        ("Mechanism: the three standard detectors are over-confident under distribution shift, and "
         "source-fit Platt scaling does not transfer.", 0),
    ]),

    ("bul", "Method", [
        ("Calibration: expected calibration error (15 bins), reliability diagrams, Platt scaling — fit "
         "on held-out TRAIN only (no test leakage, per Arp et al. 2022).", 0),
        ("Selective prediction: confidence = max class probability; risk–coverage curve, area under it "
         "(AURC), and risk at 80% coverage.", 0),
        ("Open-set (LOFO): remove one attack family from training, retrain, measure detection and "
         "abstention on that family.", 0),
        ("Conformal: split conformal prediction for distribution-free coverage under exchangeability.", 0),
        ("Multi-seed (K = 15/10/8): means with 95% CIs; paired per-seed differences for equivalence "
         "claims.", 0),
    ]),

    ("bul", "Models, signals, and uncertainty estimators", [
        ("Detectors: logistic regression, random forest, histogram gradient boosting (scikit-learn) — "
         "deliberately standard; the subject is their confidence, not their architecture.", 0),
        ("Abstention signals compared: max-softmax (MSP), random-forest disagreement, Mahalanobis "
         "distance, k-NN distance.", 0),
        ("Benign-only novelty detectors: Isolation Forest, one-class SVM (trained on benign records only).", 0),
        ("Post-hoc calibration: Platt (sigmoid) scaling.", 0),
    ]),

    ("bul", "Experimental setup: datasets", [
        ("NSL-KDD: ~126k train / 22.5k test records, 41 features; families DoS, Probe, R2L, U2R. The "
         "published test split deliberately contains attack types absent from training (a built-in "
         "open-set test).", 0),
        ("CIC-IDS-2017: a modern flow corpus (78 CICFlowMeter features), three days (DDoS, PortScan, Web).", 0),
        ("CSE-CIC-IDS-2018: cross-corpus transfer on the 27 features whose names match exactly across the "
         "two releases.", 0),
        ("Canonical test partitions held fixed; resample the fit/calibration split and model seed across "
         "K seeds.", 0),
    ]),

    ("fig", "Finding 1: detection collapses on unknown families (LOFO)", im("p2_openset_detection.png"),
     "Detection rate when a family is seen in training vs. held out (unknown).", [
        ("DoS 0.86 → 0.60; Probe 0.79 → 0.43; U2R 0.18 → 0.05 when held out.", 0),
        ("Abstention rejects only part of the unknowns (DoS 0.41, Probe 0.37).", 0),
        ("R2L is low even when seen (0.07) — it mimics benign traffic.", 0),
     ], 0.6),

    ("fig2", "Finding 2: detectors are over-confident under shift",
     im("p2_ece_shift.png"), im("p2_reliability_rf.png"), [
        ("In-distribution the same models are nearly perfectly calibrated (ECE ≲ 0.003); on the "
         "shifted test set ECE inflates to ≈ 0.16–0.22.", 0),
        ("Platt scaling fit on source data does NOT transfer — the over-confidence wedge remains.", 0),
     ], "ECE: in-distribution → shifted test", "RF reliability (raw vs. Platt-scaled)"),

    ("fig", "Finding 3: abstention helps — if confidence ranks errors", im("p2_risk_coverage.png"),
     "Risk–coverage on NSL-KDD; ring marks the 80%-coverage operating point.", [
        ("Tree ensembles: selective risk 0.20 → 0.11 at 80% coverage (AURC ≈ 0.05).", 0),
        ("Logistic regression's confidence barely ranks its errors (AURC ≈ 0.23) — abstention "
         "buys little.", 0),
        ("Selective prediction is only as good as the underlying confidence signal.", 0),
     ], 0.6),

    ("fig", "Finding 4: why R2L is the blind spot", im("p2_benign_manifold.png"),
     "(a) joint (IF, OCSVM) novelty space; (b) per-family anomaly ridgeline.", [
        ("R2L's distribution sits on top of benign's — inside the benign envelope — for two "
         "independent benign-only detectors.", 0),
        ("It mimics normal traffic, so neither abstention nor a benign-only novelty detector can cleanly "
         "flag it; DoS/Probe/U2R separate.", 0),
     ], 0.66),

    ("fig", "Finding 5: a benign-only novelty stage partially closes it", im("p2_novelty_auroc.png"),
     "Novelty AUROC vs. benign, per family, both detectors.", [
        ("Isolation Forest / one-class SVM separate DoS, Probe, U2R well (AUROC ≈ 0.90–0.99).", 0),
        ("R2L stays hardest (≈ 0.73–0.82) — its support most overlaps benign.", 0),
        ("Abstention and novelty catch different failure modes; combine them.", 0),
     ], 0.6),

    ("bul", "Finding 6: calibration is task-dependent; the blind spot is not", [
        ("CIC-IDS-2017 within-split is easy and well-calibrated (accuracy 0.9998, ECE 0.0001) — "
         "over-confidence is a property of the task, not an intrinsic flaw.", 0),
        ("Cross-day drift: Web detection 0.98 → 0.79; abstention rejects 0.95 of unknown Web — "
         "far more than R2L, because Web does not mimic benign.", 0),
        ("Cross-corpus 2017→2018 (27 shared features): accuracy 0.96 → 0.67, ECE 0.26; "
         "Infiltration (benign-mimicking) is again the blind spot (detected 0.14).", 0),
    ]),

    ("bul", "Which uncertainty signal? Can we guarantee coverage?", [
        ("Paired per-seed ΔAURC: max-softmax is statistically indistinguishable from richer signals; "
         "Mahalanobis is marginally better at error-ranking but worse at unknown-attack detection.", 0),
        ("On tabular flow data the cheap max-softmax is a strong, well-rounded default — the leverage "
         "is in the abstention framework, not the estimator.", 0),
        ("Split conformal: empirical coverage 0.93 in-distribution but 0.61 under shift (target 0.90) — "
         "the guarantee erodes precisely when the deployment distribution moves.", 0),
    ]),

    ("bul", "Discussion: an operational recipe", [
        ("Deploy a model whose confidence is informative (low validation AURC — a tree ensemble, not "
         "the linear model).", 0),
        ("Set the operating coverage from the risk–coverage curve; route the abstained minority to a "
         "secondary control.", 0),
        ("Monitor the abstention rate as a cheap, label-free drift signal.", 0),
        ("Pair abstention with a benign-only novelty stage for the benign-mimicking attacks it cannot "
         "catch.", 0),
    ]),

    ("bul", "Conclusions and future research", [
        ("Selective prediction is a cheap, model-agnostic safety layer for ML intrusion detection, with "
         "clearly characterized limits.", 0),
        ("Strong when unknown attacks are statistically distinguishable from benign traffic; weak when "
         "they mimic it.", 0),
        ("On an easy modern corpus calibration is fine, so the need for it is task-dependent — the "
         "blind spot is not.", 0),
        ("Future: full time-ordered evaluation, the label-corrected CIC-2017, and standardized NetFlow-v2 "
         "multi-network transfer.", 0),
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
