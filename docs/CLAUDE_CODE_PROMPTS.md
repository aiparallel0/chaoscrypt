# Claude Code prompt sequence

Copy these into an agentic coding session one at a time. They assume this repository is the working
directory. Replace bracketed placeholders before sending. The goal is a finished short IEEE-format
paper that breaks a published chaos image cipher.

---

### Prompt 0 — orientation & setup
```
This repo is a cryptanalysis toolkit for permutation–diffusion ("chaos") image ciphers, plus a
secondary zero-knowledge Fiat–Shamir module. Read README.md and docs/RESEARCH_NOTES.md in full.
Then: create a virtualenv, run `pip install -e ".[dev]"`, run `pytest`, and run each script in
experiments/. Confirm everything passes and summarize what each module provides. Do not change the
public API without telling me.
```

### Prompt 1 — confirm the target cipher
```
From docs/RESEARCH_NOTES.md, the primary candidate target is the Optik 2025 Fisher–Yates cipher
(DOI 10.1016/j.ijleo.2025.172304). Obtain its full algorithm description. Answer the single decisive
question: is the diffusion keystream seeded ONLY from the key / chaotic initial conditions (VULNERABLE),
or from a hash or other function of the plaintext (DEFENDED)? Write a short docs/TARGET.md that records
the exact permutation step, the exact diffusion step, how the keystream/initial conditions are seeded,
the number of rounds, and a citation. Then verify no published cryptanalysis of this exact scheme
exists (search the title + authors). If it is DEFENDED or already broken, move to the next candidate in
the shortlist and repeat.
```

### Prompt 2 — reproduce the target
```
Implement the confirmed target cipher exactly as published, as a new module
src/chaoscrypt/targets/<name>.py that reuses chaoscrypt.ciphers where possible (subclass or compose;
override the map, permutation generator, and diffusion step to match the paper). Add a script
experiments/reproduce_<name>.py that encrypts a standard grayscale test image (e.g. 512×512 Lena or
Baboon from USC-SIPI) and reports entropy, NPCR, UACI, and adjacent-pixel correlation. Confirm these
match the paper's reported values to within rounding. Add a test that pins the implementation.
```

### Prompt 3 — mount the attack
```
Adapt chaoscrypt.attacks to the target's exact structure and break it. Specifically: (a) confirm the
cipher is affine/vulnerable with affine_test; (b) recover the equivalent keystream and permutation with
an equivalent-key chosen-plaintext attack (extend equivalent_key_cpa if the step order differs); (c)
decrypt a fresh ciphertext with no key. Add experiments/attack_<name>.py reporting the exact number of
chosen plaintexts, the wall-clock runtime, and a pixel-exact match between the recovered and original
images. If the target uses a weak plaintext association (e.g. sum-of-pixels), implement the codebook /
keystream-reuse variant instead and cite the corresponding paper from RESEARCH_NOTES.md.
```

### Prompt 4 — distinguisher, NPCR caveat, figures
```
Run the chi-square keystream-uniformity distinguisher on the target's keystream. Then demonstrate that
the target's near-ideal NPCR/UACI does NOT imply chosen-plaintext resistance (use distinguishers.npcr/
uaci on the actual target, and show it is still broken by Prompt 3). Generate publication-quality
figures (original / encrypted / recovered images; a keystream histogram vs uniform) and a results table.
Save them under figures/ and write a docs/RESULTS.md summarizing every number.
```

### Prompt 5 — draft the paper
```
Draft a ~6-page IEEE-format paper (use the official template for the target venue) with: abstract;
introduction and the chaos-cipher cryptanalysis context; a concise recap of the target scheme; the
equivalent-key chosen-plaintext attack with its complexity; experimental results (recovery, runtime,
recovered images, chi-square, the NPCR caveat); and a short "how to fix it" section. Cite the canonical
equivalent-key-CPA literature and (if relevant) the sum-of-pixels-break papers listed in
docs/RESEARCH_NOTES.md. Write ALL descriptions and equations in original wording — do not paraphrase the
target paper's text — to keep similarity under the venue threshold. Produce the AI-use declaration as a
separate file. Output the paper as LaTeX under paper/.
```

### Prompt 6 — pre-submission checks
```
Run a self-check before submission: confirm the paper conforms to the IEEE template and page limit;
list every claim in the results and verify each is reproduced by a script in experiments/; re-run the
full test suite; and re-search the target's title to confirm no competing cryptanalysis appeared.
Produce a short SUBMISSION_CHECKLIST.md.
```

---

### Fallback prompt (only if Track A fails) — Fiat–Shamir linter
```
Pivot to the fallback project in src/chaoscrypt/zk. Build an automated linter that statically (or via
the forgery harness in zk/fiat_shamir.py) checks whether a Sigma/Fiat–Shamir implementation binds all
public inputs and commitments and enforces the OR challenge-split. Evaluate it on a small labelled
corpus drawn from the known weak-Fiat–Shamir cases in docs/RESEARCH_NOTES.md (Frozen Heart, Dao et al.
2023). Differentiate the tool explicitly from existing automated tooling, or it will read as derivative.
```
