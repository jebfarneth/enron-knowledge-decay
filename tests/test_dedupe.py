import pandas as pd

from enron_importance.dedupe import deduplicate, flag_shifted_copies, normalize_subject, restrict_window


def message(path, folder, body="Forecast attached.", message_id=None, date="2001-05-14 23:39", sender="a@enron.com",
            subject="West desk", to=("b@enron.com",), cc=()):
    return {
        "path": path, "folder": folder, "message_id": message_id,
        "date": pd.Timestamp(date, tz="UTC"), "sender": sender,
        "subject": subject, "body": body, "to": list(to), "cc": list(cc),
    }


def test_copies_in_several_folders_collapse_to_the_sent_copy():
    frame = pd.DataFrame([
        message("maildir/a/all_documents/1.", "all_documents", message_id="<1>"),
        message("maildir/a/sent/7.", "sent", message_id="<2>", body="Forecast   attached.\n"),
        message("maildir/a/discussion_threads/3.", "discussion_threads", message_id="<3>", subject="RE: West desk"),
    ])
    kept, stats, copies = deduplicate(frame)
    assert list(kept["folder"]) == ["sent"]
    assert stats == {"duplicate_content": 2, "duplicate_message_id": 0, "candidate_separate_sends": 0,
                     "recipient_addresses_only_in_other_copies": 0}
    assert set(copies["kept_path"]) == {"maildir/a/sent/7."} and len(copies) == 2


def test_same_message_id_is_a_duplicate_even_if_text_differs():
    frame = pd.DataFrame([
        message("maildir/a/inbox/1.", "inbox", message_id="<same>"),
        message("maildir/b/inbox/1.", "inbox", message_id="<same>", body="different rendering"),
    ])
    kept, stats, _ = deduplicate(frame)
    assert len(kept) == 1 and stats["duplicate_message_id"] == 1


def test_different_messages_are_kept():
    frame = pd.DataFrame([
        message("maildir/a/sent/1.", "sent", body="first"),
        message("maildir/a/sent/2.", "sent", body="second"),
        message("maildir/a/sent/3.", "sent", body="first", date="2001-05-15 09:00"),
    ])
    kept, stats, _ = deduplicate(frame)
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


def test_missing_sender_and_body_from_parquet_are_handled():
    # Values read back from parquet arrive as NaN, not None or "".
    frame = pd.DataFrame([
        message("maildir/a/inbox/1.", "inbox", body=float("nan"), sender=float("nan"), subject=float("nan")),
        message("maildir/a/inbox/2.", "inbox", body=float("nan"), sender=float("nan"), subject=float("nan")),
    ])
    kept, stats, _ = deduplicate(frame)
    assert len(kept) == 1 and stats["duplicate_content"] == 1


def test_same_text_to_disjoint_distributions_is_two_sends():
    frame = pd.DataFrame([
        message("maildir/bass-e/sent/69.", "sent", body="http://short.url", to=["jim.schwieger@enron.com"]),
        message("maildir/bass-e/sent/70.", "sent", body="http://short.url", to=["x@enron.com", "y@enron.com"]),
        message("maildir/bass-e/_sent_mail/5.", "_sent_mail", body="http://short.url", to=["x@enron.com", "y@enron.com"]),
        message("maildir/x/inbox/1.", "inbox", body="http://short.url", to=[]),
    ])
    kept, stats, copies = deduplicate(frame)
    assert sorted(kept["path"]) == ["maildir/bass-e/sent/69.", "maildir/bass-e/sent/70."]
    assert stats["candidate_separate_sends"] == 1
    assert copies.set_index("path").loc["maildir/bass-e/_sent_mail/5.", "kept_path"] == "maildir/bass-e/sent/70."


