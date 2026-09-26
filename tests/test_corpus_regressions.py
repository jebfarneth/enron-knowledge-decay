"""Real-corpus cases from the 2026-09-25 audits, checked against the generated data.

Run after the pipeline (`make regress`). Skipped only when data/processed
holds no files at all; otherwise fails unless the stage manifest certifies
one complete run by the current code and configuration with every output
unchanged (provenance.py), so old or mixed outputs cannot certify new code. Each case is a message or
address the audits showed an earlier pipeline got wrong, and every case must
be present.
"""

import pandas as pd
import pytest

from enron_importance.config import load_config
from enron_importance.provenance import stale_reasons

CONFIG = load_config()
PROCESSED = CONFIG["paths"]["processed"]
BUILT = PROCESSED.exists() and any(PROCESSED.iterdir())
# Skip only on a checkout where nothing has been built; once any file exists, every check must run.
pytestmark = [pytest.mark.corpus, pytest.mark.skipif(not BUILT, reason="generated data not built")]


def test_generated_data_is_complete_and_current():
    reasons = stale_reasons(CONFIG)
    assert not reasons, f"generated data is not one current run: {reasons}; rerun the pipeline"


@pytest.fixture(scope="module")
def messages():
    columns = ["path", "sender", "automated", "structured", "routine", "signature_only", "analysis"]
    frame = pd.read_parquet(PROCESSED / "messages.parquet", columns=columns)
    frame = frame.merge(pd.read_parquet(PROCESSED / "sender_people.parquet"), on="path")
    return frame.merge(pd.read_parquet(PROCESSED / "links.parquet"), on="path").set_index("path", drop=False)


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


def test_mark_dana_davis_is_dana_davis(messages):
    assert messages.loc["maildir/benson-r/deleted_items/89.", "sender_person"] == "dana davis"


def test_title_suffixes_and_rooms_do_not_become_people(messages):
    assert messages.loc["maildir/salisbury-h/read/297.", "sender_person"] == "george wasaff"
    assert messages.loc["maildir/salisbury-h/read/314.", "sender_person"] == "robert knight"
    types = pd.read_parquet(PROCESSED / "person_types.parquet").set_index("person_key")["entity_type"]
    assert types[messages.loc["maildir/may-l/calendar/1.", "sender_person"]] == "role"


def test_pete_davis_bug_reports_are_kept(messages):
    for path in ["maildir/guzman-m/notes_inbox/1236.", "maildir/guzman-m/notes_inbox/1255."]:
        assert not messages.loc[path, "automated"], path


def test_calendar_entries_are_structured_records(messages):
    for path in ["maildir/blair-l/meetings/100.", "maildir/nemec-g/notes_inbox/2242."]:
        assert messages.loc[path, "structured"], path


def test_repeated_approvals_stay_in_text_analysis(messages):
    assert messages.loc["maildir/donoho-l/deleted_items/101.", "analysis"]


def test_long_messages_do_not_pass_as_speech_acts(messages):
    for path in ["maildir/baughman-d/inbox/304.", "maildir/benson-r/inbox/116.", "maildir/causholli-m/deleted_items/106."]:
        assert not (messages.loc[path, "routine"] and messages.loc[path, "analysis"]), path


def test_separate_sends_of_one_text_are_both_kept(messages):
    assert {"maildir/bass-e/sent/69.", "maildir/bass-e/sent/70."} <= set(messages.index)


def test_audited_wrong_parents_are_not_linked(messages):
    for child, wrong in [("maildir/hodge-j/deleted_items/466.", "maildir/heard-m/inbox/255."),
                         ("maildir/kaminski-v/var/2.", "maildir/kaminski-v/sent/8.")]:
        assert messages.loc[child, "parent_path"] != wrong, child


# Audit 4 (2026-09-26) cases.

def test_a_wrapped_plain_recipient_line_ends_the_quoted_header():
    authored = pd.read_parquet(PROCESSED / "messages.parquet", columns=["path", "authored"]).set_index("path")["authored"]
    text = authored["maildir/jones-t/notes_inbox/964."]
    assert text.startswith("I know nothing!") and "Aronowitz" not in text and "To:" not in text


def test_answers_and_tables_are_not_signature_only(messages):
    for path in ["maildir/jones-t/notes_inbox/3821.", "maildir/zufferli-j/sent_items/98."]:
        assert not messages.loc[path, "signature_only"], path


def test_a_second_spelling_of_a_recipient_is_not_added(messages):
    from enron_importance.network import network_messages
    row = network_messages(CONFIG).set_index("path").loc["maildir/forney-j/sent_items/96."]
    assert row["recipient_extra"] == []


def test_reply_parents_follow_the_first_quoted_author(messages):
    def parent_sender(path):
        parent = messages.loc[path, "parent_path"]
        return messages.loc[parent, "sender_person"] if isinstance(parent, str) else None

    assert parent_sender("maildir/lavorato-j/sent_items/591.") != "kevin presto"            # quotes Louise first
    assert parent_sender("maildir/kaminski-v/stanford/7.") != "christie patrick"             # relays Susan's message
    assert pd.isna(messages.loc["maildir/kitchen-l/_americas/netco_legal/46.", "parent_path"])  # quotes its own sender
