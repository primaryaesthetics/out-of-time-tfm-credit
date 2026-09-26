# Literature sweeps

Newest first. One `## <date>` section per sweep. `scripts/check_sweep.py` reads
the top entry and fails when it is older than fourteen days; `--queries` prints
the standing search list.

**A sweep that found nothing still gets an entry.** An empty sweep is evidence
that the gap was open on that date. A missing sweep is evidence of nothing, and
the cost of that is measured: work on the predecessor projects went into
topics that were already published, because the premise was set once and never
rechecked.

Findings go into [prior-art.md](prior-art.md) with a status. This file records
what was searched, on what date, and what changed.

---

## 2026-09-25

Eight days after the last entry, covering submissions and releases from
2026-09-15 on. Items first found on 2026-09-21 are entered here, each checked
again on 2026-09-25. The arXiv API answered every query over https; plain
http now answers 301. The arXiv index ends with submissions of 2026-09-24: a
`cat:cs.LG` query returns 130 papers for that day and 0 for 2026-09-25.
alphaXiv's latest publication date is also 2026-09-24.

**Nothing found closes a leg for TabPFN or TabICL. One public artifact measures
a tabular foundation model out of time on credit data with a calibration
metric, and it makes the 2026-09-14 wording of leg 2 false for a tabular
foundation model in general. It is FinTFM, a single-author model pretrained on
synthetic data and deposited on Zenodo as software on 2026-09-25. It scores its
own model on one year cut of a corporate bankruptcy panel. Neither Goethals
repository has taken the time axis; both had commits up to 2026-09-24, and
their diffs were read, not summaries of them. A Springer journal paper applies
PSI with the 0.10 and 0.25 thresholds inside a "regulatory validation suite",
on a random split.**

- **FinTFM**, Zenodo 10.5281/zenodo.22950210 (software, v0.5.5, created
  2026-09-25; versions 0.5.1 to 0.5.5 all that day), by Organokov;
  `kabartay/fintfm` on GitHub, `fintfm` 0.5.5 on PyPI, weights at
  `kabartay/fintfm-binary`. An in-context classifier for corporate credit risk,
  pretrained only on synthetic tables. The deposit's one file is a zip of the
  repository at `c372862`. It holds no PDF or TeX. `docs/paper/README.md`
  says it is "Not a draft yet". arXiv and Zenodo hold no FinTFM paper. So
  there was nothing to extract, and the reading is of the repository: the
  archive and a clone at `8d68910`. The measurement log
  `docs/results/FINDINGS.md` runs to 8,337 lines. Its scorecard, §26–§40, §55
  and §73 were read; the rest was covered by a term search over every `.md`
  and `.py` file.
  - The split, §26 (2026-09-09): 120,000 company-years drawn at random from
    V4FinBench and split on the observation year, "72,622 train (≤2016),
    47,378 test (≥2017), no year in both". The model's hazard head and a
    per-horizon logistic regression are scored at horizons 0 to 3.
  - The metrics: ROC AUC and ten-bin equal-width ECE per horizon for both
    models, and for the hazard head alone the mean predicted default rate set
    against the observed rate (§28). The harness computes Brier skill, but the
    log reports no out-of-time value of it. §28 corrects §26 with a base-rate
    correction: fourth-horizon ECE falls from 0.3677 to 0.0114, while "Mean AUC
    did not move at all". Best out-of-time reading on three seeds (§38): mean
    AUC 0.8143 and mean ECE 0.0072, against 0.8616 and about 0.0018 for the
    logistic regression. The log's verdict: "'Ahead of the incumbent out of
    time.' False."
  - §55, labelled a hypothesis, reads the TabPFN Nature protocol: "The
    defensible gap is the intersection of four things their protocol never
    tests: low default rates, out-of-time splits, proper scoring rules, and a
    term structure over horizons".
  - What it does not do. No other tabular foundation model is scored, on the
    time split or on any split; TabPFN appears only in results quoted from
    others (V4FinBench's fine-tuned model, arXiv:2605.18147, the TabArena
    leaderboard). There is one cut, so there is no trajectory. The axis is the
    observation year, not an origination date. Calibration is ECE and the mean
    level: no reliability table leaves the out-of-time harness, and there is no
    fitted intercept or slope and no decomposition. `PSI` and `population
    stability` count zero in every `.md` and `.py` file. The data are corporate
    company-years, not retail originations. The log also says §47 "invalidates
    every accuracy number produced before 2026-09-10", and every out-of-time
    run is dated 2026-09-09.
  - **Leg 2 is reworded** in prior-art.md. The 2026-09-14 form, "no calibration
    measurement of any kind, for a TFM on a time-ordered credit split", is
    false for a tabular foundation model in general. What holds: no
    decomposition, reliability curve, or fitted intercept or slope for any
    tabular foundation model on such a split, and no calibration measurement of
    any kind there for TabPFN or TabICL in any version, or for LimiX-2M,
    LimiX-2, Google TabFM or Mitra-v2. A level reading out of time is public,
    so observed over expected out of time is not new in itself. Row added,
    `repo-read`.
- **`andreasgoethals/CreditPFN` and `CreditICL`**, re-checked at HEAD.
  Both were cloned with history, so the diffs were read directly.
  - CreditPFN has 18 commits between 2026-09-21 and 2026-09-24 (HEAD
    `e069447`). `docs/PAPER_ROADMAP.md` was rewritten (`53418cf`) and renamed
    `docs/RESEARCH_BRIEF.md` (`af3b603`), both on 2026-09-23. The brief says
    the evaluation "uses five row-level outer CV folds" and "These are IID
    table benchmarks; they do not simulate future origination cohorts". It also
    says: "Temporal/grouped validation requires valid origination-time and
    loan/borrower keys, excluded from features. It is a future sensitivity
    study, not a property of current IID folds." ECE and Platt/isotonic
    calibration on an inner 20% split were already in the code at `31e2aa3`
    (2026-09-11). New on 2026-09-24 (`6777eb1`) are stored "reliability-bin
    sufficient statistics" and a `plot_reliability` figure.
  - CreditICL has 5 commits between 2026-09-21 and 2026-09-24 (HEAD
    `2034cc2`). At HEAD, `src/eval/runner.py` still raises
    `NotImplementedError` for `split == "temporal"`: "temporal splits need a
    per-dataset date column, which the registry does not carry yet". Its
    `cohort` shift ("context = early vintages, query = late ones") belongs to
    the synthetic pretraining prior and has been there since 2026-08-11. It is
    not an evaluation on real vintages.
  - The trigger named on 2026-09-14 has been read at both HEADs and has not
    fired. `andreasgoethals/TabPFNCredit` has no push after 2026-09-18.
- **doi:10.1007/s44564-026-00017-y**, Mallireddy, Hasan, Mahmood, "A
  multi-metric evaluation framework for machine learning credit scoring
  models aligned with Basel III and IFRS 9 regulatory validation
  requirements", *Discover Informatics* (2026-09-23). WoE logistic regression,
  random forest, XGBoost, LightGBM and an MLP on UCI Taiwan credit card
  default; "A stratified 70/15/15 holdout split was applied". AUC, Gini, KS,
  Hosmer-Lemeshow, Brier and PSI over ten deciles, read against
  "action-triggering thresholds of 0.10 and 0.25", with no critical value and
  no test. The paper states "this does not constitute out-of-time validation"
  and reports no TFM. A classical, in-time mirror of legs 2 and 3, and an
  example of the rule-of-thumb practice the package corrects. Read from the
  Springer HTML page; not indexed.
