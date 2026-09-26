# Code of the recorded runs

Each run's manifest names the commit of the study's working record it ran
at and the sha256 of every code file it ran. This table says, per run,
whether that code is identical in this snapshot or was changed after the
run, and names the files that were. Changed files are available at the
named commit of the record.

| run | record commit | code files | identical here | changed since the run |
|---|---|---:|---:|---|
| 2026-08-30-lc-label-trajectory | `1a671cc7c9c3` | 1 | 0 | `scripts/label_trajectory.py` |
| 2026-08-30-lc-vintage-structure | `9d62a65145eb` | 1 | 0 | `scripts/vintage_structure.py` (dirty) |
| 2026-08-30-lc-vintage-structure-recorded | `64942026981e` | 1 | 0 | `scripts/vintage_structure.py` |
| 2026-09-04-lc-arm-contrast | `e7f236d00907` | 1 | 0 | `scripts/arm_contrast.py` |
| 2026-09-04-lc-arm-contrast-rolling4 | `43b5738fb93d` | 1 | 0 | `scripts/arm_contrast.py` |
| 2026-09-04-lc-gbm-builds | `79fdc418b940` | 1 | 0 | `scripts/gbm_builds.py` |
| 2026-09-04-lc-gbm-byvalue | `5c6d002b2ec7` | 1 | 0 | `scripts/gbm_builds.py` |
| 2026-09-04-lc-gbm-wide | `8ca04fe69e47` | 1 | 0 | `scripts/gbm_builds.py` |
| 2026-09-04-lc-gbm-wide2 | `0344dcadd1a8` | 9 | 6 | `src/outoftime/gbm.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-04-lc-label-sensitivity | `a0d679c38f67` | 1 | 0 | `scripts/label_sensitivity.py` (crlf) |
| 2026-09-04-lc-label-trajectory | `f486c8d8ec09` | 1 | 0 | `scripts/label_trajectory.py` (crlf) |
| 2026-09-04-lc-scorecard-builds | `416241b6bde3` | 1 | 0 | `scripts/scorecard_builds.py` (crlf) |
| 2026-09-04-lc-scorecard-byvalue | `5c6d002b2ec7` | 1 | 0 | `scripts/scorecard_builds.py` (crlf) |
| 2026-09-04-lc-scorecard-byvalue2 | `624880f1c75f` | 1 | 0 | `scripts/scorecard_builds.py` |
| 2026-09-04-lc-scorecard-byvalue3 | `0344dcadd1a8` | 9 | 6 | `src/outoftime/gbm.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-04-lc-scorecard-grid | `d091bf0922b0` | 1 | 0 | `scripts/scorecard_builds.py` (crlf) |
| 2026-09-04-lc-scorecard-uniform | `e1278103a7e3` | 1 | 0 | `scripts/scorecard_builds.py` (crlf) |
| 2026-09-04-lc-vintage-builds | `e0ab2e32ed5d` | 1 | 0 | `scripts/vintage_builds.py` (crlf) |
| 2026-09-04-lc-vintage-builds-byvalue | `2110c76b8730` | 1 | 0 | `scripts/vintage_builds.py` (crlf) |
| 2026-09-04-lc-vintage-builds-rolling4 | `43b5738fb93d` | 1 | 0 | `scripts/vintage_builds.py` (crlf) |
| 2026-09-04-lc-vintage-structure | `f486c8d8ec09` | 1 | 0 | `scripts/vintage_structure.py` (crlf) |
| 2026-09-05-lc-2015h1e-bundle | `6ff487220fa8` | 10 | 6 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-05-lc-2015h1e-intervals | `ca3bb7b9f719` | 10 | 5 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-05-lc-2015h1e-intervals2 | `6ff487220fa8` | 10 | 5 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-05-lc-2015h1e-scores | `ca3bb7b9f719` | 10 | 5 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-fm-reduce | `b614df161db9` | 12 | 6 | `scripts/freddie_mac_reduce.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-fm-reduce2 | `4fae9638facb` | 12 | 6 | `scripts/freddie_mac_reduce.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-fm-reduce3 | `17bedd22dba0` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-fm-vintage-structure | `4fae9638facb` | 12 | 6 | `scripts/freddie_mac_structure.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-fm-vintage-structure2 | `7565c599361a` | 12 | 6 | `scripts/freddie_mac_structure.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-fm-vintage-structure3 | `304d00d1875a` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2013h1e-bundle | `336eea7df44f` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2013h1e-scores | `336eea7df44f` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2013h2e-bundle | `336eea7df44f` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2013h2e-scores | `336eea7df44f` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2014h1e-bundle | `336eea7df44f` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2014h1e-scores | `336eea7df44f` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2014h2e-bundle | `336eea7df44f` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2014h2e-scores | `336eea7df44f` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-draws | `ae0568553626` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-draws2 | `3b4d2e7589b1` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-probe3 | `5affa7fc8bb2` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-probe3-nobal | `051c27d2121c` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-seeds | `78c2998e0f9e` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-tabicl-t1 | `12164b4f18e6` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-tabicl-t1-2 | `3b4d2e7589b1` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-tabpfn | `723170fce85e` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-tfm | `94976f0d74e5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-intervals-tfm2 | `3b5b424f5b4c` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h1e-tabicl-t1-derived | `12164b4f18e6` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h2e-bundle | `336eea7df44f` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2015h2e-scores | `336eea7df44f` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2016h1e-bundle | `336eea7df44f` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2016h1e-scores | `336eea7df44f` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2016h2e-bundle | `336eea7df44f` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2016h2e-scores | `336eea7df44f` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2017h1e-bundle | `336eea7df44f` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-06-lc-2017h1e-scores | `336eea7df44f` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2013h1e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2013h2e-intervals-tabicl | `a10d1e430dd1` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2013h2e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2014h1e-intervals-tabicl | `a10d1e430dd1` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2014h1e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2014h2e-intervals-tabicl | `a10d1e430dd1` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2014h2e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2015h1e-intervals-tabicl | `265da433cb6d` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2015h1e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2015h2e-intervals-tabicl | `265da433cb6d` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2015h2e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2016h1e-intervals-tabicl | `265da433cb6d` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2016h1e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2016h2e-intervals-tabicl | `265da433cb6d` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2016h2e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2017h1e-intervals-tabicl | `265da433cb6d` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-08-lc-2017h1e-tabicl-t1-derived | `82fbb4ab4a02` | 12 | 6 | `scripts/derive_temperature.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-09-lc-2013h1e-intervals-tabicl | `a10d1e430dd1` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2013h1e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2013h2e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2014h1e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2014h2e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2015h1e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2015h2e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2016h1e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2016h2e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-2017h1e-intervals-grid | `e7b617c7dbd5` | 12 | 6 | `scripts/build_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-11-lc-arm-e-intervals | `af04f939b6a3` | 12 | 6 | `scripts/arm_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2013h1r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2013h1r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2013h2r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2013h2r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2014h1r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2014h1r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2014h2r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2014h2r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2015h1e-folds | `09d8f5389bba` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2015h1e-folds-2to5 | `dbde5e1d8dba` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2015h1e-protocols | `65ebe6b28d51` | 12 | 6 | `scripts/protocol_table.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2015h1e-protocols5 | `08cf0904e808` | 12 | 6 | `scripts/protocol_table.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2015h1r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2015h1r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2015h2r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2015h2r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2016h1r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2016h1r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2016h2r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2016h2r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2017h1r-bundle | `adfdb3d21751` | 12 | 7 | `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-2017h1r-scores | `adfdb3d21751` | 12 | 6 | `scripts/score_build.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-12-lc-arm-e-intervals | `a9edd51f56c5` | 12 | 6 | `scripts/arm_intervals.py`, `src/outoftime/gbm.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py`, `src/outoftime/scorecard.py`, `src/outoftime/vintage.py` |
| 2026-09-13-fm-2002h2e-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2002h2e-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2002h2e-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2002h2e-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2e-bundle | `dc50bdcd150b` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2e-bundle-dti-kept | `dc50bdcd150b` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2e-bundle-upb-nominal | `dc50bdcd150b` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2e-scores | `dc50bdcd150b` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2e-scores-dti-kept | `dc50bdcd150b` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2e-scores-upb-nominal | `dc50bdcd150b` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2r-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2r-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2r-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2004h2r-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2006h2e-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2006h2e-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2006h2e-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2006h2e-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2006h2r-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2006h2r-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2006h2r-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2006h2r-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2008h2e-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2008h2e-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2008h2e-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2008h2e-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2008h2r-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2008h2r-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2008h2r-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2008h2r-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2010h2e-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2010h2e-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2010h2e-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2010h2e-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2010h2r-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2010h2r-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2010h2r-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2010h2r-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2012h2e-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2012h2e-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2012h2e-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2012h2e-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2012h2r-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2012h2r-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2012h2r-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2012h2r-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2014h2e-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2014h2e-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2014h2e-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2014h2e-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2014h2r-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2014h2r-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2014h2r-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2014h2r-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2016h2e-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2016h2e-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2016h2e-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2016h2e-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2016h2r-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2016h2r-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2016h2r-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2016h2r-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2018h2e-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2018h2e-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2018h2e-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2018h2e-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2018h2r-bundle | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-2018h2r-scores | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2018h2r-scores-dti-kept | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-2018h2r-scores-upb-nominal | `001b24bd3852` | 13 | 11 | `scripts/fm_score_build.py`, `src/outoftime/metrics.py` |
| 2026-09-13-fm-features | `d4322105b2d3` | 13 | 9 | `scripts/fm_feature_run.py`, `src/outoftime/fm_features.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py` |
| 2026-09-13-fm-features-dti-kept | `d4322105b2d3` | 13 | 9 | `scripts/fm_feature_run.py`, `src/outoftime/fm_features.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py` |
| 2026-09-13-fm-features-dti-kept2 | `de586ecd2c9f` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-features-upb-nominal | `de586ecd2c9f` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-features2 | `de586ecd2c9f` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-grid-budget | `001b24bd3852` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-13-fm-vintage-builds | `d4322105b2d3` | 13 | 10 | `src/outoftime/fm_features.py`, `src/outoftime/metrics.py`, `src/outoftime/performance_label.py` |
| 2026-09-13-fm-vintage-builds2 | `de586ecd2c9f` | 13 | 12 | `src/outoftime/metrics.py` |
| 2026-09-14-fm-2002h2e-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-14-fm-2004h2e-ablation-dti-kept | `960c3b578d56` | 13 | 12 | `scripts/ablation_intervals.py` |
| 2026-09-14-fm-2004h2e-ablation-upb-nominal | `960c3b578d56` | 13 | 12 | `scripts/ablation_intervals.py` |
| 2026-09-14-fm-2004h2e-ablation-upb-nominal-draws | `b1da1a961037` | 13 | 12 | `scripts/ablation_intervals.py` |
| 2026-09-14-fm-2004h2e-dti-kept-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-fm-2004h2e-in-sample | `960c3b578d56` | 13 | 12 | `scripts/in_sample_level.py` |
| 2026-09-14-fm-2004h2e-intervals | `960c3b578d56` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-14-fm-2004h2e-intervals-dti-kept | `960c3b578d56` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-14-fm-2004h2e-intervals-upb-nominal | `960c3b578d56` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-14-fm-2004h2e-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-fm-2004h2e-upb-nominal-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-fm-2006h2e-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-14-fm-2008h2e-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-14-fm-2010h2e-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-14-fm-2012h2e-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-14-fm-2014h2e-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-14-lc-2013h1r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2013h2r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2014h1r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2014h2r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2015h1e-folds-tabicl-t1-derived | `577c25bec903` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2015h1r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2015h2r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2016h1r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2016h2r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-14-lc-2017h1r-tabicl-t1-derived | `0c1f005f6778` | 13 | 11 | `scripts/derive_temperature.py`, `src/outoftime/metrics.py` |
| 2026-09-15-fm-2002h2e-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-fm-2002h2e-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2002h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2002h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2002h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2004h2e-grid-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2004h2e-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-fm-2004h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2004h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2004h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2004h2r-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2004h2r-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2004h2r-tabpfn-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2004h2r-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2004h2r-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2006h2e-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2006h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2006h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2006h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2006h2r-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2006h2r-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2006h2r-tabpfn-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2006h2r-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2006h2r-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2008h2e-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2008h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2008h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2008h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2008h2r-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2008h2r-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2008h2r-tabpfn-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2008h2r-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2008h2r-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2010h2e-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2010h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2010h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2010h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2010h2r-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2010h2r-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2010h2r-tabpfn-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2010h2r-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2010h2r-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2012h2e-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2012h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2012h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2012h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2012h2r-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2012h2r-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2012h2r-tabpfn-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2012h2r-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2012h2r-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2014h2e-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2014h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2014h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2014h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2014h2r-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2014h2r-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2014h2r-tabpfn-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2014h2r-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2014h2r-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2016h2e-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2016h2e-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2016h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2016h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2016h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2016h2r-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2016h2r-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2016h2r-tabpfn-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2016h2r-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2016h2r-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2018h2e-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2018h2e-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2018h2e-tabpfn-t1-measure | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2018h2e-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2018h2e-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2018h2r-bundle-upb-nominal | `b3b2f45f9270` | 13 | 13 |  |
| 2026-09-15-fm-2018h2r-tabicl-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2018h2r-tabpfn-t1-derived | `7a7a798e3eaa` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2018h2r-upb-nominal-tabicl-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-fm-2018h2r-upb-nominal-tabpfn-t1-derived | `45aa7f832ae8` | 13 | 12 | `scripts/derive_temperature.py` |
| 2026-09-15-lc-2013h1r-intervals-grid | `5724c4d94b5b` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-2013h2r-intervals-grid | `5724c4d94b5b` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-2014h1r-intervals-grid | `fd0818a1bd8e` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-2014h2r-intervals-grid | `fd0818a1bd8e` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-2015h1r-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-2015h2r-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-2016h1r-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-2016h2r-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-2017h1r-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-15-lc-arm-contrast-byvalue | `2a0918838cbf` | 13 | 13 |  |
| 2026-09-16-fm-2002h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2004h2e-intervals-apple-check | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2004h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2004h2r-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2004h2r-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2006h2e-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2006h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2006h2r-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2006h2r-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2008h2e-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2008h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2008h2r-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2008h2r-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2010h2e-intervals-grid | `c599ebb6977f` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2010h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2010h2r-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2010h2r-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2012h2e-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2012h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2012h2r-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2012h2r-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2014h2e-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2014h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2014h2r-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2014h2r-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2016h2e-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2016h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2016h2r-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2016h2r-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2018h2e-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2018h2e-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2018h2r-intervals-grid | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-2018h2r-intervals-grid-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/build_intervals.py` |
| 2026-09-16-fm-arm-e-intervals | `1c786fee4a0c` | 13 | 12 | `scripts/arm_intervals.py` |
| 2026-09-16-fm-arm-e-intervals-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/arm_intervals.py` |
| 2026-09-16-fm-arm-r-intervals | `1c786fee4a0c` | 13 | 12 | `scripts/arm_intervals.py` |
| 2026-09-16-fm-arm-r-intervals-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/arm_intervals.py` |
| 2026-09-16-fm-between-arm-intervals | `1c786fee4a0c` | 13 | 12 | `scripts/between_arm_intervals.py` |
| 2026-09-16-fm-grid-in-sample | `1c786fee4a0c` | 13 | 12 | `scripts/in_sample_level.py` |
| 2026-09-16-fm-grid-in-sample-upb-nominal | `1c786fee4a0c` | 13 | 12 | `scripts/in_sample_level.py` |
| 2026-09-16-lc-arm-r-intervals | `c599ebb6977f` | 13 | 12 | `scripts/arm_intervals.py` |
| 2026-09-16-lc-between-arm-intervals | `1c786fee4a0c` | 13 | 12 | `scripts/between_arm_intervals.py` |
| 2026-09-16-psi-ztest-size | `47ba5588b313` | 13 | 13 |  |
| 2026-09-17-fm-2002h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2004h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2004h2r-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2006h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2006h2r-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2008h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2008h2r-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2010h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2010h2r-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2012h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2012h2r-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2014h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2014h2r-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2016h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2016h2r-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2018h2e-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-2018h2r-control-refit | `8816e912d0be` | 16 | 16 |  |
| 2026-09-17-fm-arm-contrast | `45c6f7b10338` | 19 | 17 | `scripts/fm_score_build.py`, `scripts/score_build.py` |
| 2026-09-17-fm-arm-e-intervals | `1ad2915f5eea` | 16 | 13 | `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-fm-arm-e-intervals-outcome-reported | `1ad2915f5eea` | 16 | 13 | `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-fm-arm-e-intervals-refit-control | `1ad2915f5eea` | 16 | 13 | `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-fm-arm-r-intervals | `9f0e11093bca` | 16 | 14 | `scripts/arm_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-fm-between-arm-intervals | `116b5cbe78c1` | 19 | 14 | `scripts/ablation_intervals.py`, `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/derive_temperature.py`, `scripts/score_context.py` |
| 2026-09-17-fm-between-arm-intervals-outcome-reported | `51307103a52e` | 19 | 14 | `scripts/ablation_intervals.py`, `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/derive_temperature.py`, `scripts/score_context.py` |
| 2026-09-17-fm-between-arm-intervals-refit-control | `1ad2915f5eea` | 19 | 16 | `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-fm-between-arm-intervals-upb-nominal | `1ad2915f5eea` | 19 | 16 | `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-fm-grid-in-sample | `9f0e11093bca` | 16 | 14 | `scripts/in_sample_level.py`, `scripts/score_context.py` |
| 2026-09-17-fm-h4-sensitivity | `40440176b052` | 13 | 13 |  |
| 2026-09-17-fm-h5-rescaled-control | `0ce5b321424f` | 13 | 13 |  |
| 2026-09-17-fm-h5-rescaled-control-in-sample | `8e3a0206656a` | 16 | 13 | `scripts/build_intervals.py`, `scripts/in_sample_level.py`, `scripts/score_context.py` |
| 2026-09-17-fm-kill-criterion-3 | `774fe4fa8de2` | 13 | 13 |  |
| 2026-09-17-lc-2013h1e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2013h1r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2013h2e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2013h2r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2014h1e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2014h1r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2014h2e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2014h2r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2015h1e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2015h1r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2015h2e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2015h2r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2016h1e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2016h1r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2016h2e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2016h2r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2017h1e-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-2017h1r-control-refit | `8816e912d0be` | 13 | 13 |  |
| 2026-09-17-lc-arm-e-intervals | `9f0e11093bca` | 16 | 14 | `scripts/arm_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-lc-arm-e-signed-slope-control | `9f0e11093bca` | 16 | 14 | `scripts/arm_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-lc-arm-e-signed-slope-control-parent | `1ad2915f5eea` | 16 | 13 | `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-lc-arm-e-signed-slope-control-seeds | `9f0e11093bca` | 16 | 14 | `scripts/arm_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-lc-arm-e-signed-slope-control-seeds-parent | `1ad2915f5eea` | 16 | 13 | `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-lc-arm-r-intervals | `9f0e11093bca` | 16 | 14 | `scripts/arm_intervals.py`, `scripts/score_context.py` |
| 2026-09-17-lc-between-arm-intervals | `51307103a52e` | 19 | 14 | `scripts/ablation_intervals.py`, `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/derive_temperature.py`, `scripts/score_context.py` |
| 2026-09-17-lc-h4-sensitivity | `40440176b052` | 13 | 13 |  |
| 2026-09-17-lc-kill-criterion-3 | `774fe4fa8de2` | 13 | 13 |  |
| 2026-09-17-psi-ztest-size-pinned | `d0dc34938a52` | 19 | 19 |  |
| 2026-09-17-smoothing-dry-run | `3257fee39c51` | 16 | 14 | `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-18-fm-arm-e-intervals | `9f0e11093bca` | 16 | 14 | `scripts/arm_intervals.py`, `scripts/score_context.py` |
| 2026-09-18-fm-arm-e-intervals-outcome-reported | `9f0e11093bca` | 16 | 14 | `scripts/arm_intervals.py`, `scripts/score_context.py` |
| 2026-09-18-lc-arm-e-intervals-at-1ad2915 | `1ad2915f5eea` | 16 | 13 | `scripts/arm_intervals.py`, `scripts/build_intervals.py`, `scripts/score_context.py` |
| 2026-09-19-fm-arm-e-intervals | `386c62975a98` | 17 | 16 | `scripts/score_context.py` |
| 2026-09-19-fm-arm-r-intervals | `386c62975a98` | 17 | 16 | `scripts/score_context.py` |
| 2026-09-19-fm-grid-in-sample | `386c62975a98` | 17 | 16 | `scripts/score_context.py` |
| 2026-09-19-fm-vintage-structure | `049c8261aa31` | 13 | 13 |  |
| 2026-09-19-lc-arm-e-intervals | `386c62975a98` | 17 | 16 | `scripts/score_context.py` |
| 2026-09-19-lc-arm-r-intervals | `386c62975a98` | 17 | 16 | `scripts/score_context.py` |
| 2026-09-19-lc-label-sensitivity | `d87152ceaa47` | 13 | 13 |  |
| 2026-09-19-lc-label-trajectory | `d87152ceaa47` | 13 | 13 |  |
| 2026-09-19-lc-vintage-structure | `d87152ceaa47` | 13 | 13 |  |
| 2026-09-20-fm-arm-e-intervals-refit-control | `386c62975a98` | 17 | 16 | `scripts/score_context.py` |
| 2026-09-20-fm-h5-rescaled-control-in-sample | `1f32bca750b9` | 17 | 16 | `scripts/score_context.py` |
| 2026-09-21-fm-arm-e-intervals | `a36c751e366e` | 17 | 17 |  |
| 2026-09-21-fm-arm-e-intervals-refit-control | `a36c751e366e` | 17 | 17 |  |
| 2026-09-21-fm-arm-r-intervals-refit-control | `386c62975a98` | 17 | 16 | `scripts/score_context.py` |
| 2026-09-21-fm-between-arm-intervals | `5c653368eeb8` | 19 | 18 | `scripts/score_context.py` |
| 2026-09-21-fm-between-arm-intervals-outcome-reported | `5c653368eeb8` | 19 | 18 | `scripts/score_context.py` |
| 2026-09-21-fm-between-arm-intervals-refit-control | `5c653368eeb8` | 19 | 18 | `scripts/score_context.py` |
| 2026-09-21-lc-2015h1e-fold-bundles | `25f4af7dac42` | 13 | 13 |  |
| 2026-09-22-fm-arm-r-intervals-refit-control | `a36c751e366e` | 17 | 17 |  |
| 2026-09-22-fm-between-arm-intervals | `a36c751e366e` | 19 | 19 |  |
| 2026-09-22-fm-between-arm-intervals-outcome-reported | `a36c751e366e` | 19 | 19 |  |
| 2026-09-22-fm-between-arm-intervals-refit-control | `a36c751e366e` | 19 | 19 |  |
| 2026-09-22-fm-grid-in-sample | `a36c751e366e` | 17 | 17 |  |
| 2026-09-22-lc-2015h1e-fold1-tabicl-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold1-tabicl-t1-check-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold1-tabpfn-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold1-tabpfn-t1-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold2-tabicl-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold2-tabicl-t1-check-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold2-tabpfn-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold2-tabpfn-t1-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold3-tabicl-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold3-tabicl-t1-check-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold3-tabpfn-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold3-tabpfn-t1-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold4-tabicl-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold4-tabicl-t1-check-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold4-tabpfn-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold4-tabpfn-t1-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold5-tabicl-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold5-tabicl-t1-check-4090 | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold5-tabpfn-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-2015h1e-fold5-tabpfn-t1-m4pro | `a5e47cd4af8d` | 3 | 3 |  |
| 2026-09-22-lc-arm-e-intervals | `a36c751e366e` | 17 | 17 |  |
| 2026-09-23-fm-arm-e-intervals-upb-nominal | `a36c751e366e` | 17 | 17 |  |
| 2026-09-23-fm-arm-r-intervals-upb-nominal | `a36c751e366e` | 17 | 17 |  |
| 2026-09-23-fm-between-arm-intervals-upb-nominal | `a36c751e366e` | 19 | 19 |  |
| 2026-09-23-fm-grid-in-sample-upb-nominal | `a36c751e366e` | 17 | 17 |  |
| 2026-09-23-lc-2013h1e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-2013h2e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-2014h1e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-2014h2e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-2015h1e-fold1-tabicl-t1-derived | `5f9ed9f18195` | 14 | 14 |  |
| 2026-09-23-lc-2015h1e-fold2-tabicl-t1-derived | `5f9ed9f18195` | 14 | 14 |  |
| 2026-09-23-lc-2015h1e-fold3-tabicl-t1-derived | `5f9ed9f18195` | 14 | 14 |  |
| 2026-09-23-lc-2015h1e-fold4-tabicl-t1-derived | `5f9ed9f18195` | 14 | 14 |  |
| 2026-09-23-lc-2015h1e-fold5-tabicl-t1-derived | `5f9ed9f18195` | 14 | 14 |  |
| 2026-09-23-lc-2015h1e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-2015h1e-intervals-grid | `801f60a25e25` | 15 | 15 |  |
| 2026-09-23-lc-2015h1e-protocols5-criteria | `c5a07426b941` | 13 | 13 |  |
| 2026-09-23-lc-2015h1e-protocols5-tfm | `801f60a25e25` | 18 | 18 |  |
| 2026-09-23-lc-2015h2e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-2016h1e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-2016h2e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-2017h1e-in-sample | `c5a07426b941` | 17 | 17 |  |
| 2026-09-23-lc-features | `652f83fefe34` | 14 | 14 |  |
| 2026-09-24-fm-2002h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2004h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2004h2r-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2006h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2006h2r-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2008h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2008h2r-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2010h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2010h2r-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2012h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2012h2r-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2014h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2014h2r-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2016h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2016h2r-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2018h2e-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-2018h2r-intervals-grid-dti-kept | `c697dd1d4668` | 15 | 15 |  |
| 2026-09-24-fm-arm-e-intervals-dti-kept | `c697dd1d4668` | 17 | 17 |  |
| 2026-09-24-fm-arm-r-intervals-dti-kept | `c697dd1d4668` | 17 | 17 |  |
| 2026-09-24-lc-2013h1e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-2013h2e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-2014h1e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-2014h2e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-2015h1e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-2015h2e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-2016h1e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-2016h2e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-2017h1e-label24 | `57f6bce840c6` | 18 | 18 |  |
| 2026-09-24-lc-between-arm-intervals | `3e8954b8064d` | 19 | 19 |  |
| 2026-09-25-fm-2002h2e-reliability | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-fm-2002h2e-ridge | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-fm-arm-e-auc-age-floors | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-fm-arm-e-intervals-horizon | `7a85efc64523` | 18 | 18 |  |
| 2026-09-25-fm-arm-r-intervals-horizon | `7a85efc64523` | 18 | 18 |  |
| 2026-09-25-fm-build-grid | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-fm-grid-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-fm-grid-in-sample-upb-nominal-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-fm-metric-age | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-fm-relief-share | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2013h1e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2013h2e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2014h1e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2014h2e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2015h1e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2015h1e-ridge | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2015h2e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2016h1e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2016h2e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-2017h1e-in-sample-level | `d30009f22bc5` | 20 | 20 |  |
| 2026-09-25-lc-arm-e-intervals-label24 | `b6e4ddc18f1e` | 18 | 18 |  |
| 2026-09-25-lc-arm-e-intervals-label24-at12 | `b6e4ddc18f1e` | 18 | 18 |  |
| 2026-09-25-paper-tables | `33815d930c4f` | 22 | 22 |  |
| 2026-09-26-fm-arm-e-build-rows-print | `c3d2b1f1d57f` | 24 | 24 |  |
| 2026-09-26-fm-between-arm-rows-print | `c3d2b1f1d57f` | 24 | 24 |  |
| 2026-09-26-fm-kill-criterion-3-upb-nominal | `2fe1054b3402` | 13 | 13 |  |
| 2026-09-26-lc-2015h1e-reliability-print | `c3d2b1f1d57f` | 24 | 24 |  |
| 2026-09-26-lc-arm-e-auc-age-print | `c3d2b1f1d57f` | 24 | 24 |  |
