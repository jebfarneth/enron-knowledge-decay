import pandas as pd

from enron_importance.dedupe import deduplicate, normalize_subject, restrict_window


def message(path, folder, body="Forecast attached.", message_id=None, date="2001-05-14 23:39", sender="a@enron.com", subject="West desk"):
    return {
        "path": path, "folder": folder, "message_id": message_id,
        "date": pd.Timestamp(date, tz="UTC"), "sender": sender,
        "subject": subject, "body": body,
    }


def test_copies_in_several_folders_collapse_to_the_sent_copy():
    frame = pd.DataFrame([
        message("maildir/a/all_documents/1.", "all_documents", message_id="<1>"),
        message("maildir/a/sent/7.", "sent", message_id="<2>", body="Forecast   attached.\n"),
        message("maildir/a/discussion_threads/3.", "discussion_threads", message_id="<3>", subject="RE: West desk"),
    ])
    kept, stats = deduplicate(frame)
    assert list(kept["folder"]) == ["sent"]
    assert stats == {"duplicate_content": 2, "duplicate_message_id": 0}


def test_same_message_id_is_a_duplicate_even_if_text_differs():
    frame = pd.DataFrame([
        message("maildir/a/inbox/1.", "inbox", message_id="<same>"),
        message("maildir/b/inbox/1.", "inbox", message_id="<same>", body="different rendering"),
    ])
    kept, stats = deduplicate(frame)
    assert len(kept) == 1 and stats["duplicate_message_id"] == 1


def test_different_messages_are_kept():
    frame = pd.DataFrame([
        message("maildir/a/sent/1.", "sent", body="first"),
        message("maildir/a/sent/2.", "sent", body="second"),
        message("maildir/a/sent/3.", "sent", body="first", date="2001-05-15 09:00"),
    ])
    kept, stats = deduplicate(frame)
    assert len(kept) == 3 and stats["duplicate_content"] == 0


def test_window_drops_undated_and_out_of_range_messages():
    frame = pd.DataFrame([
        message("1", "sent", date="1997-12-31 23:00"),
        message("2", "sent", date="1998-01-01 00:00"),
        message("3", "sent", date="2002-12-31 23:59"),
        message("4", "sent", date="2003-01-01 00:00"),
    ])
    frame.loc[len(frame)] = {**message("5", "sent"), "date": pd.NaT}
    kept, stats = restrict_window(frame, "1998-01-01", "2002-12-31")
    assert list(kept["path"]) == ["2", "3"]
    assert stats == {"undated": 1, "outside_window": 2}


def test_subject_prefixes_are_normalized():
    assert normalize_subject("RE: Fw: FWD:  West   desk") == "west desk"
