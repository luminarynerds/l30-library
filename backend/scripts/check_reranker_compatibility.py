"""Exercise the reranker API with a tiny local random model; no weight downloads.

This verifies loading and prediction compatibility, not ranking quality.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import CrossEncoder
from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast


def main() -> None:
    torch.set_num_threads(1)
    with tempfile.TemporaryDirectory(prefix="l30-reranker-check-") as directory:
        model_path = Path(directory)
        vocabulary = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "library", "book", "story"]
        vocab_file = model_path / "vocab.txt"
        vocab_file.write_text("\n".join(vocabulary) + "\n")
        tokenizer = BertTokenizerFast(vocab_file=str(vocab_file), do_lower_case=True)
        tokenizer.save_pretrained(model_path)
        model = BertForSequenceClassification(BertConfig(
            vocab_size=len(vocabulary), hidden_size=8, num_hidden_layers=1,
            num_attention_heads=2, intermediate_size=16, num_labels=1,
        ))
        model.save_pretrained(model_path)
        encoder = CrossEncoder(str(model_path), max_length=32, device="cpu", local_files_only=True)
        scores = encoder.predict(
            [("library", "book"), ("library", "story")],
            activation_fn=None, convert_to_numpy=True,
        )
        assert np.asarray(scores).shape == (2,), np.asarray(scores).shape
        assert np.isfinite(scores).all(), scores
        print("Tiny local CrossEncoder load and prediction passed (not a quality benchmark)")


if __name__ == "__main__":
    main()
