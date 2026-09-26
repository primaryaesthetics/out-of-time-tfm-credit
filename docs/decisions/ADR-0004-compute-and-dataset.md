# ADR-0004 — data local, forward passes on a hosted GPU

Date: 2026-08-27. Status: accepted.

## Decision

Lending Club is the dataset, pulled once through the Kaggle API and held
locally. Everything except the foundation-model forward passes runs on the
development machine. The forward passes run on Google Colab's free tier.

The first thing run on the accelerator is a timing probe, and the probe needs
no data at all.

## Context

The development machine has no CUDA device. Costed against the only published
measurement of what a forward pass takes — arXiv:2512.00888 on an NVIDIA T4,
recorded as only partially verified — a quarterly vintage trajectory at three
seeds is hours of accelerator time against weeks of CPU time. The classical
half of the study is minutes either way.

Kaggle Notebooks were the first choice. The quota is published, and the
`kernels push` workflow would have kept a version-controlled script as the unit
of work. That route is closed. Kaggle gates notebook GPU and notebook internet
behind phone verification, and phone verification is not available here.

Colab has no such gate: the free tier needs a Google account and nothing else,
and it serves the same T4. Its allowance is comparable, but it is unpublished
and revocable, and idle sessions get disconnected. Confirmed working.

The two resources turned out to be independent, which is what makes the
verification gate survivable. Dataset access through the Kaggle API needs an
account and acceptance of the dataset's terms, not a verified phone. The data
therefore comes down once over the API and lives on disk here, and nothing
about that path touches notebooks.

Lending Club is chosen over the Freddie Mac single-family data for three
reasons. It is 1.4 GB compressed and fits, where Freddie Mac's full set is far
larger than the free disk here and needs its own registration. It carries a
real origination axis in `issue_d`. Most of all, arXiv:2605.18635 ran the
literature's only temporal validation on this exact dataset, training to June
2019 and testing on the half-year after, so numbers here are comparable to
published ones rather than merely adjacent to them.

Freddie Mac remains the stronger vintage substrate. It spans 2008 where
Lending Club does not. It is the extension, not the starting point.

## Consequences

- The estimate is replaced by a measurement before any design is fixed. A
  design fixed on the strength of a paper whose architecture claims are wrong
  is a design resting on nothing.
- The probe measures shape, not content. Forward-pass cost is set by context
  size, feature count and batch size, so the probe runs on a synthetic frame of
  the intended shape and moves no data to the accelerator at all. What this
  does not capture is preprocessing on real columns, and that is stated
  wherever the probe's numbers are used.
- Colab costs the `kernels push` workflow. A run there is driven by hand rather
  than by a command, so the discipline has to be carried by the script instead:
  the probe emits its own environment block, and the manifest is assembled here
  from what it returns.
- Accelerator forward passes are nondeterministic. Every timing is taken twice
  and the disagreement is recorded rather than averaged away.
- A result that exists only in a notebook session is not evidence. It reaches
  `experiments/<date>-<slug>/` carrying a manifest, the raw output and one
  plot of structure, or it does not count.
- The quota is a real constraint on the protocol and belongs in the setting
  section of every experiment that spends it, beside the tuning budget.

## Closed on 2026-08-30

**The data stops at 2018-12.** EXP-001 measured the origination axis at
2007-06 to 2018-12 across 47 quarterly cohorts. The framing that tests across
the 2020 regime shift is unavailable here and is dropped rather than stretched.
The vintage trajectory remains the contribution.

**The estimate was wrong, and wrong in the safe direction.** The probe ran on a
Colab T4 with 15.64 GB, recorded in
`experiments/2026-08-30-colab-t4-timing-probe`. TabICL scores 20,000 rows from
a 10,000-row context in about 13 seconds. Twenty-nine cohorts at three seeds is
87 passes, so the trajectory is minutes of accelerator time rather than the
tens of hours arXiv:2512.00888 implied. Nothing in this study is time-bound at
these shapes, and TabICL stays in the set on measured cost rather than on a
guess about it.

**Memory is the constraint instead.** Peak allocation sat at 9.1 GB for a
5,000-row context and 9.5 GB for 10,000, against 15.64 GB available. Barely
moving while the context doubles points at the 20,000-row scoring batch as what
sets the floor, not the context. That is a design lever, since a scoring batch
can be split and a training context cannot.

## The ceiling, found on 2026-08-30

Recorded in `experiments/2026-08-30-colab-t4-ceiling`. A 50,000-row context
runs, peaking at 12.4 GB with 3.2 GB to spare. A 100,000-row context kills the
kernel. Peak allocation climbs at 0.076 GB per thousand context rows over the
measured range, which puts 100,000 rows at 16.2 GB against 15.64 available, so
the arithmetic and the kill agree.

Time is super-linear where memory is nearly flat. Two and a half times the
context costs three and a third times the seconds: 12.2 s at 10,000 rows,
22.8 s at 20,000, and 76.4 s at 50,000.

The first reading of that, written here before the next measurement, was that a
context could not exceed about fifty thousand rows. That was wrong. It came
from one sweep taken at a fixed scoring batch, which cannot separate what the
context costs from what the batch costs.

## The memory law, 2026-08-30

Recorded in `experiments/2026-08-30-colab-t4-memory-law`. The hypothesis under
test was that the 20,000-row scoring batch set the floor. Cutting it fourfold
moved peak allocation by 8.8%, so it does not.

