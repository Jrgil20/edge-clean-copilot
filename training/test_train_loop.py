"""Regression test for train_loop warmup and gradient accumulation (skipped without torch)."""
import importlib.util
import types
import unittest
from pathlib import Path

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None

SCRIPT = Path(__file__).parent / "train_lora.py"


@unittest.skipIf(torch is None, "torch is not installed")
class TrainLoopTest(unittest.TestCase):
    def test_warmup_ramps_lr_and_counts_partial_group(self):
        spec = importlib.util.spec_from_file_location("train_lora", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Toy(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.w = torch.nn.Parameter(torch.tensor(1.0))

            def forward(self, input_ids, attention_mask, labels):
                return types.SimpleNamespace(loss=(self.w * input_ids.float().mean() - labels.float().mean()) ** 2)

        batches = [
            {"input_ids": torch.ones(1, 3), "attention_mask": torch.ones(1, 3), "labels": torch.zeros(1, 3)}
            for _ in range(5)
        ]
        model = Toy()
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.1, weight_decay=0.01)
        lrs = []
        optimizer.register_step_pre_hook(lambda opt, args, kwargs: lrs.append(opt.param_groups[0]["lr"]))

        module.train_loop(
            model=model, dataloader=batches, optimizer=optimizer, device="cpu",
            epochs=2, grad_accum=2, warmup_ratio=0.5,
        )

        self.assertEqual(len(lrs), 6)  # ceil(5 / 2) steps per epoch, 2 epochs
        self.assertAlmostEqual(lrs[0], 0.1 / 3, places=4)
        self.assertAlmostEqual(lrs[2], 0.1, places=4)
        self.assertTrue(all(abs(lr - 0.1) < 1e-9 for lr in lrs[2:]))


if __name__ == "__main__":
    unittest.main()