def test_whole_hour_shifted_copies_are_flagged_not_removed():
    body = "Please review the attached turbine contract before Friday's call with the lenders. " * 2
    frame = pd.DataFrame([
        message("maildir/salisbury-h/inbox/1079.", "inbox", body=body, date="2001-06-11 23:23:06"),
        message("maildir/williams-w3/sent_items/512.", "sent_items", body=body, date="2001-06-12 02:23:06"),
        message("maildir/a/sent/9.", "sent", body=body, date="2001-06-12 02:23:07"),     # not whole hours
        message("maildir/a/sent/10.", "sent", body=body, date="2001-06-13 02:23:06"),    # a day later
        message("maildir/a/sent/11.", "sent", body="short", date="2001-06-11 01:00"),
        message("maildir/a/sent/12.", "sent", body="short", date="2001-06-11 04:00"),   # too short to judge
    ])
    flags = flag_shifted_copies(frame, max_hours=8, min_chars=100)
    assert flags.iloc[1] == "maildir/salisbury-h/inbox/1079."
    assert flags.drop(index=1).isna().all()


def test_recipients_only_other_copies_list_are_kept_apart():
    frame = pd.DataFrame([
        message("maildir/haedicke-m/california/3.", "california", to=["f..carla@enron.com", "ray@enron.com"]),
        message("maildir/williams-w3/bill_williams_iii/874.", "bill_williams_iii", to=["f..calger@enron.com", "ray@enron.com"]),
    ])
    kept, stats, _ = deduplicate(frame)
    assert len(kept) == 1 and list(kept.iloc[0]["to"]) == ["f..carla@enron.com", "ray@enron.com"]
    assert list(kept.iloc[0]["to_extra"]) == ["f..calger@enron.com"]
    assert stats["recipient_addresses_only_in_other_copies"] == 1


def test_send_grouping_does_not_depend_on_copy_order():
    rows = [message(f"maildir/a/{f}/{i}.", f, to=to) for i, (f, to) in
            enumerate([("sent", ["b@enron.com"]), ("inbox", ["c@enron.com"]), ("all_documents", ["b@enron.com", "c@enron.com"])])]
    for order in (rows, rows[::-1], [rows[1], rows[2], rows[0]]):
        kept, stats, _ = deduplicate(pd.DataFrame(order))
        assert len(kept) == 1 and stats["candidate_separate_sends"] == 0


def test_message_id_duplicates_point_at_a_kept_message():
    frame = pd.DataFrame([
        message("maildir/a/sent/1.", "sent", body="same", message_id="<x>"),
        message("maildir/a/inbox/2.", "inbox", body="same", message_id="<y>"),       # content copy of 1
        message("maildir/a/inbox/3.", "inbox", body="different", message_id="<y>"),  # same ID as the removed copy
    ])
    kept, stats, copies = deduplicate(frame)
    assert set(copies["kept_path"]) <= set(kept["path"])


def test_cc_addresses_only_other_copies_list_are_kept_apart():
    frame = pd.DataFrame([
        message("maildir/a/sent/1.", "sent", to=["b@enron.com"], cc=["c@enron.com"]),
        message("maildir/a/inbox/2.", "inbox", to=["b@enron.com"], cc=["d@enron.com"]),
    ])
    kept, _, _ = deduplicate(frame)
    assert list(kept.iloc[0]["cc"]) == ["c@enron.com"] and list(kept.iloc[0]["cc_extra"]) == ["d@enron.com"]


def test_a_copy_whose_keeper_was_removed_points_to_the_final_kept_message():
    frame = pd.DataFrame([
        message("maildir/a/sent/1.", "sent", body="body A", message_id="<1>"),
        message("maildir/a/inbox/2.", "inbox", body="body B", message_id="<1>", to=["b@enron.com"]),
        message("maildir/a/inbox/3.", "inbox", body="body B", message_id="<2>", to=["b@enron.com", "z@enron.com"]),
    ])
    kept, _, copies = deduplicate(frame)
    assert set(copies["kept_path"]) <= set(kept["path"])
