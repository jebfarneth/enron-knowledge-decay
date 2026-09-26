import pandas as pd

import pytest

from enron_importance import mentions as mentions_module
from enron_importance.mentions import (Distances, cached_mentions, compatible, mention_centrality, mention_links,
                                       mention_measures, name_index, nil_reason, tag_mentions, tagger_id)

PEOPLE = {"jeffrey skilling", "jeffrey dasovich", "mark e taylor", "kay mann", "sara shackleton", "jonah self"}


def test_mentions_match_full_first_last_nickname_and_initials():
    index = name_index(PEOPLE)
    assert compatible("Jeff", index) == {"jeffrey skilling", "jeffrey dasovich"}
    assert compatible("Skilling", index) == {"jeffrey skilling"}
    assert compatible("Jeff Skilling", index) == {"jeffrey skilling"}
    assert compatible("J.S.", index) == {"jeffrey skilling", "jonah self"}
    assert compatible("Kay's", index) == {"kay mann"}
    assert compatible("Nobody", index) == set()
    assert compatible("Mark Taylor", index) == {"mark e taylor"}   # initialled keys are indexed by first and last name


def graph(pairs):
    return Distances(pd.DataFrame(pairs, columns=["source", "target"]))


def test_the_candidate_closest_to_both_sender_and_recipient_wins_and_ties_abstain():
    # skilling is one hop from both kay and sara; dasovich is two hops from kay.
    distances = graph([("kay mann", "jeffrey skilling"), ("sara shackleton", "jeffrey skilling"),
                       ("sara shackleton", "jeffrey dasovich"), ("kay mann", "sara shackleton")])
    assert distances.resolve("kay mann", "sara shackleton", {"jeffrey skilling", "jeffrey dasovich"}) == "jeffrey skilling"
    tie = graph([("a b", "c d"), ("a b", "e f"), ("g h", "c d"), ("g h", "e f")])
    assert tie.resolve("a b", "g h", {"c d", "e f"}) is None
    assert distances.resolve("kay mann", "nobody", {"jeffrey skilling"}) is None


def test_links_and_centrality_count_distinct_people_mentioned_to_a_recipient():
    distances = graph([("kay mann", "jeffrey skilling"), ("sara shackleton", "jeffrey skilling"),
                       ("kay mann", "sara shackleton"), ("sara shackleton", "jonah self"), ("kay mann", "jonah self")])
    messages = pd.DataFrame({
        "path": ["m1", "m2"], "sender_person": ["kay mann", "kay mann"],
        "to_people": [["sara shackleton"], ["sara shackleton"]], "cc_people": [[], []],
        "mentions": [["Skilling", "Jonah Self", "Sara"], ["Skilling"]],
    })
    links, counts = mention_links(messages, name_index(PEOPLE), distances)
    assert set(links["person"]) == {"jeffrey skilling", "jonah self", "sara shackleton"}
    parties = pd.Series([{"kay mann", "sara shackleton"}] * 2, index=["m1", "m2"])
    measures = mention_centrality(links, parties).set_index("person_key")
    assert measures.loc["sara shackleton", "mentioned_to"] == 2           # the self-mention "Sara" is dropped
    assert measures.loc["sara shackleton", "mention_degree"] == 2
    assert measures.loc["jeffrey skilling", "mention_degree"] == 1
    assert measures.loc["sara shackleton", "third_party_mentioned_to"] == 2
    assert counts["mentions"] == 4


class FakeNLP:
    meta = {"name": "fake", "version": "1"}
    calls = 0

    pipe_names = ["ner"]

    def pipe(self, texts, batch_size=256):
        for text in texts:
            FakeNLP.calls += 1
            FakeNLP.seen = text
            words = [(w, text.index(w)) for w in text.split() if w.istitle()]
            yield type("Doc", (), {"ents": [type("Ent", (), {"text": w, "start_char": i, "label_": "PERSON"}) for w, i in words]})


def test_tags_are_cached_and_only_changed_text_is_retagged(tmp_path):
    cache = tmp_path / "tags.parquet"
    messages = pd.DataFrame({"path": ["m1", "m2"], "authored": ["ask Kay", "tell Sara"]})
    FakeNLP.calls = 0
    assert list(cached_mentions(messages, cache, FakeNLP())) == [[("Kay", 4)], [("Sara", 5)]] and FakeNLP.calls == 2
    messages.loc[1, "authored"] = "tell Jeff"
    assert list(cached_mentions(messages, cache, FakeNLP())) == [[("Kay", 4)], [("Jeff", 5)]] and FakeNLP.calls == 3


