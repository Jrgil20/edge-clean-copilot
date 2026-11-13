# Valid Use Cases: Where to Use the Model and Where Not

> **Model:** `clean-copilot-1.5b-q4_k_m.gguf` (Qwen2.5-Coder-1.5B-Instruct + LoRA, 941 MB).
> **Basis:** what the model was trained on, what the benchmark measured and how fast it runs. See [project-analysis.md](../project/project-analysis.md) for the evidence.
> **How to run it:** [model-usage-and-sharing-guide.md](./model-usage-and-sharing-guide.md).

---

## 1. The envelope in one table

| Dimension | Inside the envelope | Outside the envelope |
| :-- | :-- | :-- |
| Input size | One TypeScript class or function, **up to about 20 lines** (the benchmark used 3–18 lines) | Whole files, several files, modules |
| Language | TypeScript | Python, Go, Java, … (only 13 Python training rows) |
| Task | Refactoring away framework coupling, declaring ports, scaffolding entities, value objects and AAA tests | Behavior-preserving refactors of production code, bug fixing, inline completion |
| Output use | A **draft** that a person reads, compiles and edits | Code applied automatically |
| Environment | Offline or air-gapped machines; a CPU laptop with about 2 GB free RAM | Interactive, latency-sensitive editing (about 47 s per answer on CPU) |
| Audience | Teaching, demos, research on small models | Teams expecting frontier-model quality |

---

## 2. Valid use cases

Each case states what the evidence supports. "Measured" means it was covered by the 30-case benchmark. "Trained" means the training data covered it, but no benchmark measured it.

### UC1: Extract a port from a class coupled to an ORM or HTTP client (measured)

- **Input:** a small class that imports `axios`, `@prisma/client`, `mongoose`, etc. and calls it directly.
- **Expected output:** an `I…Repository` or `I…Gateway` interface, a domain class without the import, and constructor injection.
- **Evidence:** best-scoring categories, with fine-tune vs base: HTTP leakage 80.7 vs 62.9; god class 80.0 vs 38.3; ORM coupling 71.4 vs 49.3. The fine-tune left no forbidden import in 30/30 cases.
- **Check:** the original logic may be dropped rather than moved. Compare against the input.

### UC2: Remove `any` and tighten types in a small snippet (measured)

- **Evidence:** typing component 19.7/20 vs 17.8/20 for the base.
- **Check:** `any` can be replaced by an invented interface. Confirm the new types match real data.

### UC3: Scaffold a value object or entity from a description (trained)

- **Example:** "Implement a pure Value Object `Money` with positive amount and ISO currency."
- **Evidence:** this was the largest training category. It was not part of the benchmark.
- **Check:** invariant guards are weak in benchmark output (2.7/25). Add validation and `Result` handling yourself if the model omits them.

### UC4: Scaffold an AAA unit test with an in-memory test double (trained)

- **Evidence:** about 25 training rows; not benchmarked.
- **Check:** some training answers used `as any` on the mock, so the model may reproduce it. Run the test.

### UC5: Teaching and demonstration (supported)

- Show the Dependency Rule, Ports & Adapters and the difference between a coupled and a decoupled version on small examples, fully offline, in a classroom or a lab without internet.
- This is the use the project is best suited for.

### UC6: Research baseline for small specialised models (supported)

- Use the GGUF, the suite and the attributed reports as a reproducible starting point for comparing data strategies, metrics or other base models.

---

## 3. Where it is ideal to use

1. **Air-gapped or privacy-restricted machines** where code may not leave the device and no cloud assistant is allowed.
2. **Labs and classrooms** without reliable internet, on ordinary laptops (no GPU needed).
3. **Batch, non-interactive runs**, e.g. drafting decoupled versions of a list of small classes overnight, then reviewing them.
4. **A local server on a GPU machine** (e.g. the Spark on port 8085). It is much faster there and can serve several users of a course.

---

## 4. Where not to use it

| Do not use for | Why |
| :-- | :-- |
| Applying refactors to production code without review | Only 12/30 benchmark answers type-checked even in isolation; behavior is never checked. |
| Large files or multi-file changes | Trained with 2,048-token sequences; benchmarked on inputs of 18 lines or fewer. |
| Invariants, validation and `Result`-based error handling | Weakest component (2.7/25); rarely produced. |
| Real-time inline completion (VS Code Copilot routing) | Not trained for fill-in-the-middle; about 12 tok/s on CPU; never evaluated. |
| Replacing a frontier or commercial assistant | Never compared against one. |
| Languages other than TypeScript | Almost no training data. |

---

## 5. Practical tips

- **Keep inputs short.** One class at a time, under about 20 lines. Split larger code first.
- **Use the system prompt the model was trained with.** The CLI already sends it. When calling the HTTP API directly, use the one in `cli/src/application/use-cases/RefactorCodeUseCase.ts`.
- **Keep temperature low** (0.1, the default).
- **On CPU, pass `--max-tokens 600` or less to the CLI.** The adapter times out after 60 s, and at about 12 tok/s longer answers will fail.
- **Do not trust `-o` for code files.** It writes the full reply (Markdown and prose). Prefer `--diff`, or copy the code block by hand.
- **Always compile the result** (`tsc --noEmit`) and run your tests before keeping it.
