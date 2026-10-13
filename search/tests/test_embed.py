import numpy as np
import pytest

from enron_search.embed import embed_in_shards, text_hash


def fake_encoder(calls):
    def encode(texts):
        calls.append(len(texts))
        vectors = np.array([[len(t), 1.0, 0.0] for t in texts], dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    return encode


def test_shards_cover_every_text_in_order(tmp_path):
    texts = ["a" * n for n in range(1, 8)]
    calls = []
    vectors = embed_in_shards(texts, fake_encoder(calls), tmp_path, shard_size=3, dimensions=3, log=lambda _: None)
    assert calls == [3, 3, 1]
    assert vectors.shape == (7, 3)
    assert np.allclose(vectors[:, 0] / vectors[:, 1], np.arange(1, 8))


def test_an_interrupted_run_resumes_from_saved_shards(tmp_path):
    texts = [f"text {n}" for n in range(10)]
    first = embed_in_shards(texts, fake_encoder([]), tmp_path, shard_size=4, dimensions=3, log=lambda _: None)
    (tmp_path / "shard-0001.npy").unlink()
    calls = []
    again = embed_in_shards(texts, fake_encoder(calls), tmp_path, shard_size=4, dimensions=3, log=lambda _: None)
    assert calls == [4]
    assert np.array_equal(first, again)


def test_a_wrongly_shaped_shard_is_rejected(tmp_path):
    def broken(texts):
        return np.zeros((len(texts), 2), dtype=np.float32)

    with pytest.raises(RuntimeError, match="expected"):
        embed_in_shards(["x", "y"], broken, tmp_path, shard_size=2, dimensions=3, log=lambda _: None)


def test_text_hash_depends_on_boundaries():
    assert text_hash(["ab", "c"]) != text_hash(["a", "bc"])
