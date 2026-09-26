import io
import json
import tarfile

import pandas as pd

from enron_importance.prepare import prepare

ORIGINAL = b"""Message-ID: <1>
Date: Tue, 1 May 2001 09:00:00 -0500
From: kay.mann@enron.com
To: mark.taylor@enron.com
Subject: Turbine contract

Can you review section 4 of the turbine contract?
"""
COPY = ORIGINAL.replace(b"<1>", b"<2>")
REPLY = b"""Message-ID: <3>
Date: Tue, 1 May 2001 10:30:00 -0500
From: mark.taylor@enron.com
To: kay.mann@enron.com
Subject: RE: Turbine contract

Section 4 is fine.

 -----Original Message-----
From: Mann, Kay
Sent: Tuesday, May 01, 2001 9:00 AM
To: Taylor, Mark
Subject: Turbine contract

Can you review section 4 of the turbine contract?
"""
OLD = ORIGINAL.replace(b"2001", b"1985").replace(b"<1>", b"<4>")


def build(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    archive = raw / "corpus.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, data in [("maildir/mann-k/sent/1.", ORIGINAL), ("maildir/mann-k/all_documents/9.", COPY),
                           ("maildir/taylor-m/sent/1.", REPLY), ("maildir/mann-k/sent/2.", OLD)]:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    import hashlib
    return {
        "corpus": {"url": "unused", "filename": "corpus.tar.gz", "bytes": archive.stat().st_size,
                   "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
        "paths": {"raw": raw, "interim": tmp_path / "interim", "processed": tmp_path / "processed"},
        "ingest": {"start": "1998-01-01", "end": "2002-12-31"},
        "dedupe": {"max_shift_hours": 8, "min_body_chars": 100},
        "senders": {"internal_domain": "enron.com", "min_messages": 50, "feed_share": 0.9, "top_templates": 3, "routine_repeats": 10, "speech_act_words": 4},
        "threads": {"max_reply_days": 14},
    }


def test_end_to_end_funnel(tmp_path):
    manifest = prepare(build(tmp_path))
    funnel = manifest["funnel"]
    assert funnel["parsed_files"] == 4
    assert funnel["dropped_outside_window"] == 1
    assert funnel["dropped_duplicate_content"] == 1
    assert funnel["unique_messages"] == 2
    assert funnel["analysis_messages"] == 2
    messages = pd.read_parquet(tmp_path / "processed" / "messages.parquet")
    reply = messages[messages["sender"] == "mark.taylor@enron.com"].iloc[0]
    assert reply["authored"] == "Section 4 is fine."
    saved = json.loads((tmp_path / "processed" / "manifest.json").read_text())["stages"]["prepare"]
    assert set(saved["outputs"]) == {"interim/messages_raw.parquet", "processed/messages.parquet", "processed/senders.parquet",
                                     "processed/copies.parquet", "processed/funnel.json"}


def test_cached_parse_still_verifies_the_archive(tmp_path):
    import pytest
    config = build(tmp_path)
    prepare(config)
    archive = tmp_path / "raw" / "corpus.tar.gz"
    archive.write_bytes(b"truncated archive")
    with pytest.raises(SystemExit):
        prepare(config)


def test_cache_is_rebuilt_when_its_stamp_does_not_match(tmp_path):
    config = build(tmp_path)
    prepare(config)
    stamp = tmp_path / "interim" / "messages_raw.json"
    stamp.write_text('{"corpus_sha256": "other", "parser_sha256": "other"}')
    manifest = prepare(config)
    assert manifest["funnel"]["parsed_files"] == 4
    assert json.loads(stamp.read_text())["corpus_sha256"] == config["corpus"]["sha256"]


def test_an_altered_parsed_cache_is_rebuilt(tmp_path):
    config = build(tmp_path)
    prepare(config)
    table = tmp_path / "interim" / "messages_raw.parquet"
    pd.read_parquet(table).head(1).assign(body="POISONED CACHE TEXT").to_parquet(table, index=False)
    assert prepare(config)["funnel"]["parsed_files"] == 4


def test_cache_is_rebuilt_when_the_python_or_lockfile_stamp_differs(tmp_path):
    import sys

    from enron_importance.download import sha256_of
    from enron_importance.provenance import PACKAGE
    config = build(tmp_path)
    prepare(config)
    stamp_path = tmp_path / "interim" / "messages_raw.json"
    stamp = json.loads(stamp_path.read_text())      # the stamp holds the real versions, not placeholders
    assert stamp["python"] == sys.version.split()[0]
    assert stamp["uv_lock_sha256"] == sha256_of(PACKAGE.parents[1] / "uv.lock")
    for field in ["python", "uv_lock_sha256"]:
        stamp = json.loads(stamp_path.read_text())
        stamp[field] = "different"
        stamp_path.write_text(json.dumps(stamp))
        prepare(config)
        assert json.loads(stamp_path.read_text())[field] != "different"


def test_stale_reasons_catch_configuration_and_output_changes(tmp_path):
    from enron_importance.provenance import stale_reasons
    config = build(tmp_path)
    prepare(config)
    assert stale_reasons(config, ["prepare"]) == []
    (tmp_path / "processed" / "senders.parquet").write_bytes(b"altered")
    config["senders"]["routine_repeats"] = 11
    reasons = stale_reasons(config, ["prepare"])
    assert "prepare: built with a different configuration" in reasons
    assert any("senders.parquet" in r for r in reasons)