def test_tags_are_saved_chunk_by_chunk(tmp_path):

    class Crashing(FakeNLP):
        def pipe(self, texts, batch_size=256):
            for text in texts:
                if "Boom" in text:
                    raise RuntimeError("interrupted")
                yield from FakeNLP.pipe(self, [text])

    cache = tmp_path / "tags.parquet"
    messages = pd.DataFrame({"path": ["m1", "m2", "m3"], "authored": ["ask Kay", "tell Sara", "Boom"]})
    try:
        cached_mentions(messages, cache, Crashing(), chunk=1)
    except RuntimeError:
        pass
    assert len(pd.read_parquet(cache)) == 2       # the two chunks before the failure survive


def test_any_change_to_the_tagger_retags_everything(tmp_path, monkeypatch):
    cache = tmp_path / "tags.parquet"
    messages = pd.DataFrame({"path": ["m1"], "authored": ["ask Kay"]})
    FakeNLP.calls = 0
    cached_mentions(messages, cache, FakeNLP())
    cached_mentions(messages, cache, FakeNLP())
    assert FakeNLP.calls == 1

    class MorePipes(FakeNLP):
        pipe_names = ["tok2vec", "ner"]

    cached_mentions(messages, cache, MorePipes())
    assert FakeNLP.calls == 2                        # another component set
    monkeypatch.setattr(mentions_module, "MAX_CHARS", 3)
    cached_mentions(messages, cache, MorePipes())
    assert FakeNLP.calls == 3                        # another character cap
    pd.DataFrame({"key": ["x"], "model": ["fake-1"], "mentions": [["Kay"]]}).to_parquet(cache)
    cached_mentions(messages, cache, FakeNLP())
    assert FakeNLP.calls == 4                        # a cache from before tagger identities


def test_only_the_first_5000_characters_are_tagged():
    assert mentions_module.MAX_CHARS == 5000              # the documented cap
    text = "ask Kay " + "x" * 5000 + " Sara"
    assert tag_mentions(pd.Series([text]), FakeNLP()) == [[("Kay", 4)]]
    assert len(FakeNLP.seen) == 5000


def test_the_tagger_identity_covers_model_spacy_and_weights(tmp_path, monkeypatch):
    base = tagger_id(FakeNLP())

    class OtherVersion(FakeNLP):
        meta = {"name": "fake", "version": "2"}

    class WithWeights(FakeNLP):
        path = tmp_path

    assert tagger_id(OtherVersion()) != base
    (tmp_path / "weights").write_text("a")
    first = tagger_id(WithWeights())
    (tmp_path / "weights").write_text("b")
    assert first != tagger_id(WithWeights()) and first != base
    monkeypatch.setattr(mentions_module, "version", lambda package: "0.0")
    assert tagger_id(FakeNLP()) != base


def test_a_cached_entry_whose_names_are_not_in_the_text_is_retagged(tmp_path):
    cache = tmp_path / "tags.parquet"
    messages = pd.DataFrame({"path": ["m1"], "authored": ["ask Kay"]})
    FakeNLP.calls = 0
    cached_mentions(messages, cache, FakeNLP())
    forged = pd.read_parquet(cache).assign(mentions=[["FORGED PERSON"]], starts=[[999999]])
    forged.to_parquet(cache)
    assert list(cached_mentions(messages, cache, FakeNLP())) == [[("Kay", 4)]] and FakeNLP.calls == 2


def test_initials_middle_initials_and_hyphenated_names():
    index = name_index({"edward dunn", "ed smith", "mark e taylor", "mark d taylor", "mark taylor", "mary smith-jones"})
    assert compatible("Ed", index) == {"edward dunn", "ed smith"}     # a first name, never the initials E.D.
    assert compatible("E.D.", index) == compatible("ED", index) == {"edward dunn"}
    assert compatible("Mark E. Taylor", index) == {"mark e taylor", "mark taylor"}
    assert compatible("Mark Taylor", index) == {"mark e taylor", "mark d taylor", "mark taylor"}
    assert compatible("Mary Smith-Jones", index) == {"mary smith-jones"}
    assert compatible("Smith-Jones", index) == {"mary smith-jones"}


