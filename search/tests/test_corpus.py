import json

import pandas as pd
import pytest

from enron_search.corpus import build_text, certified_sources, person_text_messages, sha256_of, strip_prefixes


def write_run(tmp_path, messages, people, tamper=False):
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    messages.to_parquet(processed / "messages.parquet", index=False)
    people.to_parquet(processed / "sender_people.parquet", index=False)
    outputs = {f"processed/{name}": sha256_of(processed / name) for name in ("messages.parquet", "sender_people.parquet")}
    if tamper:
        outputs["processed/messages.parquet"] = "0" * 64
    manifest = {"stages": {"prepare": {"outputs": {"processed/messages.parquet": outputs["processed/messages.parquet"]}},
                           "identity": {"outputs": {"processed/sender_people.parquet":
                                                    outputs["processed/sender_people.parquet"]}}}}
    (processed / "manifest.json").write_text(json.dumps(manifest))
    return processed


def message(path, subject="s", authored="text"):
    return {"path": path, "message_id": f"<{path}>", "date": pd.Timestamp("2001-05-01", tz="UTC"),
            "sender": f"{path}@enron.com", "subject": subject, "authored": authored, "custodian": "c", "folder": "f",
            "analysis": True}


MESSAGES = pd.DataFrame([message("b/1"), message("a/2"), message("c/3")])
PEOPLE = pd.DataFrame({"path": ["a/2", "b/1", "c/3"], "sender_person": ["ann", "bob", "carl"],
                       "person_text": [True, True, False]})


def test_only_person_text_messages_in_path_order(tmp_path):
    rows = person_text_messages(write_run(tmp_path, MESSAGES, PEOPLE))
    assert rows["path"].tolist() == ["a/2", "b/1"]
    assert rows["sender_person"].tolist() == ["ann", "bob"]
    assert "person_text" not in rows and "analysis" not in rows


def test_sources_must_match_the_certified_run(tmp_path):
    processed = write_run(tmp_path, MESSAGES, PEOPLE)
    assert set(certified_sources(processed)) == {"processed/messages.parquet", "processed/sender_people.parquet"}
    with pytest.raises(RuntimeError, match="differs from the certified run"):
        certified_sources(write_run(tmp_path / "x", MESSAGES, PEOPLE, tamper=True))


def test_reply_and_forward_prefixes_are_stripped():
    assert strip_prefixes("RE: Fw: re[2]: Gas curves") == "Gas curves"
    assert strip_prefixes("FWD:RE:") == ""
    assert strip_prefixes("Reply needed") == "Reply needed"
    assert strip_prefixes(None) == ""


def test_text_is_subject_then_collapsed_body_cut_to_length():
    assert build_text("Re: Storage", "Please send\n\n  the   numbers.", 100) == "Storage Please send the numbers."
    assert build_text("", "Thanks", 100) == "Thanks"
    assert build_text("Budget", None, 100) == "Budget"
    assert build_text("abc", "defgh", 6) == "abc de"
