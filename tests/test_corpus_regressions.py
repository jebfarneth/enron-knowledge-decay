"""Real-corpus cases from the 2026-09-25 audit, checked against the generated data.

Skipped when data/processed has not been built. Each case is a message or
address the audit showed the earlier pipeline got wrong.
"""

import pandas as pd
import pytest

from enron_importance.config import load_config

PROCESSED = load_config()["paths"]["processed"]
pytestmark = pytest.mark.skipif(not (PROCESSED / "sender_people.parquet").exists(), reason="generated data not built")


@pytest.fixture(scope="module")
def messages():
    columns = ["path", "sender", "automated", "structured", "analysis", "reply_to"]
    frame = pd.read_parquet(PROCESSED / "messages.parquet", columns=columns)
    return frame.merge(pd.read_parquet(PROCESSED / "sender_people.parquet"), on="path").set_index("path", drop=False)


@pytest.fixture(scope="module")
def identities():
    return pd.read_parquet(PROCESSED / "identities.parquet").set_index("address")


def test_placeholder_mail_is_not_don_millers(messages, identities):
    assert identities.loc["no.address@enron.com", "entity_type"] == "placeholder"
    for path in ["maildir/arnold-j/inbox/31.", "maildir/arnold-j/inbox/41.", "maildir/arora-h/inbox/67."]:
        assert messages.loc[path, "sender_person"] != "don miller", path


def test_numbered_temp_mailboxes_stay_separate(identities):
    keys = identities.loc[["legal.1@enron.com", "legal.2@enron.com", "legal.7@enron.com"], "person_key"]
    assert keys.nunique() == 3 and (identities.loc[keys.index, "entity_type"] == "role").all()


def test_mark_a_and_mark_e_taylor_are_two_people(identities):
    assert identities.loc[".taylor@enron.com", "person_key"] == "mark e taylor"
    assert identities.loc["a.taylor@enron.com", "person_key"] == "mark a taylor"


def test_albert_and_bert_meyers_are_one_person(identities):
    assert identities.loc["albert.meyers@enron.com", "person_key"] == identities.loc["bert.meyers@enron.com", "person_key"]


def test_pete_davis_bug_reports_are_kept(messages):
    for path in ["maildir/guzman-m/notes_inbox/1236.", "maildir/guzman-m/notes_inbox/1255."]:
        if path in messages.index:
            assert not messages.loc[path, "automated"], path


def test_calendar_entries_are_structured_records(messages):
    assert messages.loc["maildir/blair-l/meetings/100.", "structured"]


def test_repeated_approvals_stay_in_text_analysis(messages):
    assert messages.loc["maildir/donoho-l/deleted_items/101.", "analysis"]


def test_separate_sends_of_one_text_are_both_kept(messages):
    assert {"maildir/bass-e/sent/69.", "maildir/bass-e/sent/70."} <= set(messages.index)


def test_audited_wrong_parents_are_not_linked(messages):
    rows = messages.reset_index(drop=True)
    parent = rows["reply_to"].map(lambda i: rows.at[int(i), "path"] if pd.notna(i) else None)
    parent.index = rows["path"]
    for child, wrong in [("maildir/hodge-j/deleted_items/466.", "maildir/heard-m/inbox/255."),
                         ("maildir/kaminski-v/var/2.", "maildir/kaminski-v/sent/8."),
                         ("maildir/guzman-m/notes_inbox/581.", "maildir/guzman-m/notes_inbox/582.")]:
        if child in parent.index:
            assert parent[child] != wrong, child
