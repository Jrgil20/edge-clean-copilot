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
| Current split (`split_dataset.py`, not yet trained on) | 91 train / 34 holdout | 36 in total, 28 in train |

The 160 teacher-generated rows come from a small set of prompt templates sampled several times. The most repeated training prompts appear 13–14 times each (`python3 dataset/audit_dataset.py`). With a final training loss of 0.031, the model most likely learned these templates rather than a general refactoring skill.

**Next:**
- Raise the number of *distinct* tasks, not rows. Target at least 150–200 distinct prompts before any retraining. One answer per prompt is better than many sampled answers to the same prompt.
- Vary the input code: different domains (billing, inventory, auth, scheduling), sizes, coding styles, and plain JavaScript as well as TypeScript.
- Add a duplicate/near-duplicate check to `audit_dataset.py` that compares the code inside prompts, not only the prompt text.
- Make `audit_dataset.py --strict` a required check before any training run.

### 1.2 Category imbalance

Current distribution across train + holdout (`classify_sample` in `split_dataset.py`):

| Category | Rows | Target in `dataset/README.md` |
| :--- | ---: | ---: |
| Entity / value object | 43 | — |
| Port / adapter | 34 | — |
| AAA test | 28 | 20% |
| `ARCH_REFACTOR` | 10 | **40%** |
| `SOLID_CRITIQUE` | 10 | 10% |

`ARCH_REFACTOR` (messy code → layered code) is the task the CLI actually performs, and it is the thinnest category. Its 10 examples are hand-written and were added after the model was trained.

**Next:** write or generate more `ARCH_REFACTOR` pairs first, starting from realistic coupled code (Express handlers with SQL, React components calling APIs, services importing ORMs).

### 1.3 Answers are not verified

Teacher answers are only checked for ChatML structure and balanced code fences. Nothing checks that the answer compiles or that it keeps the behavior of the input.

**Next:**
- Run `tsc --noEmit` on every code block in every assistant answer, and drop or fix the ones that fail.
- For `ARCH_REFACTOR`, keep a small runnable test with the original code and check that the refactored version passes it.
- Score each training answer with CAS and drop low scorers, so the model is not trained on examples the benchmark would penalize.

### 1.4 The published training data is not in the working tree

The committed `train.jsonl` / `eval_holdout.jsonl` are the new split. The data the published model was trained on only exists in git history (`git show 64f3c6c:dataset/train.jsonl`).

**Next:** store it as `dataset/published_model_train.jsonl` (or record the commit in `MODEL_CARD.md`) so the model's training data stays easy to find.

### 1.5 The holdout set was contaminated

The holdout used with the published model shared 28 of 30 prompts with training. It cannot be used as evidence about that model. The current split fixes this (0/34 overlap), but it has not been used yet.

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

- `MODEL_CARD.md` cites a frontier score of **90.5**. The audit (F3, F8) found no recorded run behind it. Remove the number or mark it as unmeasured.
- `MODEL_CARD.md` says the model "eradicates 100%" of forbidden imports. This holds on the 30-case suite only; say so.
- `docs/progress-and-milestones.md` and `docs/final-report-and-presentation.md` still use "100% complete" wording. Align them with the proof-of-concept framing of the README.
- `status.py` prints hard-coded states (for example "DGX Spark Status: Offline (Curfew)"). Compute them or remove them.
- Keep the `es/` mirror in sync with every change above.