What fits four measurements, to a maximum residual of 0.035 GB:

    peak_gb = 7.27 + 0.0743 * context/1k + 0.0724 * scored/1k

The two coefficients agree to within 2.5%. **A context row and a scored row
cost the same 73 KB**, because TabICL holds both in one attention buffer. There
is one row budget rather than two, about 114,000 rows on a T4, and it is shared.
The law predicts 16.07 GB for the configuration that killed the kernel against
15.64 available, which is why it died.

So the reachable context depends on what is being scored beside it: about
109,000 rows when scoring in chunks of 5,000, and about 94,000 when scoring
20,000 at once. Chunking trades time for headroom, and time is not the binding
resource here.

**TabPFN is a different animal, and stops for a different reason.** At a
10,000-row context scoring 20,000 rows it peaks at 0.668 GB against TabICL's
9.489, fourteen times less, and takes 18.9 s against 12.2.

Over that narrow range its memory looked flat, and the first reading here
called that internal chunking. The wider sweep refuses it. The slope is 0.0036
GB per thousand context rows below ten thousand and 0.0114 between twenty and
fifty thousand, three times steeper, and a straight line through all five
points leaves a 0.034 GB residual. The growth is real and it is not linear.

It is still small. Extrapolated to a hundred thousand rows TabPFN wants about
1.6 GB, a tenth of the card, at a context TabICL cannot reach at all. What
binds TabPFN is time. Seconds grow as context to the power 1.63 against
TabICL's 1.32, so 50,000 rows costs 106 s and 100,000 rows costs an estimated
330 s. At three seeds over twenty-nine cohorts that is eight hours of quota for
one model, and the estimate rests on two points.

**So there is no single row ceiling for "the foundation models".** TabICL runs
out of memory while time is still cheap; TabPFN runs out of time while memory
is still cheap. A design that caps them at the same number has to say which
constraint it is respecting and why. A 50,000-row context runs both inside two
hours of passes, and that is the operating point until something argues
otherwise.

**The design consequence, restated on the corrected numbers.** An in-context
learner has no training phase to amortise, so its context is its training set.
For TabICL that set tops out near one quarterly cohort of Lending Club, which
runs past 100,000 loans from 2015 onward. Any training window spanning several
quarters exceeds it. The foundation models will therefore see a subsample of a
window that the scorecard and the gradient-boosted baseline see whole, and the
two foundation models may not even be limited at the same point.

That asymmetry cannot be quietly absorbed. Either every model is fitted on the
same subsample, which measures the models but understates what a bank would
actually deploy, or each is given what it can use, which measures the deployable
systems but confounds the architecture with the sample size. Both are defensible
and they answer different questions. The choice is recorded before any model is
fitted, not after the numbers are in.

TabPFN did not run at all. Version 8.5.0 requires a one-time licence
acceptance at Prior Labs before it will fetch weights, and a notebook has no
interactive terminal to accept it in. This is an account step, not a technical
one, and until it is done the comparison has one model in it.

## The Apple node, measured on 2026-09-02

Recorded in `experiments/2026-09-02-m3-tabpfn-timing`. An Apple M3 with 17.18 GB
of unified memory ran TabPFN through Metal, sweeping the context from 1,000 rows
to 50,000 while scoring 5,000 rows each time.

It is a T4 divided by 5.6. One configuration was run on both machines at the
same context and the same scoring batch: 50,000 rows of context against 5,000
scored. It takes 106 s on the T4 against 600 s here. That single matched pair is
the whole of the ratio. Every other pair differs in scoring batch and cannot be
divided.

The shape is the same on both. Seconds grow as context to the power 1.634 on the
T4 and 1.617 on the M3, measured over the large-context end of each sweep. Two
vendors and two backends agree to about one percent. The constant differs. The
asymptotics do not. What the T4 established about where TabPFN becomes
expensive therefore carries across, and only the wall-clock changes. Each
exponent rests on two points and is indicative rather than fitted.

Memory was not compared, because the two readings are different quantities. CUDA
reports a high-water mark over live tensors. Metal reports the driver's
allocated pool, cache included, after the pass. Their ratio means nothing. What
survives is that TabPFN at a 50,000-row context spends single-digit gigabytes on
a machine that has 17.18, and is no more memory-bound here than it was there.

The probe miscaptioned its own run. The guard printing the device note tested
for the absence of CUDA rather than the presence of a CPU, so it told an Apple
machine that it was timing the CPU path while the model sat on Metal. The
numbers are unaffected. They were taken with `device="mps"`, and the Metal
allocator grew from 1.411 GB to 2.611 GB as the context grew, which a process
that never touches Metal does not do. The caption is now derived from the device
that was used, and a test constructs the mistake.

TabPFN is unblocked on Colab. The licence acceptance that version 8.5.0 demands,
and that a notebook has no terminal to give, has now been made against the
account. That reopens the free T4 for the model that could not run there, which
is the larger of the two results recorded on this date.

**What is still open, and it is the part that decides a rental.** TabICL was not
run on the M3. It is the memory-bound model, the T4 needed 11.35 GB at exactly
this shape, and the memory available here is unified with the operating system
rather than reserved. The memory law of 2026-08-30 was fitted on CUDA and does
not transfer to Metal. Every timing on both machines also scores 5,000 rows,
where a Lending Club cohort from 2015 onward runs past 100,000 loans, and how
seconds grow in the scoring batch has never been measured on either machine.
Until both are, the per-pass cost of the study is a floor and not an estimate.
