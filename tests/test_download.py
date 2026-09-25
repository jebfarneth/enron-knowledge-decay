import hashlib

import pytest

from enron_importance.download import ensure_corpus, sha256_of


def make_config(tmp_path, content: bytes, sha256):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "corpus.tar.gz").write_bytes(content)
    return {
        "corpus": {"url": "unused", "filename": "corpus.tar.gz", "bytes": len(content), "sha256": sha256},
        "paths": {"raw": raw},
    }


def test_sha256_matches_hashlib(tmp_path):
    path = tmp_path / "file"
    path.write_bytes(b"enron" * 1000)
    assert sha256_of(path) == hashlib.sha256(b"enron" * 1000).hexdigest()


def test_verified_corpus_is_returned(tmp_path):
    content = b"fixture corpus"
    config = make_config(tmp_path, content, hashlib.sha256(content).hexdigest())
    assert ensure_corpus(config).name == "corpus.tar.gz"


def test_checksum_mismatch_stops_the_pipeline(tmp_path):
    config = make_config(tmp_path, b"tampered", "0" * 64)
    with pytest.raises(SystemExit, match="SHA-256 mismatch"):
        ensure_corpus(config)


def test_size_mismatch_stops_the_pipeline(tmp_path):
    config = make_config(tmp_path, b"short", hashlib.sha256(b"short").hexdigest())
    config["corpus"]["bytes"] = 999
    with pytest.raises(SystemExit, match="expected 999 bytes"):
        ensure_corpus(config)