- **First found on 2026-09-21, checked again.**
  - Hurlin, "Tabular Foundation Models for Credit Risk", Zenodo
    10.5281/zenodo.22849261 (record type other, one PDF, 2026-09-19): one
    version, unchanged. A teaching deck that states the premise in prose
    and, for TabICL on Give Me Some Credit under a random split, publishes a
    decile reliability curve, a calibration slope of 0.97 and the mean PD
    against the observed rate. Row added, verified from the full text on
    2026-09-21.
  - `andreasgoethals/TabPFNCredit`, the code of arXiv:2605.18147, HEAD
    `3dae074` (2026-09-18), cloned: ECE per method over 14 PD datasets on
    the pilot's single stratified random split, and decile calibration
    curves for TabPFN-3 and TabICLv2 under stratified five-fold; no time
    axis. Row added, `repo-read`.
  - The TabPFN-3.5 report is now **arXiv:2609.17895v2** (22 Sep). A
    sentence-level diff against v1 shows 73 changed sentences; the first 60,
    read, are in relational-benchmark comparators and reference renumbering.
    `Brier`, `temperature` and `ECE` still count zero. The BeyondArena
    sentence stands in v2: "Tuned and ensembled MLPs retain the highest
    performance on grouped, temporal, and large datasets, but TabPFN-3.5
    substantially narrows these gaps."
  - TabICLv2, arXiv:2602.11139, is at v2 (16 Sep).
  - `IFoA-ADSWP/tabpfn-reserving`: TabPFN-3.5, zero-shot, reserving 464 real
    insurance loss triangles against Chain Ladder, with the coverage of its
    predictive intervals set beside Mack's and the ODP bootstrap's (README).
    Insurance reserving, not credit.
  - `Arashka-DS/lendtech-credit-risk-engine`: an XGBoost PD engine with
    isotonic calibration and a PSI against the training baseline, on
    synthetic data (README). No TFM, and no test on the PSI.
  - arXiv:2609.20554, "Does Training on Future Data Pay? Look-Ahead Bias in
    Forecasting with Pretrained Models": annual vintages of financial
    time-series foundation models across 14 equity markets (abstract).
    Outside the premise.
  - arXiv:2605.21742, "Correcting Class Imbalance in Prior-Data Fitted
    Networks for Tabular Classification" (20 May 2026), has no row yet; one
    is owed.
- **Packages.**
  - `tabpfn` 9.0.0 (2026-09-15) is still the latest release, and the grid's
    8.5.0 with the TabPFN-3 checkpoint at 0.9 stands. Unreleased on `main`:
    #1270 (2026-09-17), whose changelog reads
    "`SAMPLE_SUBSAMPLING_METHOD="majority_downsample"` now corrects the target
    prior shift it introduces, so predicted probabilities and regression
    distributions are calibrated to the training data rather than to the
    downsampled context". It applies only under that sampler, and the
    classifier applies the temperature before the correction. Also
    unreleased: #1315 (2026-09-24), "Replace task-specific specs with unified
    ModelSpecs (breaking)". No change to the default softmax temperature.
  - `tabicl` 2.2.0 unchanged, no commit on the default branch since
    2026-09-15.
  - `tabpfn-extensions` 0.6.3 (2026-09-21) adds hurdle regression and an image
    extension, with no change to the classifier.
  - `tabpfn-client` 0.6.0 (2026-09-15): release notes not read.
  - `calibre` 0.14.0 (2026-09-20) adds `calibre/decisions.py`.
  - `scores` is at 2.7.0, released 2026-09-05; the row, read on 2.6.0, now
    names both versions.
  - `causilo` 1.0.2 (2026-09-17).
  - Unchanged: `iyipada` 0.1.0, `feature-engine` 1.9.4, `optbinning` 1.0.0,
    `psi-inference` 0.1.0. `PDtoolkit` on CRAN is 1.2.0 of 2023-09-20.
  - `rpsi` is still not on CRAN: the package page, the archive directory and
    crandb all return 404.
  - Twelve more candidate PSI or PRS package names return 404 on PyPI. Zenodo,
    searched for "population stability index", shows no new PSI test. No
    package implementing PRS, the effect-size test or the overlapping
    statistic appeared.

**Also surfaced, not indexed.** `MehKh-Analysis/credit-risk-tabpfn-benchmark`
(created 2026-09-24): TabPFN through the cloud client against LR, RF and
XGBoost on the Kaggle `credit_risk_dataset`, "one stratified 80/20 train/test
split", Brier and a calibration curve, "TabPFN's probabilities are well
calibrated out of the box"; no time axis. arXiv:2609.24386: TabPFN with Brier
and ECE on survey rounds held out in time, childhood stunting, not credit.
arXiv:2609.27654 (FedIncome): out-of-time R² for income on LendingClub, no TFM.
arXiv:2609.26652: context-adaptive thresholding with a FICO credit example.
arXiv:2609.22866: Causilo technical report, a new TFM. SSRN 7484638: Bayesian
PD calibration with cohort dependence, simulation only.
doi:10.1109/satml68715.2026.00028: SaTML version of arXiv:2506.02978. Four SSRN
essays by C. Maxwell on tabular distribution shift, no measurement named.
Dismissed at abstract level, no credit, time-axis or calibration angle on a
TFM: arXiv:2609.27679, 2609.28208, 2609.25541, 2609.23574, 2609.26290,
2609.18130, 2609.29814, 2609.25542, 2609.28576, 2609.25788, 2609.26839,
2609.26955.

**What ran.**

- *alphaXiv*, `scripts/alphaxiv_sweep.py sweep --after 2026-09-15`: 12
  standing queries, 85 distinct papers, none failed; two embedding and eight
  keyword queries ad hoc.
- *arXiv API*, from 2026-09-15: `TabPFN` 9, `TabICL` 1, `LimiX` 1, `tabular
  foundation` 14, `prior-data fitted` 2; credit scoring 2, credit risk 1,
  probability of default 0, Lending Club 0, Freddie Mac 0; population
  stability 0, out-of-time 4, vintage 4; the standing author list 9; q-fin
  RM, ST, GN, CP and PM 37, none on TFMs or PD.
- *Semantic Scholar*: 6 calls, all 429.
- *Crossref*, created 2026-09-15 to 2026-09-25: `TabPFN` 7, `TabICL` 0, and
  the first 15 of six credit and stability queries read.
- *Zenodo*: "tabular foundation" AND credit, 3 hits (FinTFM, Hurlin, this
  project's protocol deposit).
- *Web search*: four queries.
- *GitHub*: unauthenticated REST until the rate limit, then `git clone`.

**Rows already held.** New versions: arXiv:2602.11139 v2 (16 Sep), line
numbers stale; arXiv:2609.17895 v2 (22 Sep), whose identifier the Models
row now carries in place of "no arXiv identifier found". Journal references now listed: arXiv:2601.20533
(*Journal of the Operational Research Society*), arXiv:2605.28554 (ESANN 2026),
arXiv:2506.02978 (SaTML 2026). Every other arXiv row unchanged at the version
cited (41 identifiers checked by `id_list`). MDPI, the ACIS 2025 PDF route and
SSRN abstract pages still return 403.

**Not reached.** Semantic Scholar; SSRN full texts (7484638, 7478518, the
Maxwell essays); the LimiX GitHub releases; the `tabpfn-client` release notes;
GitHub code search; the `PriorLabs/tabpfn_3_5` and `stable-ai` Hugging Face
trees; submissions of 2026-09-25, in neither index yet. FinTFM's log was read
section by section for everything on time and calibration and searched by term
elsewhere, not read end to end.

Net: every published evaluation of TabPFN, TabICL, LimiX, Google TabFM or
Mitra-v2 on credit PD still reports discrimination and, at most, a calibration
scalar or curve on a random split or a single window. Legs 1 and 3 are
unchanged. Leg 2 now reads: no decomposition, reliability curve, or fitted
intercept or slope for any tabular foundation model on a time-ordered credit
split, and no calibration of any kind there for TabPFN, TabICL, LimiX, Google
TabFM or Mitra-v2. FinTFM's calibration figures are on one year cut of a
corporate panel, for a model of that project's own that it places 93rd of 95 on
TabArena. The CreditPFN brief now says in writing that its benchmarks are IID
and do not simulate origination cohorts.

### Addendum 2026-09-26: the TabPFN-3.5 report, read in full

arXiv:2609.17895 v2 (22 Sep) was extracted to `papers/2609.17895v2` and read
end to end; the extractor flagged 12 of its 33 pages, and the lines cited from
flagged pages were read in the PDF. Its only time-ordered evaluation is
BeyondArena's temporal slice, reported as Elo per slice over datasets it does
not name, the two BeyondArena credit tasks among them. Its only probabilistic
reading is CRPS on regression. Brier, ECE, reliability, temperature, softmax,
PSI, drift, out-of-time and vintage do not occur in it, so the softmax
temperature of 1.0 that TabPFN-3.5 ships with rests on the checkpoint metadata
and `tabpfn` 9.0.0, not on the report. The Models row moves from secondary to
verified for the report's text. Legs 1 to 3 are unchanged.

Two survival-analysis papers on tabular foundation models were extracted in
the same pass, arXiv:2609.04901 v2 and arXiv:2606.04564 v2: both evaluate on
SurvSet data under five-fold cross-validation, and credit, loan and
out-of-time do not occur in either. Outside the premise.

## 2026-09-17

Five days after the last entry, over submissions and releases from 2026-09-12.
The arXiv API answered every query without a 429; its index ends with
submissions of 2026-09-15 (a `cat:cs.LG` query from 2026-09-16 returns zero
against 99 from 2026-09-15), and the latest publication date alphaXiv returned
is also 2026-09-15, so papers submitted on 2026-09-16 and 2026-09-17 are not
covered by either and belong to the next entry.

**Nothing found closes a leg. One paper narrows leg 2 on the classical side
and publishes a locked-protocol audit on Lending Club; one SSRN
abstract puts TabPFN, credit scoring and calibration in one sentence and could
not be read; and the TabPFN package changed its default model and, with it,
the default softmax temperature.**

- **arXiv:2609.16102**, Shoeibi, Shabanpour, Karwowski, Yousefi, "A
  Decision-Support Audit Protocol for Supervision Drift in Proxy-Labeled
  Credit-Risk Prediction" (14 Sep 2026; the code repository's README states
  acceptance at HICSS-60). Extracted through `scripts/extract_paper.py`
  (`papers/2609.16102`), five of ten pages flagged; every flagged hit is one
  of the seven lines carrying the notation P(Y | X, C), which neither engine
  recovers, and the two engines agree on every number checked, up to the
  typesetting of minus signs. Lending Club
  in the Ariza-Garzón et al. (2024) granting-model release, one temporal pair
  (2013 vintage trained, 2016 vintage scored) and one cross-segment pair;
  logistic regression, random forest and histogram gradient boosting only;
  AUROC, average precision, Brier, ten-bin equal-frequency ECE, calibration
  intercept and slope, and an intercept-only recalibration to the observed
  target default rate, labelled oracle-style and not deployable. Thresholds
  and rules A to G committed before the official runs, manifests with commit,
  package versions and SHA-256 of inputs, code at
  `mehrdad-shoeibi/supervision-drift-credit` and Zenodo
  10.5281/zenodo.22731264. No TFM (`requirements.txt` holds pandas, numpy,
  scikit-learn, pyarrow and scipy), no trajectory beyond the one pair, no
  PSI: its fourth layer is marginal feature-label association against a
  random-split noise baseline. Its own limitations section says the release
  carries no contractual term, no resolution status and no outcome snapshot
  date, so maturity selection cannot be separated from population change.
  **Leg 2 narrows on the classical side**: calibration intercept and slope
  and an intercept recalibration across a Lending Club vintage pair are
  published for classical models, and the reading that the temporal error is
  mostly an intercept is published for them. **A locked, pre-committed audit
  protocol with run manifests on credit is published**, so no text here may
  describe that design as a first. Row added; the items on the flagged pages 4, 6 and 9 and the threshold
  bounds on page 5 were read in the PDF and match the extraction, so the row
  is `verified`.
