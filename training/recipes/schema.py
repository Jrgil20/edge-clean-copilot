"""Model Recipe Schema & Loader for Edge Clean Copilot

Provides a strongly-typed specification for foundational SLMs, abstracting
Hugging Face model IDs, LoRA target modules, precision dtypes, tokenization
response templates, and training hyperparameters away from train_lora.py.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import json
import sys

# Optional PyYAML support with graceful fallback
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class ModelRecipe:
    """Strongly-typed declarative recipe for fine-tuning an open-weight foundation SLM."""
    
    # Foundational Model Identity
    model_id: str
    architecture_family: str
    description: str = ""
    
    # LoRA Hyperparameters
    target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"
    ])
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    bias: str = "none"
    task_type: str = "CAUSAL_LM"
    
    # Tokenization & Loss Masking
    response_template: Optional[str] = None
    max_seq_len: int = 2048
    trust_remote_code: bool = True
    
    # Precision & Execution
    torch_dtype: str = "bfloat16"  # "bfloat16", "float16", "float32"
    device_map: str = "auto"
    
    # Training Defaults
    learning_rate: float = 2e-4
    batch_size: int = 2
    grad_accum_steps: int = 4
    num_train_epochs: int = 3
    warmup_ratio: float = 0.05
    weight_decay: float = 0.01
    
    # Hardware & Edge Quantization Hints
    recommended_quant: str = "Q4_K_M"
    target_vram_gb: float = 8.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes recipe to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelRecipe":
        """Instantiates a ModelRecipe from a dictionary, filtering unknown keys."""
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


def load_recipe(recipe_path: Union[str, Path]) -> ModelRecipe:
    """Loads a ModelRecipe from a YAML or JSON file path."""
    path = Path(recipe_path)
    if not path.exists():
        raise FileNotFoundError(f"[ERROR] Recipe file not found: {path.resolve()}")
    
    suffix = path.suffix.lower()
    raw_text = path.read_text(encoding="utf-8")
    
    if suffix in [".yaml", ".yml"]:
        if not HAS_YAML:
            raise ImportError(
                f"[ERROR] PyYAML is not installed to parse '{path.name}'. "
                f"Please install PyYAML ('pnpm dlx' / pip install pyyaml) or provide a .json recipe."
            )
        data = yaml.safe_load(raw_text)
    elif suffix == ".json":
        data = json.loads(raw_text)
    else:
        # Attempt JSON first, then YAML
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            if HAS_YAML:
                data = yaml.safe_load(raw_text)
            else:
                raise ValueError(
                    f"[ERROR] Unsupported recipe format '{suffix}'. Supported: .yaml, .yml, .json"
                )
    
    if not isinstance(data, dict):
        raise ValueError(f"[ERROR] Recipe file '{path.name}' must contain a key-value mapping.")
    
    if "model_id" not in data or "architecture_family" not in data:
        raise ValueError(
            f"[ERROR] Recipe '{path.name}' is missing mandatory fields: 'model_id' and 'architecture_family'."
        )
    
    return ModelRecipe.from_dict(data)
