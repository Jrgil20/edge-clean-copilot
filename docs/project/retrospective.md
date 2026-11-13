# Retrospective: Observations and Lessons

> **Date:** 2026-11-13
> **Purpose:** what the project revealed about itself: where its value lies, where its limits come from and what that implies for later work. The evidence behind each observation is in [project-analysis.md](./project-analysis.md); this document interprets it.

---

## 1. The value lies in the process, not the artifact

The proposal set out to show that a small model can be specialised, packaged and evaluated with limited, shared hardware. Every stage of that process now exists, is scripted and has been executed:

- teacher-generated data;
- time-capped LoRA training on a shared GPU;
- GGUF export and offline serving;
- a hexagonal client;
- an attributed benchmark.

The "Cold Staging, Hot Burst" method and the care taken not to disturb other users of the shared machine can be reused independently of the model they produced.

The model itself is one output of that process, and a modest one. This shapes how the project should be cited. It is evidence that the **method** works under real constraints. It is not evidence that small models rival large ones.

## 2. The project corrected itself, and that is part of the result

Earlier documents reported:

- a frontier comparison that was never run;
- a holdout described as isolated that was not;
- hyperparameters that differ from the code that actually ran;
- progress described as complete.

Later work audited those claims, re-measured them, marked the unsupported ones and left the corrections visible in the history. One correction in this retrospective's own period followed the same pattern. A first type-check measurement suggested the fine-tune wrote more type-correct code than the base model. A more careful check showed the opposite (14/30 vs 17/30), and the claim was withdrawn.

**Observation:** the parts of a project that are measured automatically tend to stay honest. The parts that are written by hand drift toward optimism. Attributed reports, audit scripts and tests did more for the credibility of the results than any prose.

## 3. The model learned a template, not a skill

The fine-tune beats its base model consistently: +16.8 CAS points, 24 wins, no losses. Where the gain comes from is revealing:

- **Most of the gain:** removing framework imports and declaring interfaces. These are the two behaviors the metric rewards most cheaply.
- **Almost none of the gain:** validating invariants or using `Result`, although most training answers did both.
- **Score shape:** 26 of 30 scores fall in a narrow 65–75 band.

The model reproduces a shape (an interface, a class with a private constructor and a static factory, no imports) rather than adapting to the code in front of it.

**Observation:** with 18 distinct training prompts, a low training loss (0.031) measured memorisation of the templates. It did not measure learning. A low loss on a small, repetitive dataset is a warning sign, not a success signal.

## 4. Data quality was the binding constraint

The limits of the model trace back to the data more than to the model size, the hyperparameters or the training code:

- **Few tasks:** 18 distinct prompts behind 138 rows.
- **Truncated answers:** 35% of the training answers stop mid-code.
- **Explicit `any`:** many answers use it, contradicting the project's own rule.
- **Wrong task mix:** almost no examples ask for the task the benchmark measures (refactoring given code).

None of this was visible while the data was being produced. It only appeared once the data was audited.

**Observation:** a teacher model's output is raw material, not training data. Between the two there needs to be a gate that rejects:

- truncated answers;
- forbidden constructs;
- code that does not type-check.

That gate now exists (`split_dataset.py` and `audit_dataset.py --typecheck`). Applied to the current data, it keeps 82 of 186 rows. The cleaner dataset is also much smaller, which says how little verified signal the original volume contained.

## 5. A metric shapes what it measures

The Clean Architecture Score made comparison possible, and comparison is what produced the one robust result. It also has blind spots that the model found:

- **A floor for doing nothing:** an empty answer scores 50.
- **Loose "ports":** any interface counts as a port.
- **Free boundary points:** leaving out imports earns the full boundary score.
- **No correctness check:** whether the code compiles or still does what it did is not part of the score.

The fine-tune's profile matches these blind spots closely.

**Observation:** a metric that checks the form of the output invites outputs that have the right form. Unless correctness is part of the score, the score measures appearance. Checks that are cheap and deterministic (compilation, behavior tests on the original code) belong in the metric itself, not in a later manual review.

## 6. Hypotheses need their comparison group from the start

The proposal's central hypothesis is a comparison: a specialised small model against general commercial models. The project never ran the comparison group. The base model was the only baseline. There was no few-shot-prompted base, no teacher model and no frontier model.

As a result, the hypothesis is neither confirmed nor refuted. It is untested, and a placeholder figure (90.5) circulated for a while as if it were a result.

**Observation:** when a hypothesis is a comparison, the comparison group is part of the minimum viable experiment. It is not a later addition. Without it, the most that can be claimed is improvement over the starting point.

## 7. Constraints shaped the design, mostly for the better

Short GPU windows, a shared machine and a CPU-only laptop forced decisions that turned out to be sound:

- the dry-run mode;
- the mock inference engine;
- time and memory caps;
- one-command evaluation;
- prompt-disjoint splits that can be checked offline.

The same constraints also explain the gaps:

- no validation loss;
- no repeated runs;
- no larger model;
- about 12 tokens per second on CPU (about 47 s per answer), which rules out interactive use.

**Observation:** constrained environments reward investment in offline tooling (tests, audits, mocks), because every minute of scarce hardware time then goes into the run itself.

## 8. What the project leaves for later work

The observations above point to the same few open questions. Each is concrete and measurable:

1. **Data:** does a verified, diverse dataset (150–200 distinct refactoring tasks, every answer type-checked) produce a model that adapts to the code, rather than a template?
2. **Measurement:** what does the comparison look like when the score includes compilation and behavior preservation and subtracts the do-nothing floor?
3. **Comparison:** where does a specialised small model stand against the same base model with good prompting, against its teacher and against a frontier model, on the same suite?
4. **Hybrid systems:** does a small model paired with a deterministic verifier reach acceptable quality where the model alone does not? Verification has proved cheap and the model alone has proved insufficient, so this is the most direct continuation.

The project can be cited for this: a reproducible process for specialising small models on limited hardware, together with an honest measurement of where it falls short. The shortfalls define the follow-up work.
