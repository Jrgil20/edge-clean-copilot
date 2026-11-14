# Edge Clean Copilot CLI

Command-line interface for **Edge Clean Copilot**, implementing the **Ports & Adapters (Hexagonal) Architecture** to ensure complete decoupling between core business logic and local language model inference engines.

---

## 1. Architectural Layers

```
proyecto/cli/src/
├── domain/                    # Pure business logic and invariants
│   └── entities/
│       └── SourceFile.ts      # Validates file size, extensions, and immutability
│
├── application/               # Application orchestration and interfaces
│   ├── dtos/
│   │   └── RefactorDTO.ts     # Input and output boundary data transfers
│   ├── ports/
│   │   └── IInferenceEngine.ts # Primary outbound inference port contract
│   ├── services/
│   │   └── extractCodeBlocks.ts # Keeps only the fenced code of a model reply
│   └── use-cases/
│       └── RefactorCodeUseCase.ts # Orchestrates domain verification and inference
│
├── infrastructure/            # Concrete adapters and I/O implementations
│   ├── ai/
│   │   ├── MockInferenceAdapter.ts # Deterministic offline adapter for unit testing
│   │   └── LlamaServerAdapter.ts   # HTTP adapter for local llama-server completions
│   ├── fs/
│   │   ├── FileDiskReader.ts       # Filesystem reader adapter
│   │   └── FileDiskWriter.ts       # Filesystem writer adapter (--output)
│   └── cli/
│       ├── index.ts                # Commander executable composition root
│       └── TerminalDiffFormatter.ts # Colored +/- diff for --diff
│
└── shared/                    # Reusable primitives
    ├── errors/
    │   └── DomainError.ts     # Typed domain and infrastructure errors
    └── types/
        └── Result.ts          # Functional Result<T, E> error handling
```

---

## 2. Getting Started

### Installation
```bash
# Strictly managed via PNPM
pnpm install
```

### Build
```bash
# Compile TypeScript to dist/ with strict type safety
pnpm run build
```

### Execution Modes

#### Offline / Deterministic Testing (Mock Engine)
Does not require any local language model or server running:
```bash
pnpm run dev refactor src/domain/entities/SourceFile.ts --mock
```

#### Local Edge Inference (via llama-server)
Requires `llama-server` running with our GGUF model:
```bash
# Default endpoint: http://127.0.0.1:8080
pnpm run dev refactor src/domain/entities/SourceFile.ts

# Custom endpoint and model name
pnpm run dev refactor src/domain/entities/SourceFile.ts --url http://192.168.6.34:8080 --model Qwen3-Coder-30B
```

### `refactor` options

| Flag | Env var (default source) | Default | Effect |
|------|--------------------------|---------|--------|
| `-m, --mock` | — | off | Deterministic mock engine, no server needed |
| `-u, --url <url>` | `CLEAN_COPILOT_URL`, then `LLAMA_SERVER_URL` | `http://127.0.0.1:8080` | llama-server base URL (`/v1/chat/completions` is appended) |
| `-n, --model <model>` | `CLEAN_COPILOT_MODEL` | `clean-copilot` | Model name sent in the request |
| `-d, --diff` | — | off | Print a colored diff instead of the full code |
| `-o, --output <path>` | — | — | Also write the code to `<path>` (refuses to overwrite the input) |
| `-t, --temperature <number>` | — | `0.1` | Sampling temperature, 0–2 |
| `--max-tokens <number>` | — | `2048` | Generation budget; a reply that hits it fails as truncated (at `-t 0.1` some replies ran to the cap on the local model; `-t 0` stopped on its own in the same test) |
| `--timeout <ms>` | `CLEAN_COPILOT_TIMEOUT_MS` | `300000` | Request timeout; on a CPU-only i5-10310U typical replies took 86–130 s and a full 2048-token reply took 208 s |

### Output contract

| Stream | Content |
|--------|---------|
| stdout | Only the result: the refactored code, or the diff with `--diff` |
| stderr | Banner, settings, status and errors |
| exit code | `0` on success, `1` on any error |

The model answers with prose around fenced code blocks; the CLI keeps only the code inside the fences (joined by a blank line), so `clean-copilot refactor in.ts > out.ts` and `-o out.ts` both get code only. The code is not compiled or checked: review it before use (the model can leave placeholders such as `= /* implementation */;`).