@pytest.mark.parametrize("text, mention, reason", [
    ("Governor Davis signed the bill.", "Davis", "office"),
    ("We met Sen. Feinstein today.", "Feinstein", "office"),
    ("Williams pipeline capacity is full.", "Williams", "company"),
    ("email Sally & let her know", "Sally", None),                  # a conjunction, not a company
    ("Call Tim Belden\nPower prices rose.", "Tim Belden", None),   # the next line is not the same phrase
    ("Kevin Presto Power Group", "Kevin Presto", None),            # a department, not a company
    ("Ask Dana Davis\nCapital Calls", "Dana Davis", None),
    ("Ste. Aurelie Timberlands", "Ste", "abbreviation"),           # spaCy's span stops before the period
    ("Thanks, Kay. See you.", "Kay", None),
    ("Duke Energy called.", "Duke Energy", "company"),
    ("Clemens Ste. Marie", "Ste.", "abbreviation"),
    ("Ask Dana Davis about it.", "Dana Davis", None),
    ("Sally Beck's group owns it.", "Sally Beck", None),
    ("our sales rep Kay Mann", "Kay Mann", None),
])
def test_context_marks_public_figures_companies_and_abbreviations(text, mention, reason):
    assert nil_reason(mention, text, text.index(mention)) == reason


def test_rows_record_why_they_leave_the_main_measures():
    distances = graph([("kay mann", "jeffrey skilling"), ("sara shackleton", "jeffrey skilling"), ("kay mann", "sara shackleton")])
    text = "Kay Mann\nGovernor Skilling"
    messages = pd.DataFrame({
        "path": ["m1", "m2", "m3"], "sender_person": ["kay mann"] * 3, "to_people": [["sara shackleton"]] * 3,
        "cc_people": [[]] * 3, "person_text": [True, True, False],
        "mentions": [[("Kay Mann", 0), ("Skilling", 18)], [("Skilling", 0)], [("Skilling", 0)]],
        "authored": [text, "Skilling agreed.", "Skilling agreed."],
    })
    links, counts = mention_links(messages, name_index(PEOPLE), distances)
    assert [x if isinstance(x, str) else None for x in links["excluded"]] == ["self", "office", None, "not_person_text"]
    assert counts["excluded_self"] == counts["excluded_office"] == counts["excluded_not_person_text"] == 1
    parties = pd.Series([{"kay mann", "sara shackleton"}] * 3, index=["m1", "m2", "m3"])
    measures = mention_measures(links, parties).set_index("person_key")
    assert measures.loc["sara shackleton", "mentioned_to"] == 1                # Skilling, from m2 only
    assert measures.loc["sara shackleton", "mentioned_to_unfiltered"] == 2     # Kay Mann and Skilling
    assert measures.loc["kay mann", "mention_degree"] == 0 and measures.loc["kay mann", "mention_degree_unfiltered"] == 1


def test_distances_ignore_edge_direction():
    one_way = graph([("jeffrey skilling", "kay mann"), ("jeffrey skilling", "sara shackleton")])
    assert one_way.resolve("kay mann", "sara shackleton", {"jeffrey skilling"}) == "jeffrey skilling"


def test_each_recipient_resolves_a_mention_separately():
    # Jeff is closest to Sara through Skilling and to Jonah through Dasovich.
    distances = graph([("kay mann", "jeffrey skilling"), ("kay mann", "jeffrey dasovich"),
                       ("sara shackleton", "jeffrey skilling"), ("jonah self", "jeffrey dasovich")])
    messages = pd.DataFrame({"path": ["m1"], "sender_person": ["kay mann"], "to_people": [["sara shackleton"]],
                             "cc_people": [["jonah self"]], "mentions": [["Jeff"]]})
    links, _ = mention_links(messages, name_index(PEOPLE), distances)
    assert dict(zip(links["recipient"], links["person"])) == {"sara shackleton": "jeffrey skilling",
                                                             "jonah self": "jeffrey dasovich"}


def test_the_cc_check_scores_single_and_ambiguous_candidates_apart():
    distances = graph([("kay mann", "sara shackleton"), ("kay mann", "jeffrey skilling"), ("sara shackleton", "jeffrey skilling"),
                       ("kay mann", "jeffrey dasovich")])
    messages = pd.DataFrame({
        "path": ["m1", "m2"], "sender_person": ["kay mann"] * 2, "to_people": [["sara shackleton"]] * 2,
        "cc_people": [["jeffrey skilling"], ["jeffrey dasovich"]], "mentions": [["Skilling"], ["Jeff"]],
    })
    _, counts = mention_links(messages, name_index(PEOPLE), distances)
    assert counts["cc_checks_single"] == 1 and counts["cc_checks_single_correct"] == 1
    # "Jeff" with Dasovich Cc'd: the resolver, using the To recipient, picks Skilling (one hop from both).
    assert counts["cc_checks_ambiguous"] == 1 and counts["cc_checks_ambiguous_correct"] == 0
    assert counts["cc_checks"] == 2 and counts["cc_checks_correct"] == 1
