# Next Steps

ECC is a proof of concept. The published model (`clean-copilot-1.5b-q4_k_m.gguf`, SHA-256 `d2deae6542d1…`) is already trained and may not be retrained. The items below are ordered by importance; **the dataset comes first** because it limits everything else, including any future retraining.

Figures were measured on 2026-11-13 unless noted. Related audit: [docs/evaluation/evaluation-audit-2026-11-05.md](./evaluation/evaluation-audit-2026-11-05.md).

🌐 **[Versión en español →](../es/docs/next-steps.md)**

---

## 1. Dataset (priority)

### 1.1 Too few distinct tasks

| Split | Rows | Distinct prompts |
| :--- | ---: | ---: |
| Used to train the published model (commit `64f3c6c`) | 138 train / 30 holdout | **18** in train |
| Current split (`split_dataset.py`, not yet trained on) | 153 train / 30 holdout | 133 in total, 108 in train |

The 160 teacher-generated rows come from a small set of prompt templates sampled several times. The most repeated training prompts appear 13–14 times each (`python3 dataset/audit_dataset.py`). With a final training loss of 0.031, the model most likely learned these templates rather than a general refactoring skill.

**Next:**
- Raise the number of *distinct* tasks, not rows. Target at least 150–200 distinct prompts before any retraining. One answer per prompt is better than many sampled answers to the same prompt.
- Vary the input code: different domains (billing, inventory, auth, scheduling), sizes, coding styles, and plain JavaScript as well as TypeScript.
- ~~Add a duplicate/near-duplicate check to `audit_dataset.py` that compares the code inside prompts.~~ **Done:** the audit compares the code blocks of prompts (Jaccard similarity of 5-token shingles, `--near-dup-threshold`, default 0.8), reports eval rows whose code is near a train row and near-duplicate pairs inside train, and `--strict` fails on eval near-duplicates. The published split has 9/30 such holdout rows; the current split has none (no pair reaches 0.3).
- Make `audit_dataset.py --strict` a required check before any training run.

### 1.2 Category imbalance

Current distribution across train + holdout (`classify_sample` in `split_dataset.py`):

| Category | Rows | Target in `dataset/README.md` |
| :--- | ---: | ---: |
| Entity / value object | 31 | 30% (with use cases) |
| `USE_CASE` | 20 | |
| Port / adapter | 31 | — |
| AAA test | 32 | 20% |
| `ARCH_REFACTOR` | 49 | **40%** |
| `SOLID_CRITIQUE` | 20 | 10% |

`ARCH_REFACTOR` (messy code → layered code) is the task the CLI actually performs, and it was the thinnest category. All 49 examples were added after the model was trained: 9 hand-written and 40 written by Claude (`claude_authored_examples.jsonl`, pending manual review). A third batch added Claude-written use cases, AAA tests, SOLID critiques and port designs (100 Claude rows in total). With 183 rows, `ARCH_REFACTOR` is 27%, below its 40% target again, and distinct prompts (133) are close to the 150–200 goal. The holdout cap was raised from 15 to 30 rows (25 distinct prompts, at least 4 rows per category); one 6-row teacher group (`Email` value object) landed in it.

**Next:** write or generate more `ARCH_REFACTOR` pairs first, starting from realistic coupled code (Express handlers with SQL, React components calling APIs, services importing ORMs).

### 1.3 Answers are not verified

Teacher answers are only checked for ChatML structure and balanced code fences. Nothing checks that the answer compiles or that it keeps the behavior of the input.

**Next:**
- ~~Type-check every assistant answer.~~ **Done (detection):** `python3 dataset/audit_dataset.py --typecheck [--list-failures]` type-checks each answer's TypeScript in isolation and also reports truncated answers and explicit `any`. Before filtering, the previous split (91 train / 34 eval) had 66/91 and 29/34 passing; 8 train and 11 eval answers contain explicit `any`. Published split (`64f3c6c`): 82/107 pass, 49/138 truncated. **Done (filtering):** `split_dataset.py` now drops rows with explicit `any` or a failing type-check (`--no-verify` skips this): 17 and 26 rows respectively, on top of 61 truncated ones. Two hand-authored `ARCH_REFACTOR` answers were fixed instead of dropped: their adapters now type the external client with a minimal interface instead of `any`. The holdout now takes the smallest prompt groups first and is capped at 15 rows (previously a single 13-row prompt could drain a category). The resulting split (67 train / 15 holdout, every category on both sides) passes the audit 100%.
- For `ARCH_REFACTOR`, keep a small runnable test with the original code and check that the refactored version passes it.
- Score each training answer with CAS and drop low scorers, so the model is not trained on examples the benchmark would penalize.

