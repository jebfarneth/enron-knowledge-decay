"""Embed every person-text message with a sentence-transformers model.

Each message's text (see `corpus.build_text`) is encoded by the pinned model
revision into a unit-length vector, so cosine similarity is a dot product.
Messages are encoded in fixed shards saved as they finish; a stamp records
the model, its revision, the text settings, the checksums of the source files
and a hash of every embedded text, and an interrupted run resumes only
while the stamp still matches. A finished run writes:
  data/embeddings.npy   float32 matrix, one row per message, in path order
  data/rows.parquet     the messages' path, headers, sender person and authored text, same order
  data/embeddings.json  the stamp

Usage: uv run python -m enron_search.embed
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Callable

import numpy as np

from .config import load_config
from .corpus import build_text, certified_sources, person_text_messages

Encoder = Callable[[list[str]], np.ndarray]


def load_model(config: dict):
    from sentence_transformers import SentenceTransformer

    settings = config["embedding"]
    return SentenceTransformer(settings["model"], revision=settings["revision"], device="cpu")


def model_encoder(model, batch_size: int) -> Encoder:
    def encode(texts: list[str]) -> np.ndarray:
        return model.encode(texts, batch_size=batch_size, normalize_embeddings=True, convert_to_numpy=True,
                            show_progress_bar=False).astype(np.float32)

    return encode


def text_hash(texts: list[str]) -> str:
    digest = hashlib.sha256()
    for text in texts:
        digest.update(text.encode("utf-8") + b"\0")
    return digest.hexdigest()


def embed_in_shards(texts: list[str], encode: Encoder, shard_dir: Path, shard_size: int, dimensions: int,
                    log: Callable[[str], None] = print) -> np.ndarray:
    """Encode texts shard by shard, reusing shards already saved in shard_dir."""
    shard_dir.mkdir(parents=True, exist_ok=True)
    starts = range(0, len(texts), shard_size)
    begun = time.monotonic()
    encoded = 0
    for number, start in enumerate(starts):
        path = shard_dir / f"shard-{number:04d}.npy"
        expected = (min(shard_size, len(texts) - start), dimensions)
        if path.exists() and np.load(path, mmap_mode="r").shape == expected:
            continue
        vectors = encode(texts[start:start + shard_size])
        if vectors.shape != expected:
            raise RuntimeError(f"shard {number} has shape {vectors.shape}, expected {expected}")
        np.save(path.with_suffix(".tmp.npy"), vectors)
        path.with_suffix(".tmp.npy").rename(path)
        encoded += expected[0]
        elapsed = time.monotonic() - begun
        remaining = len(texts) - start - expected[0]
        log(f"shard {number + 1}/{len(starts)}: {start + expected[0]:,} of {len(texts):,} messages, "
            f"{encoded / elapsed:.0f}/s, about {remaining / (encoded / elapsed) / 60:.0f} min left")
    return np.concatenate([np.load(shard_dir / f"shard-{n:04d}.npy") for n in range(len(starts))])


def main() -> None:
    config = load_config()
    settings, data = config["embedding"], config["paths"]["data"]
    sources = certified_sources(config["paths"]["source"])
    rows = person_text_messages(config["paths"]["source"])
    texts = [build_text(s, a, settings["max_chars"]) for s, a in zip(rows["subject"], rows["authored"])]
    stamp = {
        "model": settings["model"], "revision": settings["revision"], "dimensions": settings["dimensions"],
        "max_chars": settings["max_chars"], "normalized": True, "messages": len(texts),
        "text_sha256": text_hash(texts), "sources": sources,
    }
    shard_dir, stamp_path = data / "shards", data / "embeddings.json"
    progress = shard_dir / "stamp.json"
    if progress.exists() and json.loads(progress.read_text()) != stamp:
        print("settings or sources changed since the saved shards; starting over")
        shutil.rmtree(shard_dir)
    shard_dir.mkdir(parents=True, exist_ok=True)
    progress.write_text(json.dumps(stamp, indent=2))

    print(f"embedding {len(texts):,} messages with {settings['model']}")
    encode = model_encoder(load_model(config), settings["batch_size"])
    vectors = embed_in_shards(texts, encode, shard_dir, settings["shard_size"], settings["dimensions"])
    np.save(data / "embeddings.npy", vectors)
    rows.to_parquet(data / "rows.parquet", index=False)
    stamp["embeddings_sha256"] = hashlib.sha256(vectors.tobytes()).hexdigest()
    stamp_path.write_text(json.dumps(stamp, indent=2))
    shutil.rmtree(shard_dir)
    print(f"wrote {vectors.shape[0]:,} x {vectors.shape[1]} embeddings")


if __name__ == "__main__":
    main()
