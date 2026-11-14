# CLI de Edge Clean Copilot

> Espejo en español de [`cli/README.md`](../../cli/README.md).

Interfaz de línea de comandos de **Edge Clean Copilot**. Implementa la **arquitectura de puertos y adaptadores (hexagonal)** para desacoplar por completo la lógica de negocio del núcleo de los motores locales de inferencia de modelos de lenguaje.

---

## 1. Capas arquitectónicas

```
proyecto/cli/src/
├── domain/                    # Lógica de negocio pura e invariantes
│   └── entities/
│       └── SourceFile.ts      # Valida tamaño, extensión e inmutabilidad del archivo
│
├── application/               # Orquestación de la aplicación e interfaces
│   ├── dtos/
│   │   └── RefactorDTO.ts     # Transferencia de datos de entrada y salida en la frontera
│   ├── ports/
│   │   └── IInferenceEngine.ts # Contrato del puerto de salida para la inferencia
│   ├── services/
│   │   └── extractCodeBlocks.ts # Conserva solo el código entre fences de la respuesta del modelo
│   └── use-cases/
│       └── RefactorCodeUseCase.ts # Orquesta la verificación del dominio y la inferencia
│
├── infrastructure/            # Adaptadores concretos e implementaciones de E/S
│   ├── ai/
│   │   ├── MockInferenceAdapter.ts # Adaptador determinista sin conexión para pruebas
│   │   └── LlamaServerAdapter.ts   # Adaptador HTTP para completions de llama-server local
│   ├── fs/
│   │   ├── FileDiskReader.ts       # Adaptador de lectura del sistema de archivos
│   │   └── FileDiskWriter.ts       # Adaptador de escritura del sistema de archivos (--output)
│   └── cli/
│       ├── index.ts                # Raíz de composición del ejecutable (commander)
│       └── TerminalDiffFormatter.ts # Diff +/- con colores para --diff
│
└── shared/                    # Primitivas reutilizables
    ├── errors/
    │   └── DomainError.ts     # Errores tipados de dominio e infraestructura
    └── types/
        └── Result.ts          # Manejo funcional de errores con Result<T, E>
```

---

## 2. Primeros pasos

### Instalación
```bash
# Se gestiona exclusivamente con PNPM
pnpm install
```

### Compilación
```bash
# Compila TypeScript a dist/ con tipado estricto
pnpm run build
```

### Modos de ejecución

#### Pruebas sin conexión y deterministas (motor simulado)
No requiere ningún modelo de lenguaje ni servidor en ejecución:
```bash
pnpm run dev refactor src/domain/entities/SourceFile.ts --mock
```

#### Inferencia local en el borde (con llama-server)
Requiere `llama-server` en ejecución con nuestro modelo GGUF:
```bash
# Endpoint por defecto: http://127.0.0.1:8080
pnpm run dev refactor src/domain/entities/SourceFile.ts

# Endpoint y nombre de modelo personalizados
pnpm run dev refactor src/domain/entities/SourceFile.ts --url http://192.168.6.34:8080 --model Qwen3-Coder-30B
```

### Opciones de `refactor`

| Opción | Variable de entorno (origen del valor por defecto) | Por defecto | Efecto |
|--------|-----------------------------------------------------|-------------|--------|
| `-m, --mock` | — | desactivado | Motor simulado determinista; no necesita servidor |
| `-u, --url <url>` | `CLEAN_COPILOT_URL`, luego `LLAMA_SERVER_URL` | `http://127.0.0.1:8080` | URL base de llama-server (se agrega `/v1/chat/completions`) |
| `-n, --model <model>` | `CLEAN_COPILOT_MODEL` | `clean-copilot` | Nombre del modelo que se envía en la petición |
| `-d, --diff` | — | desactivado | Muestra un diff con colores en lugar del código completo |
| `-o, --output <path>` | — | — | Además escribe el código en `<path>` (se niega a sobrescribir la entrada) |
| `-t, --temperature <number>` | — | `0.1` | Temperatura de muestreo, entre 0 y 2 |
| `--max-tokens <number>` | — | `2048` | Presupuesto de generación; una respuesta que lo alcanza falla como truncada (con `-t 0.1` algunas respuestas del modelo local llegaron al tope; con `-t 0` se detuvo sola en la misma prueba) |
| `--timeout <ms>` | `CLEAN_COPILOT_TIMEOUT_MS` | `300000` | Tiempo máximo de la petición; en un i5-10310U solo con CPU, con una entrada de 14 líneas, las respuestas tardaron 86–130 s y una respuesta completa de 2048 tokens tardó 208 s |

### Contrato de salida

| Flujo | Contenido |
|-------|-----------|
| stdout | Solo el resultado: el código refactorizado, o el diff con `--diff` |
| stderr | Banner, configuración, estado y errores |
| código de salida | `0` si tiene éxito, `1` ante cualquier error |

El modelo responde con prosa alrededor de bloques de código con fences; el CLI conserva solo el código dentro de los fences (unidos por una línea en blanco), así que tanto `clean-copilot refactor in.ts > out.ts` como `-o out.ts` reciben solo código. El código no se compila ni se verifica: revíselo antes de usarlo (el modelo puede dejar marcadores como `= /* implementation */;`).
