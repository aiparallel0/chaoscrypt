# External references & provenance

Records external sources used, with licensing notes. **No GPL/AGPL/unlicensed code was copied into
this MIT repository**; the target cipher was reimplemented from its published description, and all
attack/experiment code is original.

## Target (Paper 1)
- S. Jain, A. Samal, A. Sharma, M. Khurana, B. Sharma, "Advanced image security through chaotic
  system-based encryption and Fisher–Yates matrix shuffling," *Optik* 327:172304 (2025),
  DOI 10.1016/j.ijleo.2025.172304. Full text obtained from the author-provided publisher PDF; used
  only to understand the algorithm (no text or code reused). See `docs/TARGET.md`.

## Datasets
- **NSL-KDD** (Tavallaee et al., 2009): public IDS benchmark; fetched from community GitHub mirrors via
  `src/ids_selective/fetch_data.py`. Research use.
- **scikit-image sample images** (`camera`/Cameraman, `moon`, `gravel`, `brick`): ship with
  scikit-image; standard public test images. Cameraman matches one of the target paper's test images.

## Tools / libraries (all permissive: BSD/MIT/LPPL)
- numpy, scipy, pandas, scikit-learn, scikit-image, matplotlib (BSD-3).
- TeX Live + `IEEEtran` document class (LPPL).

## Methodology & citation lists
- Canonical equivalent-key-CPA and chaos-cipher literature: `papers/paper1-chaos-cpa/references.bib`.
- Calibration / selective-prediction / IDS literature: `papers/paper2-ids-selective/references.bib`.
- All bibliography entries were independently verified against primary sources (publisher pages, DBLP,
  JMLR/PMLR/USENIX, author copies).