- **SSRN 7431058**, Dorador, Hurlin, Pérignon, "AdaLogit: Oracle Credit
  Scoring via Adaptive Logistic Regression" (Crossref record created
  2026-09-14). The abstract compares AdaLogit with TabPFN on synthetic and
  real credit-scoring datasets and claims "better-calibrated probability
  estimates" and "sharp tail probability calibration". The split, the
  calibration measure and the datasets are not named in the abstract. SSRN
  returned 403 to the abstract page and the delivery URL; no arXiv copy by
  title or by author pair. **The one item found that could bear on leg 2 for
  a TFM**, and nothing about it can be cited until it is read.
- **`tabpfn` 9.0.0, released 2026-09-15.** From the GitHub release notes:
  "TabPFN-3.5 is the default model: `TabPFNClassifier()` and
  `TabPFNRegressor()` now load `ModelVersion.V3_5` unless a `model_path` or
  another version is given. The previous default, TabPFN-3, stays available
  through `create_default_for_version(ModelVersion.V3)`." (#1273) and
  "`softmax_temperature` now defaults to `"auto"`, meaning "use the
  checkpoint's value" … Existing checkpoints lack the field and fall back to
  its default of `0.9`" (#1220). The `__metadata__.inference_config` of all
  three checkpoints in `Prior-Labs/tabpfn_3_5` on Hugging Face (created
  2026-09-09), read from the safetensors headers by range request, declares
  `"SOFTMAX_TEMPERATURE": 1.0`, with `N_ESTIMATORS` 8 (4 for the Fast
  checkpoint) and `TRANSFORM_DATES` and `TRANSFORM_TEXT` both true. So the
  library-default TabPFN classifier is now a different model at temperature
  1.0 and with datetime columns expanded into calendar features. The grid
  ran 8.5.0 with the TabPFN-3 checkpoint at 0.9; that pairing is still
  reachable under 9.0.0 and every recorded number names it. Also in 9.0.0:
  the threshold-tuning combinations with `roc_auc` and `log_loss` now raise
  (#1153, #1239); results change for fits using importance-based feature
  subsampling, `gini_feature_importance` directly or through `"auto"` on
  large, wide data (#1141, #1229);
  `majority_downsample` released (#1253); code relicensed to Apache 2.0 with
  the TabPFN-2.5, 2.6 and 3 weights still non-commercial (#1271). The
  TabPFN-3.5 technical report is a web page at
  `priorlabs.ai/technical-reports/tabpfn-3-5` with no arXiv identifier; by a
  summary of the page it benchmarks on TabArena, BeyondArena and STRABLE by Elo and
  names no calibration metric, no temporal split of its own and no credit
  task. The changelog says TabPFN-3.5-Thinking "further improves on grouped
  and temporal data", a BeyondArena statement.
- **LimiX-2**, arXiv:2609.17488 (15 Sep 2026): a 400M-parameter model with a
  joint p(x, y | context) objective, evaluated on TabArena, TALENT and BCCO;
  weights at `stable-ai/LimiX-2` (created 2026-09-15). A pull request adding
  it to TabArena is open (`autogluon/tabarena` #574, #575). The
  `stable-ai/LimiX-2M` checkpoint was re-uploaded on 2026-09-16 with the same
  LFS SHA-256 (`16f385d5…`) as the June commit, so it is unchanged; a
  `stable-ai/LimiX-1_2M` repository was created beside it on 2026-09-15.
  The LimiX GitHub releases page shows no release in August or September.

**Also surfaced, abstract-only, drafted or dismissed in the candidates
file.** arXiv:2609.13100, Chatterjee and Barber, rankECE, which compares points
with neighbouring predicted probabilities and is shown, with guarantees, to
be a better proxy for ECE than binned estimates: a calibration-measurement paper, no TFM, no credit, no time axis.
arXiv:2609.03106, Richman, scaling laws on a motor-insurance portfolio by
Poisson deviance across GLMs, TabM, MLPs and tabular transformers; no TFM is
named, no calibration, no credit. arXiv:2609.12136 (10 Sep 2026, before the
window and not in the last entry), prequential adaptation of frozen TFMs
under temporal drift, identification walls, eight industrial streams.
arXiv:2609.13031 (11 Sep 2026), FP8 attention quantization for TabPFN-v3 and
TabICLv2, no accuracy loss on TabArena and BeyondArena. arXiv:2605.22892,
Deprez, Verbeke and Verdonck, TabPFN for motor insurance pricing against GLM
and XGBoost on two public MTPL datasets, not consistently ahead and sensitive
to the context size; two authors from the standing author list, carried as
owed since 2026-09-04 and not previously given a row. arXiv:2609.14576, a review of foundation
models for insurance risk modelling. arXiv:2609.15744, a deep-learning credit
early-warning system with no TFM. Crossref, created from 2026-09-12: an H2O
AutoML against tuned classical models on Lending Club
(doi:10.3233/atde260860), AUC and F1; a cross-market transferability score
for alternative credit scoring on synthetic bureau data
(doi:10.1057/s41599-026-09062-2); a *Scientific Reports* paper on
time-series generative augmentation for credit risk
(doi:10.1038/s41598-026-71606-y) with no abstract in Crossref.

**What ran.**

- *alphaXiv*, `scripts/alphaxiv_sweep.py sweep --after 2026-09-12`: 12
  standing queries, 78 distinct papers, 0 failed. Ad hoc, with the same
  bound: six embedding queries (credit scoring with out-of-time and
  calibration; PD drift on Lending Club and Freddie Mac; prior-data fitted
  in-context benchmarks; population stability monitoring; Brier
  decomposition; intercept recalibration under prevalence change) and ten
  keyword queries (`tabular foundation model`, `TabPFN`, `TabICL`, `LimiX`,
  `credit scoring`, `probability of default`, `population stability`,
  `out-of-time`, `vintage`, `Brier`), and ten paper lookups; none failed.
  The keyword channel matched `TabPFN credit` on credit assignment in
  reinforcement learning and `population stability index Yurdakul` on
  mathematics and physics; nothing relevant beyond the items above.
- *arXiv API*, `submittedDate` from 2026-09-11: TFM terms in abstract
  (TabPFN, TabICL, LimiX, tabular foundation, prior-data fitted, TabDPT,
  tabular in-context), 3; credit terms (credit scoring, credit risk,
  probability of default, loan default, Lending Club, Freddie Mac), 2;
  population stability, out-of-time or vintage, 1, not relevant; calibration
  with tabular, 0. The TFM block from 2026-09-01, 19, which is how
  arXiv:2609.12136 and arXiv:2609.13031 were found. Authors (Lessmann,
  Baesens, Verbeke, Bravo, Mues, Verdonck, Goethals, Óskarsdóttir,
  Holzmüller, Hollmann, Rahman, Shoeibi), 3: arXiv:2609.16102,
  arXiv:2609.13031 and an unrelated X-ray tomography paper by a different
  Goethals. q-fin.RM, ST, GN and CP, 12, none on TFMs or PD.
- *Semantic Scholar*: 12 calls over 9 query strings, 12 answered 429,
  including three retries 30 seconds apart. Nothing from this source.
- *Crossref*, created 2026-09-12 to 2026-09-17: `TabPFN` 2 (crop-model
  residuals, rockburst), `TabICL` 0, and the tabular foundation model,
  population stability index and out-of-time credit scoring strings, which
  return relevance-ranked noise; the first 15 of each were read, which is
  how SSRN 7431058 and the three journal items above were found.
- *Web search*: TabPFN credit risk; TFM out-of-time vintage credit
  calibration; PSI critical values; LimiX-2; TabPFN-3.5; SSRN TFM credit
  out-of-time; Edinburgh CRC working papers; Population Resemblance
  Statistic in Python; TabArena with TabPFN-3.5 and LimiX-2; AdaLogit. The
  CRC working-papers page lists three 2026 papers (Djeundje, Crook and
  Andreeva on environmental risk in mortgage default; Tran and Nguyen on the
  Gini a scorecard needs; Breeden on the mathematics of LLMs), none on TFMs.
  The PRS search returns genetics packages only.
- *Packages*, PyPI JSON: `tabpfn` 9.0.0 (2026-09-15), `tabicl` 2.2.0
  unchanged since 2026-09-02 (its release notes were read on 2026-09-12),
  `iyipada` 0.1.0, `feature-engine` 1.9.4, `optbinning` 1.0.0,
  `psi-inference` 0.1.0, `tabpfn-extensions` 0.6.2 (2026-09-03). There is no
  LimiX package on PyPI (`limix` is an unrelated 2019 genomics package).
  `PDtoolkit` on CRAN, 1.2.0 of 2023-09-20, unchanged.
- *GitHub*, REST search over repository names, descriptions and READMEs,
  unauthenticated: created from 2026-09-12, `credit`, `loan` or `default`
  with `tabpfn`, `credit` with `tabicl`, `limix` or "tabular foundation", 0
  each; `tabpfn` alone, 8, one on credit
  (`habbibaZAKI/tabpfn-financial-classification`: TabPFN against XGBoost and
  LightGBM on German Credit, 800 training rows, accuracy, ROC-AUC and F1 in
  the README, no time axis, no calibration figure named); `tabicl` alone, 0;
  pushed from 2026-09-12, `credit tabpfn` 1, `andreasgoethals/CreditPFN`,
  whose commits since 2026-09-11 are "docs update" and, on 2026-09-15, "bug
  fix."; `CreditICL` has one commit since, "docs update" on 2026-09-11,
  both read from a summary of the commits page, so the diff was not
  read and the trigger named on 2026-09-14 (a time-ordered fold generator or
  a date column surviving `sanitize.py`) is not excluded; population
  stability pushed from 2026-09-12, 3, among them `lab1702/duckPSI`, PSI as
  DuckDB SQL macros with the 0.10 and 0.25 labels and no test. `credit
  scoring` created from 2026-09-12, 172, the first 40 read by description,
  no TFM. The core REST API hit its unauthenticated rate limit during the
  sweep, so the LimiX releases were read from a summary of the HTML page.
- *Hugging Face API*: Prior Labs and LimiX model repositories by last
  modification, file trees, commits and the safetensors headers above.

**Rows already held.** New versions since the rows were written: none among
arXiv:2603.06733 (v1), 2606.01427 (v1), 2603.08206 (v5, June), 2607.11007
(v3, July), 2608.02845 (v1), 2608.24582 (v1), 2511.08667 (v2, February),
2606.04485 (v2, June), 2605.18147 (v2), 2605.18635 (v1), 2606.30410 (v1),
2605.04363 (v2, May), 2512.00888 (v2). Every `abstract-only` arXiv row has
its full text on arXiv and none was extracted here. The Murphy-diagram
reference is arXiv:1503.08195, full text available. MDPI still returns 403
on *Sustainability* 18(12):6305; the ACIS 2025 landing page loads and its
PDF route returns 403. **`rpsi` is not on CRAN**: the CRAN package page and
its archive directory return 404, `crandb.r-pkg.org/rpsi` returns 404 and
the `cran/rpsi` mirror does not exist, while each route returns 200 for
`PDtoolkit`. The GitHub repository `edpeyton/rpsi` (DESCRIPTION version
1.0.0) carries CRAN badges. The implementations row and the two READMEs that placed `rpsi` on CRAN are
corrected.

**Not reached.** SSRN 7431058 (403 on both routes); Semantic Scholar (429
throughout); the Springer page of the Andreeva, Crook and Mues editorial
(redirect to a login; the Crossref record matches the item noted on
2026-09-04); the LimiX GitHub releases through the API (403, rate limit);
the diffs of the CreditPFN and CreditICL commits. GitHub code search needs
authentication and did not run. Papers submitted on 2026-09-16 and
2026-09-17 are not yet in either index.

Net: every published evaluation of a TFM on credit PD still reports
discrimination and, at most, a pooled calibration scalar on a random split
or a single window. Leg 1 and leg 3 are unchanged; leg 2 holds for TFMs with
SSRN 7431058 unread, and the classical-model side of it now includes
arXiv:2609.16102.

**Addendum, same day: SSRN 7431058 read.** The full text, obtained by hand
from SSRN, is `papers/ssrn-7431058`; the protocol, the datasets, the
calibration metrics and Tables 5 and 6 were read in the PDF. Every result is
a stratified 10-fold cross-validation repeated under four seeds on pooled
datasets, Lending Club among them as a 9,420-row sample without a date axis.
Calibration is the Brier score, the Hosmer-Lemeshow statistic and the
absolute Spiegelhalter z; averaged over eight datasets TabPFN-2.6 reads 26.6
and 2.88 on the last two against 14.7 and 1.04 for the adaptive logistic
model. So a TabPFN calibration result on credit is published, on random
folds and by scalar goodness-of-fit. Leg 2 narrows by that much: a sentence
that no study reports TFM calibration on credit is no longer true. The
out-of-time reading, the intercept and slope, the vintage trajectory and
population stability are still in no paper found, and leg 1 and leg 3 are
unchanged.

## 2026-09-12

Seven days after the package sweep and eight after the last full one, run
after the ninth cold audit named three things to check: the TabICL release of
2026-09-02, a paper it had found unindexed, and the two model rows still at
`abstract-only`. The arXiv API answered 429 to the standing query twice, so
the arXiv side ran through web search over the standing terms and the
abstracts and full texts were fetched by identifier.

**Nothing found kills the premise or the second deliverable. Four things are
recorded.**

- **Package versions against the grid's.** PyPI release histories, read from
  the JSON API: `tabicl` 2.0.1 (2026-02-14), 2.0.2, 2.0.3, 2.1.0
  (2026-04-21), 2.1.1 (2026-04-29), 2.2.0 (2026-09-02); `tabpfn` 8.0.8
  (2026-06-10) to 8.4.0 (2026-08-19) and 8.5.0 (2026-08-27). The grid ran
  `tabicl` 2.1.1 and `tabpfn` 8.5.0. The v2.2.0 release notes on GitHub add
  the prior and pre-training code, refactor device handling, use a gradient
  scaler for float32 with FlashAttention-3, drop the gluonts dependency and
  fix bugs in pickling, NaN columns and constant features; they name no
  change to the checkpoint, the softmax temperature, the default inference
  parameters or the classifier's probabilities. The TabPFN notes for 8.4.0
  add temperature calibration to the regressor's tuning config and put 1.0
  into its temperature grid, and 8.5.0 changes caching, downloads and
  memory. The grid's versions stand; a re-score under 2.2.0 is a check to
  run if a reviewer asks, not a reason to rerun.
- **`PDtoolkit` on CRAN, source read** (`cran/PDtoolkit`, `R/15_PSI.R`):
  `psi()` returns the Yurdakul chi-square critical value,
  `qchisq(p = ci, df = b - 1) * (1/n + 1/m)`, and a normal approximation of
  it, `(1/n + 1/m) * (b - 1) + qnorm(p = ci) * (1/n + 1/m) * sqrt(2 * (b -
  1))`, citing Yurdakul's 2018 dissertation; nothing beyond them. The
  landscape row moves from `listing-only` to verified, and the package
  README's sentence that `rpsi` is the R implementation of the critical
  value now names both. The statement that PRS, the effect-size test and
  the overlapping statistic were in no package on either side is
  unchanged.
- **Two papers read in full and added.** arXiv:2605.10896, V4FinBench:
  corporate bankruptcy over 2006 to 2021 at 0.19% to 0.36% positives, six
  horizons, fine-tuned TabPFN against boosting and a fine-tuned Llama, on
  five-fold stratified cross-validation grouped by company within country
  (§4, l. 225–228), a threshold calibrated on the validation fold by F1 (l.
  288–290), no calibration metric; a random-fold protocol with a threshold
  step, on a corporate book, which is the published protocol EXP-004 sets
  beside this one. arXiv:2606.18677, bounded context management for TFMs
  on data streams: TabICLv2 as the backbone (l. 181–182), seven streams
  under distribution shift, accuracy as the metric, no credit stream, no
  calibration; the second published temporal use of a current TFM after
  Drift-Resilient TabPFN, again with no calibration and no stability
  reading. Extraction of the second was poor, 15 of 17 pages flagged, and
  the lines quoted were read in the raw text.
- **Checked and not indexed.** arXiv:2506.02978, test-time attacks on
  tabular foundation models and in-context defences: adversarial
  robustness, no credit data, no temporal axis, no calibration. Out of
  scope for every table here.

The two model rows, read in full the same day: the TabPFN-3 report names
threshold tuning and temperature scaling as post-processing (§2.3, l.
413–414) and benchmarks on ROC AUC and log-loss, with a temporal prior in
pretraining and temporal splits on its regression benchmark only; the
TabICLv2 paper's temperature is the attention temperature, and the output
softmax temperature the package ships at 0.9 does not occur in it. Both rows
move to `verified`; the sentence in the TabPFN-3 row about the package's
temperature handling rests on the package notes and says so. TabArena's board
(v0.1.4, by web search) has TabPFN-3, TabPFN-2.6, RealTabPFN-2.5 and
TabICLv2 as its top four single models; no LimiX-2M entry was found. The
Edinburgh CRC and the author pages returned nothing newer than the rows
already held. GitHub was not searched for new credit-and-TabPFN repositories.

### Addendum: the scoop check of the same afternoon, read and re-checked 2026-09-14

An addendum rather than a new entry, on the precedent of 2026-09-04: this
file dates an entry by the day its searches ran, and these ran on
2026-09-12. The full-text readings, the page checks against the flagged
extractions and the re-checks of every GitHub fact against the live page were
done on 2026-09-14 and are dated so in each row of
[prior-art.md](prior-art.md). The question was narrower than the standing
list: who could publish the out-of-time, decomposed-calibration and PSI study
of TFMs on credit PD first, and whether any of the three legs has closed.

**Nothing closes a leg. Two legs are restated more narrowly, the temperature
finding gains a neighbour, and the package landscape gains a rival test.**

**What ran.** The arXiv API, scripted over `ti:` and `abs:` fields with a
submission window from 2024-01-01, no 429 that afternoon: a TFM block
(TabPFN, TabICL, tabular foundation model, LimiX, TabDPT, prior-data fitted,
TabFM, OrionMSP, TabTune, in-context learning with tabular) ANDed with credit
terms, 62 hits; with temporal and drift terms, 72; with calibration terms,
84; with finance terms, 56; the block alone, 480; Mitra with tabular, 5;
population stability index with credit or critical-value terms and no TFM
block, 8; credit scoring with out-of-time, vintage, calibration or foundation
model and no TFM block, 47; union 529 records, of which 44 carry credit or
finance vocabulary in title or abstract and were triaged one by one.
OpenAlex and Crossref over 23 search strings from 2025-01-01. Semantic
Scholar answered 8 of 23 strings and returned 429 on the rest. The GitHub
REST API, unauthenticated, over repository names and descriptions, with no
code search. Web search over journals, SSRN, conference programmes and
industry pages, the query list kept with the drafts. Crossref DOI lookups
for the non-arXiv items. On 2026-09-14 the arXiv API answered 429 to the
identifier check, so every identifier, title, author list and version below
was checked against the paper's own abstract page instead.

**Read in full through `scripts/extract_paper.py`**, each cited line mapped
to its PDF page and every line on a flagged page read in the PDF itself:
arXiv:2604.02351, 2601.20533, 2605.18696, 2605.03816, 2605.30188,
2605.04363, 2502.16840, 2606.11473, 2609.07956, 2607.26000, 2501.10677,
2511.16375, 2509.09855, 2609.04540. Rows added or changed:

- **Leg 1 on the classical side.** arXiv:2604.02351, Rahman and Tabassum:
  Lending Club, 1,347,681 loans, training cutoff 2009-12-31, nine annual
  evaluation windows 2010 to 2018, ROC AUC, ECE and Brier per window, on
  XGBoost only. A vintage trajectory with calibration scalars on Lending
  Club is published, and the novelty of leg 1 is the TFM on it, not the
  trajectory. Its SSRN sibling 6336198, deposited 2026-04-21, adds PSI in its
  abstract and does not name its models; SSRN returned 403 on every route,
  so whether a TFM is in that model set is unknown. arXiv:2601.20533, Peng
  and Lessmann: Freddie Mac with simulated drift, isotonic calibration, AUC,
  Brier and F1 under cross-validation grouped by loan, no TFM, no PSI; the
  paper itself says an out-of-time design would add vintage effects it
  wants to avoid.
- **Leg 2 restated.** arXiv:2605.18696 reports the reliability component of
  the Brier decomposition for six TFMs, pooled over the TabArena
  suite, which holds credit-g, credit_card_clients_default, GiveMeSomeCredit
  and heloc and reports none of them apart. The row's earlier gloss "no
  credit data" was wrong and is corrected. `alexquant1993/tfm_pd_comparison`
  commits two files named as reliability curves for TabPFN v2, TabICL and
  TabDPT on German Credit under ten-fold cross-validation;
  `kami3kardes/TabPFNv2-Sampling` holds ECE scalars on credit-g and no
  curve on credit; the `CreditPFN` tree commits no calibration figure. Leg 2
  now reads: no decomposition, and no calibration measurement of any kind,
  for a TFM on a time-ordered credit split. arXiv:2605.03816 adds the
  published reading that TabPFN and TabICL are well calibrated on random
  folds, by Spiegelhalter Z; arXiv:2605.30188, CalArena, a post-hoc
  calibration harness on TabArena predictions from eight TFMs, random
  splits, no credit term.
- **Leg 3 unchanged.** No paper or repository found measures population
  stability on a TFM; `PSI` counts zero in every credit-and-TFM README.
- **The temperature finding has a neighbour.**
  `ulasyurtsever/tabpfn-calibration-shift`, created 2026-06-21 and untouched
  since, is the code of a manuscript whose README states, for TabPFN and
  TabICL on census shifts, that temperature scaling cannot repair the loss of
  calibration and that an intercept-only correction recovers about 94% of
  the affine gain. No credit data, one temporal pair, no venue copy found by
  title. arXiv:2605.04363, DistPFN, names the context's class balance as the
  mechanism behind TabPFN's majority-class bias under label shift, the rival
  explanation for a default-rate under-prediction. In the TabPFN repository,
  #1220 (merged 2026-09-01, after v8.5.0) moves the softmax temperature into
  the checkpoint's inference config with 0.9 as the field default for every
  checkpoint that exists today; #1253 (merged 2026-09-09) adds
  `majority_downsample`; #1261, a mean-matching `prediction_scaling`, was
  opened and closed unmerged on 2026-09-11. All three states re-read from the
  pull-request pages on 2026-09-14.
- **The context slot.** Recency-windowed TFM contexts under drift are
  published on generic streams, by accuracy: arXiv:2502.16840 (KDD 2026),
  arXiv:2606.18677 and arXiv:2609.07956, the first and third from the Porto
  group. Distribution-matched contexts against the scored batch under
  simulated covariate drift: arXiv:2606.11473, CRUMB. None reads calibration
  and none touches credit; no paper found selects or weights a context by
  origination time on credit PD. Any public sentence here about rolling
  contexts cites the first three; CRUMB is the label-free comparator.
- **The package.** arXiv:2509.09855, Sudjianto and Burakov: a delta-method
  standard error for IV carried to PSI, a Z test under a normal null, with
  no citation of Yurdakul and no chi-square. A published PSI test that
  `psi-inference` neither implements nor cites; the two nulls are not
  compared in the paper and not compared here.
- **Also added.** arXiv:2511.16375, the workshop precursor of V4FinBench,
  stratified random test subsets and F1-tuned thresholds; *Sustainability*
  18(12):6305, TabPFN on 210 Chinese SMEs, abstract-only behind MDPI's 403;
  Leyh's ACIS 2025 AutoML benchmark, abstract-only, the AIS landing page
  serving the abstract this time; Block's BlockTabBench of 25 Aug 2026, the
  first industrial out-of-time TFM benchmark found, fraud and PR-AUC only,
  secondary; the Mitra-v2 report, whose financial-services appendix links to
  arXiv:2605.18147 for its credit result. arXiv:2607.26000 and
  arXiv:2501.10677 move from `abstract-only` to `verified` with the absences
  now located in the text.

**The closest group.** `andreasgoethals/CreditPFN` and `CreditICL`, KU
Leuven, both pushed 2026-09-11. Their `docs/PAPER_ROADMAP.md` lists temporal
splits as must-have item 3 with a note that only 5 of 25 datasets carry a
date and no PD test set does, names the full Lending Club `issue_d` as the
costly route, and lists a recalibration ablation as should-have item 11;
`CreditICL/docs/EXPERIMENTAL_DESIGN.md` holds the temporal-split protocol as
its first open decision. The time axis is on their plan and not in their
code; decomposition and stability are on neither. The trigger to watch is a
time-ordered fold generator or a date column surviving `sanitize.py`.

**Credit-and-TFM papers by first submission since 2025-01, as a list rather
than a rate:** arXiv:2501.10677 (Jan 2025), arXiv:2511.16375 (Nov 2025),
arXiv:2605.10896, arXiv:2605.18147 and arXiv:2605.18635 (May 2026),
doi:10.3390/su18126305 (Jun 2026). Six in twenty months, none with more than
one test window, none with a calibration decomposition or a PSI. The arXiv
filter sees only papers that name a TFM in title or abstract, so a credit
paper using TabPFN as one baseline in the body is invisible to it.

**CSCC XIX programme, read at last.** The agenda is served as JSON behind the
JavaScript page (`airdrive.eventsair.com`, 842 KB), fetched 2026-09-14. 184
session and talk titles. Lessmann presented "Foundation Models for Credit
Risk Prediction: Game Changer or False Hope?" on 27 August 2025, the only
title naming foundation models. Adjacent titles: Forrest, "Drifts, Shifts and
Instabilities to Quantify Scorecard Model Risk"; Ünal, "Validation of machine
learning and deep learning models in credit scoring"; Florez-Lopez, "When
sampling selection bias meets population drift"; Rakopo, a forward-looking
PD calibration approach for IFRS 9; Diaz, LLMs on Chilean consumer loans.
No title names TabPFN, TabICL, out-of-time, vintage or population stability.
The abstracts and full papers listed as documents behind the agenda were not
fetched.

**Queries that returned nothing, recorded as such.** PyPI: `iyipada` still
0.1.0, `feature-engine` 1.9.4, no new neighbour of `psi-inference`.
`optbinning` moved to 1.0.0 on 2026-09-12; its `scorecard/monitoring.py` at
tag v1.0.0 still bins the PSI at 0.10 and 0.25 and tests target rates by a
chi-square contingency test, so the landscape row stands with the version
updated. GitHub repository search for population stability index in Python
pushed after 2026-08-20: one, `iHarshMix/Basel_Scorecard_Lakehouse`, a
scorecard project whose README computes the bare PSI against the 0.10 and
0.25 thresholds. Web search for the Population Resemblance Statistic in
Python: genetics packages only. GitHub repository
search, credit with TabPFN, TabICL, TabDPT, LimiX or Mitra, pushed after
2026-08-01 or created after 2025-06-01: the three Goethals repositories,
`alexquant1993/tfm_pd_comparison` and one survey README; nineteen
out-of-time credit repositories created since May 2026, seven READMEs
scanned, no TFM in any. Hugging Face models and spaces: nothing credit and
TFM. Crossref journal titles with TabPFN, TabICL or tabular foundation model
in a finance title, from 2025-01: none in EJOR, JBF, DSS, KBS, IJF, FRL,
ASOC, JORS or ESWA; the two finance-titled hits are *Sustainability*
18(12):6305 and a *Frontiers in Public Health* paper on health-insurance
claims. The Baesens, Goethals, Lessmann, Oskarsdóttir and Sankarapu author
feeds on arXiv, as fetched on 2026-09-12: nothing on TFMs and credit beyond
the rows held; Lessmann's newest is findr, Goethals's an LLM paper of June
2026. Mission Lane's feed: no post after 27 Feb 2026. Versions of
the held rows on their abstract pages: arXiv:2605.18635 still v1,
arXiv:2605.18147 still v2, no held row moved.

**Not reached.** SSRN 6336198 and 5961475, 403 on every route, including the
delivery URL; MDPI, 403 on *Sustainability* 18(12):6305, *MAKE* 8(8):244 and
the *Risks* 14(4):95 PDF; a ScienceDirect search page, 403, so the Elsevier
journals are covered by Crossref titles only, and a paper that uses a TFM as
one baseline without naming it in the title is invisible to that route;
OpenReview forum and API pages for two ICML 2026 workshop titles; a Bravo
LinkedIn post; the Padilla blog post on TabPFN-2.5 for credit risk, whose
URL returned 404 on 2026-09-14 and which is therefore not carried as a row.
GitHub code search needs authentication and did not run, so a repository
that scores TabPFN on Lending Club with PSI and describes itself otherwise is
not excluded. The Semantic Scholar record for the SSRN DOI does not exist.

Net of the addendum: every published evaluation of a TFM on credit PD still
reports discrimination and, at most, a pooled calibration scalar on a random
split or a single window; the three-leg claim stands in the narrower wording
now in [prior-art.md](prior-art.md).

---

## 2026-09-05

A narrow sweep, run while the population-stability package was built, over
the names and sources it depends on.

- **PyPI names.** `psi-inference`, `stabilitytest` and `popstab` all return
  404 from the PyPI JSON API (`/pypi/<name>/json`); `numpy` returns 200 on
  the same route, so the negative is a negative. The package takes the first.
- **`rpsi` read from source** (`edpeyton/rpsi`, `R/main.R` and
  `R/conf_int.R`): the Yurdakul critical value, printed as
  `qchisq(crit_val, B - 1) * (1/N + 1/M)`, with a `random_base` switch that
  drops the `1/N` term, and a wrapper around `DescTools::MultinomCI`. No PRS,
  no effect-size test, no overlapping statistic. The README's sentence that
  the correct statistics are implemented in R is narrowed to the one that is.
- **The three sources read in full** through `scripts/extract_paper.py` and
  pinned by tests to their printed worked examples: Yurdakul and Naranjo
  (2020), *Journal of Risk Model Validation* 14(4), from the WMU-hosted PDF
  (the ScholarWorks route returns 403); arXiv:2307.11878v4 (PRS);
  arXiv:2303.01227v1 (effect size, overlapping). PRS Table 2 and Yurdakul
  Tables 1–3 reproduce to the printed digits.
- **Released the same day** as `primaryaesthetics/psi-inference` v0.1.0,
  Zenodo concept DOI 10.5281/zenodo.22342343. The 2026-09-04 negative on
  PyPI is now the state before this package rather than a standing gap.

Nothing else was searched. The 2026-09-04 entry stands for the premise.

---

## 2026-09-04

Eight days after the first sweep, run over three disjoint query sets in
parallel: arXiv and papers; PyPI, GitHub and releases; authors, venues and
regulators. Every finding below that carries a number was checked against the
package source or the paper's own text before it was written here.

**Two things changed, one narrows the premise and one narrows the second
deliverable. Neither kills either.**

### The premise: the general form is no longer defensible, the credit form is

**arXiv:2606.30410 — Purucker, Tschalzev, Erickson, Blayer, Holzmüller, Arazi,
Pfefferle, Tajjar, Varoquaux, Hutter, "Beyond IID: How General Are Tabular
Foundation Models, Really?" (BeyondArena, 29 Jun 2026).** Eleven models over 142
datasets, partitioned into IID, **temporal** and grouped task types. The
temporal protocol is a rolling origin, in the paper's own words (l. 366–369):
"we manually create application-specific temporal splits … We roll back the
time horizon to create multiple split time points for multiple train-test
splits. At each time point, we use all data before for training and all data
after within the time horizon for testing."

Two of its temporal datasets are credit (Table B.1, l. 2769–2770):
`lending_club_1m`, 45,730 rows and 9 columns, and
`home_credit_default_stability_1m`. TabICLv2, TabPFN-2.6 and TabDPT are among
the models.

So a multi-window, forward-in-time evaluation of current-generation TFMs on
Lending Club exists and is published, and the sentence "published evaluations
of tabular foundation models do not order time" is now too strong in its
general form. What the paper measures on those datasets is one number: "We use
ROC AUC for binary classification, log-loss for multiclass classification, and
RMSE for regression" (l. 409). Both credit datasets are binary, so ROC AUC is
all they produce, and the results are aggregated across splits into Elo rather
than reported as a trajectory. Counted in the full text: `population stability`
0, `vintage` 0, `out-of-time` 0, `origination` 0, `reliability diagram` 0,
`Brier` 0. Calibration enters once, as a post-hoc ablation on *multiclass*
log-loss (F.7), and never touches a binary task.

The three-legged claim therefore stands and is sharper than before: **every
published evaluation of TFMs on credit data reports discrimination only.**
arXiv:2605.18147 has calibration scalars on random folds; arXiv:2605.18635 has
one temporal window and no calibration by design; BeyondArena has many temporal
windows and ROC AUC alone. Not one reports a reliability curve, a score
decomposition, or a population-stability statistic on a credit PD task.

**arXiv:2411.10634 — Helli, Schnurr, Hollmann, Müller, Hutter,
"Drift-Resilient TabPFN", NeurIPS 2024.** A two-year-old paper by the TabPFN
authors on TFMs under temporal distribution shift, with a calibration claim in
its abstract. Not found by the first sweep. It does not close the gap — no
credit PD data, no vintage trajectory, no decomposition, no stability test —
but no public text from this project may say that TFMs have not been evaluated
under temporal shift, and it is a candidate baseline rather than only a
citation. Abstract-only; full text is the next primary-source job.

**arXiv:2607.26000 — "Empirical Evaluation of Out-Of-Distribution Performance
of Tabular Foundation Models" (28 Jul 2026).** Nine TFMs including TabPFN-3 and
TabICLv2 on three TableShift datasets, one of them HELOC. The shifts are
structural — label, socioeconomic, geographic — not temporal. Abstract-only.

Six further papers older than 2026-08-27 were missed by the first sweep and are
recorded in [prior-art.md](prior-art.md): arXiv:2605.18696 (a calibration paper
by the group that wrote the temporal-split credit paper), arXiv:2603.08206,
arXiv:2607.11007, arXiv:2608.24582, arXiv:2501.10677, arXiv:2603.06733. The
clustering is in the calibration and drift queries, which is the second time
those two standing queries have under-returned. The fix named in the first
sweep — run each query from a recorded, scripted search — is now overdue; the
arXiv API worked reliably here where general web search did not surface any of
the three most relevant hits.

### The second deliverable: the Yurdakul half is gone, the rest is not

**`iyipada` 0.1.0, uploaded to PyPI 2026-09-01.** Read from source:
`iyipada/null.py` returns `scipy.stats.chi2(df=bins - 1, scale=1/n + 1/m)`,
which is the Yurdakul asymptotic null exactly, and exposes both a critical
value and a p-value for an observed PSI. Three days old, one release, one
author.

**`feature-engine` 1.9.4 has had the critical value since 2026-02-27**, at
`selection/drop_psi_features.py` line 770, citing Yurdakul. The first sweep
recorded the opposite; that sentence is corrected in place above.

**What is still absent from Python**, confirmed by grep over both packages and
eight others: the Population Resemblance Statistic, the effect-size test and
the overlapping statistic. `iyipada` returns nothing for `resemblance`,
`overlapping`, `noncentral`, `effect size`, `Potgieter` or `du Pisanie`.
`mwburke/population-stability-index` is still the bare formula, unchanged since
2023. `optbinning` 0.21.0 hard-codes the 0.10/0.25 traffic lights.

So the package's contribution is now the PRS and the two tests from
arXiv:2303.01227 and arXiv:2307.11878, not "Yurdakul–Naranjo critical values in
Python", which has two independent implementations. Whether that is still a
package or becomes a module of this study is a scoping decision this entry does
not make.

**`calibre` 0.13.0 closes the CORP decomposition gap, and closed it on
2026-08-26 — one day before the first sweep.** Read from source:
`calibre/evaluation.py` exports `corp_reliability`, `score_decomposition`
returning `mean_score`, `miscalibration`, `discrimination` and `uncertainty`,
plus consistency and confidence bands and the MCB–DSC plane, pinned against the
authors' R `reliabilitydiag` in its own tests. The first sweep's "PyPI page did
not load" was a false negative rather than a stale reading. The planned local
decomposition function is redundant.

**`scores` has not added the decomposition.** Still 2.6.0, 2026-07-17; nineteen
commits since, none touching CORP, MCB or DSC.

### Releases, and a version pin that is now load-bearing

- **TabICL 2.2.0, released 2026-09-02** — new since the first sweep. The Metal
  memory measurement recorded for this project was taken at 2.2.0 and the T4
  record at 2.1.1, so the two are not the same software.
- **TabPFN v8.5.0, 2026-08-27**, is current. v8.4.0 added
  `tuning_config={"calibrate_temperature": True}` and changed the classifier's
  temperature grid. **Calibration behaviour therefore differs between TabPFN
  versions**, and every calibration number this study reports has to name the
  version that produced it. Licence unchanged, Prior Labs v1.2.
- **TabArena** moved to `autogluon/tabarena` and changed its Elo methodology in
  the window: ranks-based Elo by default, Bradley–Terry by L-BFGS, finite Elo
  for winless methods. Any Elo figure quoted from before 2026-08-31 is on a
  different method.

### Regulation

**SR 26-2, "Revised Guidance on Model Risk Management", 17 April 2026**,
Federal Reserve, OCC and FDIC jointly, **supersedes SR 11-7 and SR 21-8.** Its
scope footnote excludes generative and agentic AI and states that the guidance
applies to "non-generative, non-agentic AI models", which is what a TabPFN-class
model is — so these models sit inside the guidance rather than in the carve-out
some vendor summaries describe. It is principles-based and names no metric and
no PSI threshold, so any sentence in this project about what a supervisor
requires must cite SR 26-2 and must not put numbers in its mouth. Every
reference to SR 11-7 in this repository needs replacing.

### Authors and venues

- **Nothing new from Baesens, Lessmann, Bravo, Mues, Verbeke or Verdonck** on
  TFMs and credit beyond arXiv:2605.18147. Adjacent 2026 items found and not
  premise-touching: a fairness preprint by Mues, Casas and Yu; an editorial by
  Andreeva, Crook and Mues; arXiv:2605.22892 on TabPFN for insurance pricing.
- **Credit Scoring and Credit Control XIX has already happened**, 27–29 August
  2025, and the series is biennial: CSCC XX is 31 August – 3 September 2027.
  The 2026 exposure this venue represents is nil; the window opens mid-2027.
  The XIX programme itself is **unread** — the Edinburgh CRC domain serves a
  bot interstitial to every automated route tried, and so do its working
  papers. One CSCC XIX abstract surfaced by title only, "Foundation Models for
  Credit Risk Prediction: Game Changer or **False Hope**?", which is the
  conference precursor of arXiv:2605.18147 under a more sceptical title. Carry.
- **The Mission Lane post was retrieved** through the publication's RSS feed,
  which serves the full body that Medium and the Wayback Machine refuse.
  Archana Subramaniyan, 27 Feb 2026: TabICL **v1** against a tuned LightGBM on
  proprietary data, 2M+ training rows, 950K+ holdout, 300 features; best
  ROC-AUC 0.7010 ± 0.0012 at context ≥ 60K, about 84% of the tuned LightGBM's
  skill; 100–1000× slower in batch and over 10,000× for single-record scoring.
  One metric, ROC AUC. The split is called a holdout and its construction is
  never stated. "Stability" appears twice, meaning run-to-run reproducibility
  and scalability, never population stability. The row moves off `unread` and
  is recorded as `secondary` rather than `verified`, because the account above
  is a report of the post's content and not the post itself.
- **Not retrieved, and the highest-priority carry-over:** *Risks* 14(4):95,
  2026, doi:10.3390/risks14040095, "Temporal and Cost-Sensitive Evaluation
  Framework for Credit Risk Modeling Under Distributional Shifts" — described
  as rolling-forward validation on loan-level data. MDPI and doi.org were both
  unreachable. Whether it involves TFMs at all is unknown, and it is the only
  2026 item pairing temporal with distributional shift on credit.

### Queries that returned nothing, recorded as such

- arXiv, credit × TFM, anything new since 2026-08-27: **nothing.** The
  intersection still holds exactly the two load-bearing papers.
- New versions of the load-bearing papers: **none.** arXiv:2605.18147 is at v2,
  15 Jul 2026, which the 2026-08-27 full-text reading already covered;
  arXiv:2605.18635 is still v1 with no erratum, so the empty-test-window finding
  of EXP-001 stands uncorrected by its authors. Citations: two for the first,
  neither reusing its protocol; **none at all** for the second.
- Four TFM papers appeared in the eight-day window and none touches credit,
  calibration or time: arXiv:2609.02766, arXiv:2608.31013, arXiv:2609.00089,
  arXiv:2608.30337.
- GitHub, PSI critical values in Python: **zero repositories.** Only
  `edpeyton/rpsi` in R, last pushed 2022.
- GitHub, credit × TFM repositories active in the window: four found, three by
  Andreas Goethals, a co-author of arXiv:2605.18147 — `CreditPFN`, `CreditICL`,
  `TabPFNCredit` — and `alexquant1993/tfm_pd_comparison`, which uses this
  study's exact comparator, a WOE-and-logistic scorecard, on German Credit
  under 10-fold cross-validation. Counted with word boundaries across all four
  READMEs: `out-of-time` 0, `vintage` 0, `population stability` 0, `PSI` 0,
  `temporal` 0, `origination` 0. The group closest to this work is building in
  it and has not taken the time axis.
- PyPI, ~50 candidate names for PSI inference beyond the two found: all 404.
  `rpsi` is free as a PyPI name.
- Model-generation papers: no new release. LimiX-2M is now marked **accepted to
  ICML 2026**. Google's **TabFM**, released 2026-06-30, is absent from the model
  table and has no arXiv identifier found; blog-level only.

### Addendum, same day: the scripted arXiv run and the carry-over closed

The three standing arXiv queries were run through the arXiv API rather than a
browser, sorted by submission date, fifteen results each. Query text and
ordering are reproducible from the text below; the intent is to make this the
form every later sweep takes.

- TFM × (credit | calibration | temporal | drift | distribution shift): nothing
  new after 2026-08-31, and nothing in the window touches credit. The newest
  item is arXiv:2608.31013 (physiological time series), already recorded.
- "population stability index": one item not previously recorded.
  **arXiv:2607.12407 — Karasan, Hekimoğlu, "Statistical Properties and Power
  Analysis of Divergence Measures for Credit Risk Model Monitoring" (Jul
  2026).** Derives chi-square nulls for Jensen–Shannon and Kullback–Leibler
  divergences on PD models, cites Yurdakul and Naranjo as prior work, reports
  Type I error and power at small samples. Abstract-only. No PRS, no effect
  size, no overlapping statistic, no code release. A citation for the package,
  not a threat to it. Also surfaced: **arXiv:2507.04866 — Pomazanov (Jul
  2025)**, which argues that PSI movement bounds the Gini a scored population
  can show; abstract-only, and relevant to reading H3 beside H2 rather than
  alone.
- "credit scoring" × (out-of-time | temporal | drift): **arXiv:2410.10182 —
  Marín, "Hamiltonian Neural Networks for Robust Out-of-Time Credit Scoring"**
  (Freddie Mac, AUC in-sample against future windows, no TFM, no calibration,
  no PSI in the abstract). Abstract-only. The rest of the query is agentic and
  LLM material outside the premise.

**The *Risks* 14(4):95 carry-over is closed.** The abstract was retrieved through
Crossref and Semantic Scholar after MDPI refused again: Sodnomdavaa and
Sandagsuren, Mandakh University, rolling-forward validation on unnamed
loan-level data, PR-AUC and a cost-sensitive saving function, a composite
"Unified Policy Stability Index" of their own. No tabular foundation model, no
calibration, no population-stability statistic. It does not touch the premise
and it is not a comparator. Open-access PDF at
`mdpi.com/2227-9091/14/4/95/pdf`, unread.

Net of the addendum: the credit-specific three-leg claim is unchanged, and the
second deliverable's remaining scope — PRS, effect-size and overlapping tests —
is unchanged.

---

## 2026-08-27

First sweep. Ran as part of scoping, before the repository existed.

**Searched.** arXiv listings and general web for: tabular foundation models in
credit risk; TabPFN / TabICL / LimiX generations; calibration and proper
scoring rules for TFMs; out-of-time and drift evaluation of TFMs; population
stability index critical values; Python implementations of PSI inference.

**Found.** The four TFM-generation papers, two credit-specific TFM benchmarks
(arXiv:2605.18147, arXiv:2605.18635), ScoringBench (arXiv:2603.29928), the
uncertainty benchmark (arXiv:2605.28554), and the settled population-stability
literature (Yurdakul 2018; Yurdakul & Naranjo; arXiv:2303.01227;
arXiv:2307.11878). All recorded in [prior-art.md](prior-art.md).

**What changed.** The original project idea — auditing the PSI 0.10/0.25
thresholds as unexamined folklore — was killed by this sweep. The statistics
are solved and published, and implemented in R as `rpsi` on CRAN. The idea
survived roughly forty minutes, which is the sweep gate working as intended and
is the reason it is a gate.

**What replaced it.** The gap moved to tabular foundation models under bank
model-acceptance conditions. See the falsifiable statement at the end of
[prior-art.md](prior-art.md).

**Negative result worth keeping.** No Python package was found implementing PSI
critical values or the PRS. Re-check this every sweep: it is the second
deliverable, and it stops being a deliverable the day somebody publishes one.

**Not searched, and outstanding.** Conference programmes (SEA, ALENEX, CRC,
Credit Scoring and Credit Control XIX) were not checked. The Mission Lane
engineering post returns 403 to automated fetch and has not been read. Both
carry into the next sweep.

**Status of every row: `abstract-only`.** Nothing here has been read in full.
The premise of the project rests on what two papers did *not* do, and an
abstract cannot establish a non-finding.

### Targeted re-check: calibration tooling in Python

Run against the standing PyPI query after the methodology papers were read,
because a metrics module is only worth writing where one does not exist.

**Searched.** PyPI and GitHub for: CORP reliability diagrams, PAV-calibrated
probability curves, MCB/DSC/UNC score decomposition, consistency and confidence
bands for reliability diagrams, and again for PSI critical values and the PRS.

**Found, and it closes a gap that was about to be claimed.** `scores` (PyPI,
2.6.0, July 2026, Australian Bureau of Meteorology) implements the PAV
reliability curve as `scores.processing.isoreg_impl.isotonic_fit`, cites
Dimitriadis, Gneiting and Jordan directly, takes bootstrap confidence bands,
accepts numpy or xarray, and carries the Brier score and threshold-weighted
CRPS besides. The forecast-verification machinery this project intended to
import from meteorology is already packaged in Python, reviewed, and
maintained. It is a dependency, not a deliverable.

**Still open, and narrow.** No Python implementation of the CORP score
decomposition was found. That is three mean scores computed on top of the PAV
fit rather than a package, so it is a function in the metrics module and not a
contribution. `calibre` (`finite-sample/calibre` on GitHub) advertises the
diagram, the decomposition and the MCB–DSC plane; its PyPI page did not load
and it has not been verified. Carry to the next sweep.

**The second deliverable survives, unchanged.** No Python package implements
PSI critical values or the PRS. `feature-engine` computes a bare PSI inside
`DropHighPSIFeatures` for feature selection, with no inference and no critical
values, which is the same shape of gap `mwburke/population-stability-index`
leaves. Re-check every sweep.

> The sentence about `feature-engine` is wrong, and was wrong when written.
> `feature_engine/selection/drop_psi_features.py` line 770 of version 1.9.4,
> released 2026-02-27, returns `chi2.ppf(1 - p_value, bins - 1) * (1/N + 1/M)`
> and cites Yurdakul. Corrected in the 2026-09-04 entry, and left standing here
> because a dated record of what was believed is worth more than a tidy one.

### Two papers the first pass did not surface

Both turned up incidentally while costing out hardware, which is the wrong way
to find them.

arXiv:2606.01427, "On the Uncertainty Quantification Ability of Tabular
Foundation Models" (May 2026), sits inside the standing query on calibration
and tabular foundation models and the first pass over that query missed it. It
does not touch the premise: TabPFN against Gaussian processes, on regression
problems in mechanics and computational science, no time axis and no credit
data. The miss matters more than the paper. The standing queries are run by
hand and a hand-run query is not reproducible, which is the argument for
running each of them from a recorded search rather than from a browser.

arXiv:2512.00888 measures what a forward pass costs in latency and memory, and
appears to be the only paper that does. Its architecture descriptions are
wrong in checkable ways, so it is recorded as partially verified and cited for
orders of magnitude only.