### 1.4 The published training data ~~is not in the working tree~~

**Done:** the split the published model was trained on is stored as `dataset/published_model_train.jsonl` (138 rows) and `dataset/published_model_holdout.jsonl` (30 rows), copied verbatim from commit `64f3c6c`, and `MODEL_CARD.md` points to them. The committed `train.jsonl` / `eval_holdout.jsonl` are the new split.

### 1.5 The holdout set was contaminated

The holdout used with the published model shared 28 of 30 prompts with training. It cannot be used as evidence about that model. The current split fixes this (0/30 overlap, exact or near-duplicate), but it has not been used yet.

---

## 2. Evaluation

### 2.1 CAS measures form, not correctness

CAS checks for patterns (`interface I…Repository`, `Result.ok`, absence of `any` and framework imports). A model can satisfy it without producing a correct refactor, and the training answers contain those same patterns.

**Next:**
- Add a compile check to `eval_benchmark.py`: wrap each output and run `tsc --noEmit`, and report the compile rate next to CAS.
- Add behavior checks for a subset of cases (input code + tests that must still pass after refactoring).
- Read and grade a sample of completions by hand. `RESULT.md` already asks for 5 per model, and this has not been recorded.

### 2.2 Empty output scores 50

An empty or refusal answer earns 50/100 (30 boundary + 20 typing). This is flagged in reports, but the scale is still misleading.

**Next:** either give zero for outputs with no code, or always report CAS together with the 50-point floor.

### 2.3 Missing baselines

The +16.8 gain is against the base model with the same system prompt. It is not known how much of that gain a better prompt alone would give.

**Next:** run the same suite against:
1. The base model with a few-shot prompt (2–3 examples from the dataset).
2. The 30B teacher (Qwen3-Coder-30B), which shows the ceiling the student is learning from.
3. Optionally, one frontier model.

### 2.4 One small, self-authored suite

The 30 cases were written by the same author, in the same style as the training data.

**Next:** add cases from outside the project (open-source code with real coupling problems), and report results per category.

### 2.5 Noise

The same GGUF scored 72.5 (laptop CPU) and 74.8 (Spark GPU), with a mean per-case difference of 4.7 points; an earlier, unattributed run scored 76.3 and differed from the laptop run by 17.8 points per case.

**Next:** run each model 3–5 times (or at temperature 0) and report the mean and spread.

---

## 3. Training (only if retraining)

- Add a validation loss using the current, prompt-disjoint holdout, and stop early when it stops improving.
- With 18 distinct prompts, 3 epochs reached a loss of 0.031. With a larger dataset, start with 1–2 epochs and compare checkpoints on the benchmark.
- Retrain only after §1.1–§1.3 are done; retraining on the current data would mostly re-learn the same templates.

---

## 4. Documentation consistency

- ~~`MODEL_CARD.md` cites a frontier score of **90.5**.~~ Done 2026-11-13: removed from `MODEL_CARD.md`, `docs/index.html` and the benchmark matrix.
- ~~`MODEL_CARD.md` says the model "eradicates 100%" of forbidden imports.~~ Done 2026-11-13: scoped to the 30-case suite, with the omission caveat (E4).
- `docs/progress-and-milestones.md` and `docs/final-report-and-presentation.md` still use "100% complete" wording. Align them with the proof-of-concept framing of the README.
- ~~`status.py` prints hard-coded states.~~ Done 2026-11-13: it now reports only what it checks (files, line counts, the latest attributed Spark report) and says the Spark is not checked.
- Keep the `es/` mirror in sync with every change above.
