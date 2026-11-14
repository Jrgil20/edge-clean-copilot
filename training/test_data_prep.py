"""Tests for dataset preparation in train_lora.py: system-prompt folding and completion-only labels.

These run without torch: the helpers under test are pure Python.
"""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "train_lora.py"
spec = importlib.util.spec_from_file_location("train_lora", SCRIPT)
tl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tl)

from recipes.schema import load_recipe  # noqa: E402  (train_lora puts training/ on sys.path)

SYSTEM = {"role": "system", "content": "You are a strict architect."}
USER = {"role": "user", "content": "Refactor this."}
ASSISTANT = {"role": "assistant", "content": "export class A {}"}


class CharTokenizer:
    """Character-level stand-in for a HF tokenizer; can reject the system role like Gemma-2."""

    def __init__(self, rejects_system: bool = False):
        self.rejects_system = rejects_system

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        if self.rejects_system and messages and messages[0]["role"] == "system":
            raise ValueError("System role not supported")
        return "".join(f"<{m['role']}>{m['content']}" for m in messages)

    def encode(self, text, add_special_tokens=False):
        return [ord(c) for c in text]

    def __call__(self, text, truncation=True, max_length=None, add_special_tokens=False):
        ids = [ord(c) for c in text]
        return {"input_ids": ids[:max_length] if truncation and max_length else ids}


class MergeSystemIntoUserTest(unittest.TestCase):
    def test_folds_system_prompt_into_first_user_turn(self):
        merged = tl.merge_system_into_user([SYSTEM, USER, ASSISTANT])
        self.assertEqual([m["role"] for m in merged], ["user", "assistant"])
        self.assertEqual(merged[0]["content"], "You are a strict architect.\n\nRefactor this.")
        self.assertEqual(merged[1], ASSISTANT)

    def test_leaves_messages_without_system_prompt_unchanged(self):
        self.assertEqual(tl.merge_system_into_user([USER, ASSISTANT]), [USER, ASSISTANT])

    def test_does_not_mutate_the_input(self):
        messages = [dict(SYSTEM), dict(USER), dict(ASSISTANT)]
        tl.merge_system_into_user(messages)
        self.assertEqual(messages[1]["content"], "Refactor this.")


class CompletionLabelsTest(unittest.TestCase):
    def test_masks_everything_up_to_and_including_the_template(self):
        self.assertEqual(tl.completion_labels([1, 2, 7, 8, 3, 4], [7, 8]), [-100, -100, -100, -100, 3, 4])

    def test_returns_none_when_the_template_is_missing(self):
        self.assertIsNone(tl.completion_labels([1, 2, 3, 4], [7, 8]))

    def test_returns_none_when_nothing_follows_the_template(self):
        self.assertIsNone(tl.completion_labels([1, 2, 7, 8], [7, 8]))

    def test_without_a_template_every_token_is_a_label(self):
        self.assertEqual(tl.completion_labels([1, 2, 3], None), [1, 2, 3])


class PrepareSamplesTest(unittest.TestCase):
    def test_gemma_style_template_works_when_system_is_merged(self):
        tok = CharTokenizer(rejects_system=True)
        with self.assertRaises(ValueError):
            tl.prepare_samples([{"messages": [SYSTEM, USER, ASSISTANT]}], tok, 4096, "<assistant>", False)
        samples, dropped = tl.prepare_samples([{"messages": [SYSTEM, USER, ASSISTANT]}], tok, 4096, "<assistant>", True)
        self.assertEqual(dropped, 0)
        text = "".join(chr(i) for i in samples[0]["input_ids"])
        self.assertEqual(text, "<user>You are a strict architect.\n\nRefactor this.<assistant>export class A {}")

    def test_keeps_the_system_turn_when_merge_is_off(self):
        samples, dropped = tl.prepare_samples([{"messages": [SYSTEM, USER, ASSISTANT]}], CharTokenizer(), 4096, "<assistant>", False)
        self.assertEqual(dropped, 0)
        self.assertTrue("".join(chr(i) for i in samples[0]["input_ids"]).startswith("<system>You are"))

    def test_labels_cover_only_the_assistant_answer(self):
        samples, _ = tl.prepare_samples([{"messages": [USER, ASSISTANT]}], CharTokenizer(), 4096, "<assistant>", False)
        trained = "".join(chr(i) for i in samples[0]["labels"] if i != -100)
        self.assertEqual(trained, "export class A {}")

    def test_drops_rows_truncated_before_the_answer_instead_of_training_on_the_prompt(self):
        rows = [{"messages": [USER, ASSISTANT]}, {"messages": [{"role": "user", "content": "x" * 50}, ASSISTANT]}]
        samples, dropped = tl.prepare_samples(rows, CharTokenizer(), 40, "<assistant>", False)
        self.assertEqual(dropped, 1)
        self.assertEqual(len(samples), 1)


class RecipeFlagTest(unittest.TestCase):
    def test_gemma_recipe_merges_system_prompt_and_others_do_not(self):
        recipes = Path(__file__).parent / "recipes"
        self.assertTrue(load_recipe(recipes / "gemma-2-2b.yaml").merge_system_prompt)
        self.assertFalse(load_recipe(recipes / "qwen2.5-coder-1.5b.yaml").merge_system_prompt)
        self.assertFalse(load_recipe(recipes / "llama-3.2-3b.yaml").merge_system_prompt)


if __name__ == "__main__":
    unittest.main()
